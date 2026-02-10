#!/usr/bin/env python
# encoding: utf-8
"""
Command for running latexdiff.
"""

import logging
import os
import subprocess
import codecs
import shutil
import git

from .texutils import inline, inline_blob, remove_comments
from .gitio import read_git_blob, absolute_git_root_dir

from cliff.command import Command


class Diff(Command):
    """Run latexdiff between HEAD and a git ref."""

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(Diff, self).get_parser(prog_name)
        parser.add_argument(
            'prev_commit',
            help="Commit SHA to compare HEAD against.")
        parser.add_argument(
            '-n', '--name',
            default=None,
            help="Name of the difference file.")
        return parser

    def take_action(self, parsed_args):
        self.log.debug("diff: take_action started.")
        self.log.debug("diff: prev_commit = %s", parsed_args.prev_commit)
        self.log.debug("diff: name = %s", parsed_args.name)
        self.log.debug("diff: master = %s", self.app.options.master)

        # Inline current and previous versions of the document
        if parsed_args.name is None:
            name = "current_{0}".format(parsed_args.prev_commit)
            self.log.debug("diff: Using default name: %s", name)
        else:
            name = parsed_args.name
            self.log.debug("diff: Using provided name: %s", name)

        git_diff_pipeline(
            name,
            self.app.options.master,
            parsed_args.prev_commit)


def git_diff_pipeline(output_name, master_path, prev_commit):
    """Pipeline for typesetting latexdiff against a commit in git history."""
    log = logging.getLogger(__name__)
    log.debug("git_diff_pipeline: output_name = %s, master_path = %s, prev_commit = %s",
              output_name, master_path, prev_commit)

    current_path = inline_current(master_path)
    log.debug("git_diff_pipeline: Inlined current path: %s", current_path)
    prev_path = inline_prev(prev_commit, master_path)
    log.debug("git_diff_pipeline: Inlined previous path: %s", prev_path)

    # Run latexmk
    diff_path = os.path.splitext(output_name)[0]
    ldiff_cmd = "latexdiff --type=CTRADITIONAL {prev} {current} > {diff}.tex".\
        format(prev=prev_path, current=current_path, diff=diff_path)
    log.debug("git_diff_pipeline: Executing latexdiff command: %s", ldiff_cmd)
    subprocess.call(ldiff_cmd, shell=True)

    # Compile the diff document with latexmk
    ltmk_cmd = "latexmk -f -pdf -bibtex-cond {0}.tex".format(diff_path)
    log.debug("git_diff_pipeline: Executing latexmk compilation command: %s", ltmk_cmd)
    subprocess.call(ltmk_cmd, shell=True)

    # Copy to build directory
    if not os.path.exists("build"):
        log.debug("git_diff_pipeline: Creating build directory.")
        os.makedirs("build")
    pdf_path = "{0}.pdf".format(output_name)
    if os.path.exists(pdf_path):
        dest_path = os.path.join("build", pdf_path)
        log.debug("git_diff_pipeline: Moving %s to %s", pdf_path, dest_path)
        shutil.move(pdf_path, dest_path)

    # Clean up
    ltmk_cmd = "latexmk -f -pdf -bibtex-cond -c {0}.tex".format(diff_path)
    log.debug("git_diff_pipeline: Executing latexmk cleanup command: %s", ltmk_cmd)
    subprocess.call(ltmk_cmd, shell=True)
    build_exts = ['Notes.bib', '.bbl', '.tex']
    log.debug("git_diff_pipeline: Cleaning up intermediate files with extensions: %s", build_exts)
    for ext in build_exts:
        path = "".join((output_name, ext))
        if os.path.exists(path):
            log.debug("git_diff_pipeline: Removing %s", path)
            os.remove(path)
    log.debug("git_diff_pipeline: Removing previous inlined file: %s", prev_path)
    os.remove(prev_path)
    log.debug("git_diff_pipeline: Removing current inlined file: %s", current_path)
    os.remove(current_path)


def inline_current(root_tex_path):
    """Inline the current manuscript."""
    base_dir = os.path.dirname(root_tex_path)
    with codecs.open(root_tex_path, 'r', encoding='utf-8') as f:
        root_text = f.read()
        root_text = remove_comments(root_text)
        root_text = inline(root_text, base_dir=base_dir)
    output_path = "_current.tex"
    if os.path.exists(output_path):
        os.remove(output_path)
    with codecs.open(output_path, 'w', encoding='utf-8') as f:
        f.write(root_text)
    return output_path


def inline_prev(commit_ref, root_tex_path):
    """Inline the previous manuscript in the git tree.

    Parameters
    ----------
    commif_ref : str
        Commit reference string.
    root_tex_path : str
        Path to the root tex document in the filesystem.

    Returns
    -------
    output_path : str
        Path to the inlined latex document for latexdiff processing.
    """
    log = logging.getLogger(__name__)
    log.debug("inline_prev root_tex")
    log.debug(root_tex_path)
    git_root = absolute_git_root_dir(root_tex_path)
    rel_root_tex_path = os.path.relpath(os.path.abspath(root_tex_path),
                                        git_root)
    root_text = read_git_blob(commit_ref, rel_root_tex_path,
                              repo_dir=git_root)
    log.debug("prev root_text")
    log.debug(root_text)
    root_text = remove_comments(root_text)
    root_text = inline_blob(commit_ref, root_text,
                            base_dir=os.path.dirname(rel_root_tex_path),
                            repo_dir=git_root)
    output_path = "_prev.tex"
    if os.path.exists(output_path):
        os.remove(output_path)
    with codecs.open(output_path, 'w', encoding='utf-8') as f:
        f.write(root_text)
    return output_path


def get_n_commits():
    """Count commits in a repo from HEAD."""
    repo = git.Repo(".")
    commits = list(repo.iter_commits())
    n = len(commits)
    return n


def get_commits():
    """Returns a list of commits in the repository."""
    repo = git.Repo(".")
    commits = list(repo.iter_commits())
    return commits


def match_commit(sha):
    """Match the sha fragment to a commit."""
    commits = get_commits()
    for cm in commits:
        if cm.hexsha.startswith(sha):
            return cm
    return None
