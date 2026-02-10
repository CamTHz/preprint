#!/usr/bin/env python
# encoding: utf-8
"""
Git IO utilities.
"""

import git
import logging

log = logging.getLogger(__name__)


def absolute_git_root_dir(path):
    """Get the absolute path of the git repository root."""
    log.debug("absolute_git_root_dir: Checking path for git repository: %s", path)
    try:
        repo = git.Repo(path, search_parent_directories=True)
        git_root = repo.git.rev_parse("--show-toplevel")
        log.debug("absolute_git_root_dir: Found git root: %s", git_root)
        return git_root
    except git.InvalidGitRepositoryError:
        log.debug("absolute_git_root_dir: No git repository found at or above %s", path)
        return None


def read_git_blob(commit_ref, path, repo_dir='.'):
    """Read a file from a git blob."""
    log.debug("read_git_blob: Reading blob for commit_ref: %s, path: %s, repo_dir: %s",
              commit_ref, path, repo_dir)
    repo = git.Repo(repo_dir)
    commit = repo.commit(commit_ref)
    blob = commit.tree / path
    content = blob.data_stream.read().decode('utf-8')
    log.debug("read_git_blob: Successfully read content from blob for path: %s", path)
    return content
