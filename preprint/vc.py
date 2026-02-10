#!/usr/bin/env python
# encoding: utf-8
"""
Runs the vc tool, if available, to update the version control string in your
latex document.

See http://www.ctan.org/pkg/vc
"""

import os
import subprocess
import logging


log = logging.getLogger(__name__)


def vc_exists():
    """Return `True` if the project uses vc."""
    vc_path = 'vc'
    vc_git_awk_path = 'vc-git.awk'
    log.debug("vc_exists: Checking for existence of %s and %s", vc_path, vc_git_awk_path)
    if os.path.exists(vc_path) and os.path.exists(vc_git_awk_path):
        log.debug("vc_exists: Found a vc installation at %s and %s", vc_path, vc_git_awk_path)
        return True
    else:
        log.debug("vc_exists: Did not find a vc installation at %s or %s", vc_path, vc_git_awk_path)
        return False


def run_vc():
    """Run the vc tool."""
    if vc_exists():
        log.debug("run_vc: Running vc command: './vc'")
        subprocess.call("./vc", shell=True)
        log.debug("run_vc: vc command executed.")
    else:
        log.debug("run_vc: vc does not exist, skipping run_vc.")
