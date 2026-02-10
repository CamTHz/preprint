import logging
import sys
import warnings

# Suppress UserWarnings from the entire watchdog module
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    module="watchdog.*"  # Target any submodule of watchdog
)


from cliff.app import App
from cliff.commandmanager import CommandManager

from .config import Configurations


VERSION = "0.3.1"


class PreprintApp(App):

    log = logging.getLogger(__name__)
    confs = Configurations()

    def __init__(self):
        super(PreprintApp, self).__init__(
            description='Tools for writing latex papers',
            version=VERSION,
            command_manager=CommandManager('preprint.commands'))

    def initialize_app(self, argv):
        # Configure *this specific app's logger* and ensure it has a handler
        if self.options.debug:
            self.log.setLevel(logging.DEBUG)
        else:
            self.log.setLevel(logging.INFO)

        # Ensure a StreamHandler is present for *this app's logger*
        if not self.log.handlers:
            handler = logging.StreamHandler(sys.stderr)
            formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
            handler.setFormatter(formatter)
            self.log.addHandler(handler)

        self.log.debug('initialize_app: PreprintApp logger configured to level %s.', self.log.level)

        # Set master file from config if not provided on command line
        if self.options.master is None:
            self.options.master = self.confs.config('master')
            self.log.debug('initialize_app: Master file set from config to: %s', self.options.master)
        else:
            self.log.debug('initialize_app: Master file set from command line to: %s', self.options.master)

    def build_option_parser(self, *args):
        parser = super(PreprintApp, self).build_option_parser(*args)
        parser.add_argument(
            '--master',
            default=None, # Correctly defaults to None, so command-line takes precedence
            help='Name of master tex file')
        return parser

    def prepare_to_run_command(self, cmd):
        self.log.debug('prepare_to_run_command %s', cmd.__class__.__name__)

    def clean_up(self, cmd, result, err):
        self.log.debug('clean_up %s', cmd.__class__.__name__)
        if err:
            self.log.debug('got an error: %s', err)


def main(argv=sys.argv[1:]):
    myapp = PreprintApp()
    return myapp.run(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))