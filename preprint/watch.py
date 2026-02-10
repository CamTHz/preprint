import logging
import os
import subprocess
import time

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from cliff.command import Command

from preprint.latexdiff import git_diff_pipeline
from .vc import run_vc


class Watch(Command):
    """Watch for changes and compile paper"""

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(Watch, self).get_parser(prog_name)
        parser.add_argument(
            '--exts',
            nargs='*',
            default=self.app.confs.config('exts'),
            help="File extensions to look for")
        parser.add_argument(
            '--cmd',
            default=self.app.confs.config('cmd'),
            help="Command to run on changes")
        parser.add_argument(
            '--diff',
            nargs='?',
            const='HEAD',
            default=None,
            help="Typeset diff against git commit")
        self.log.debug("watch: get_parser configured. Default exts: %s, default cmd: %s, default diff: %s",
                       parser.get_default('exts'), parser.get_default('cmd'),
                       parser.get_default('diff'))
        return parser

    def take_action(self, parsed_args):
        self.log.debug("watch: take_action started.")
        ignore = (os.path.splitext(self.app.options.master)[0] + ".pdf",
                  'build', '_current.tex', '_prev.tex')
        self.log.debug("watch: Ignore list: %s", ignore)
        self.log.debug("watch: parsed_args.diff: %s", parsed_args.diff)

        if parsed_args.diff is None:
            self.log.debug("watch: Initializing RegularChangeHandler.")
            handler = RegularChangeHandler(
                parsed_args.cmd, parsed_args.exts, ignore)
        else:
            self.log.debug("watch: Initializing DiffChangeHandler with diff: %s", parsed_args.diff)
            handler = DiffChangeHandler(
                self.app.options.master, parsed_args.diff, parsed_args.exts,
                ignore)
        self._watch(handler)

    def _watch(self, handler):
        self.log.debug("watch: Starting file system observer.")
        observer = Observer()
        observer.schedule(handler, '.', recursive=True)
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.log.debug("watch: KeyboardInterrupt received, stopping observer.")
            observer.stop()
        observer.join()
        self.log.debug("watch: File system observer stopped.")


class BaseChangeHandler(FileSystemEventHandler):
    """React to modified files."""
    log = logging.getLogger(__name__)

    def __init__(self, exts, ignores):
        super(BaseChangeHandler, self).__init__()
        self._exts = exts
        self._ignores = ignores
        self.log.debug("BaseChangeHandler: Initialized with exts: %s, ignores: %s", exts, ignores)

    def on_any_event(self, event):
        """If a file or folder is changed."""
        self.log.debug("BaseChangeHandler: Event detected: %s", event)
        if event.is_directory:
            self.log.debug("BaseChangeHandler: Event is for a directory, ignoring.")
            return
        else:
            event_ext = os.path.splitext(event.src_path)[-1]\
                .lower().lstrip('.')
            self.log.debug("BaseChangeHandler: Event src_path: %s, extracted extension: %s", event.src_path, event_ext)
            if event_ext in self._exts:
                self.log.debug("BaseChangeHandler: Extension '%s' is in watch list.", event_ext)
                for ig in self._ignores:
                    if ig in event.src_path:
                        self.log.debug("BaseChangeHandler: Path '%s' is in ignore list due to '%s', ignoring.", event.src_path, ig)
                        return
                # passed all tests
                self.log.debug("BaseChangeHandler: Path '%s' passed all checks, running compile.", event.src_path)
                self.run_compile()
            else:
                self.log.debug("BaseChangeHandler: Extension '%s' not in watch list, ignoring.", event_ext)
        return


class RegularChangeHandler(BaseChangeHandler):
    """Class for reacting to modified files and doing a regular compile."""
    log = logging.getLogger(__name__)

    def __init__(self, command, exts, ignores):
        super(RegularChangeHandler, self).__init__(exts, ignores)
        self._cmd = command
        self.log.debug("RegularChangeHandler: Initialized with command: %s", command)

    def run_compile(self):
        """Run a compilation."""
        self.log.debug("RegularChangeHandler: Running regular compile.")
        run_vc()
        self.log.debug("RegularChangeHandler: Executing command: %s", self._cmd)
        subprocess.call(self._cmd, shell=True)
        self.log.debug("RegularChangeHandler: Compile command executed.")


class DiffChangeHandler(BaseChangeHandler):
    """React to modified files while building latexdiffs."""
    log = logging.getLogger(__name__)

    def __init__(self, master_path, prev_commit, exts, ignores):
        super(DiffChangeHandler, self).__init__(exts, ignores)
        self._master = master_path
        self._prev_commit = prev_commit
        self._output_name = "{0}_diff".format(
            os.path.splitext(self._master)[0])
        # Hack the ignore list to include the output path
        self._ignores = list(ignores)
        self._ignores.append(self._output_name)
        self.log.debug("DiffChangeHandler: Initialized with master_path: %s, prev_commit: %s, output_name: %s, updated ignores: %s",
                       master_path, prev_commit, self._output_name, self._ignores)

    def run_compile(self):
        """Run a latexdiff+compile."""
        self.log.debug("DiffChangeHandler: Running latexdiff compile with output_name: %s, master: %s, prev_commit: %s",
                       self._output_name, self._master, self._prev_commit)
        git_diff_pipeline(
            self._output_name, self._master,
            self._prev_commit)
        self.log.debug("DiffChangeHandler: latexdiff compile pipeline executed.")
