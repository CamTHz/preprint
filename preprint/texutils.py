#!/usr/bin/env python
# encoding: utf-8
"""
LaTeX utilities.
"""

import os
import re
import logging
from TexSoup import TexSoup

from .gitio import read_git_blob

log = logging.getLogger(__name__)


class RootNotFound(Exception):
    pass


def remove_comments(tex):
    """Remove comments from LaTeX."""
    log.debug("remove_comments: Removing comments from tex content.")
    cleaned_tex = re.sub(r'(?<!\\)%.*', '', tex)
    log.debug("remove_comments: Comments removed.")
    return cleaned_tex


def inline(tex, base_dir='.', replacer=None, ifexists_replacer=None):
    """Inline LaTeX files."""
    log.debug("inline: Starting inlining process from base_dir: %s", base_dir)

    def sub_if_exists(match):
        original_file_path = match.group(1)
        file_path_attempt1 = os.path.join(base_dir, original_file_path + '.tex')
        file_path_attempt2 = os.path.join('.', original_file_path + '.tex') # Fallback to current dir

        current_file_path = None
        if os.path.exists(file_path_attempt1):
            current_file_path = file_path_attempt1
        elif os.path.exists(file_path_attempt2):
            current_file_path = file_path_attempt2

        if current_file_path:
            log.debug("inline: Inlining file: %s from %s", original_file_path, current_file_path)
            with open(current_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            inlined_content = inline(content,
                                     base_dir=os.path.dirname(current_file_path),
                                     replacer=replacer,
                                     ifexists_replacer=ifexists_replacer)
            log.debug("inline: Successfully inlined %s", original_file_path)
            return inlined_content
        else:
            log.debug("inline: File %s.tex not found in %s or .", original_file_path, base_dir)
            return ''

    if replacer is None:
        replacer = sub_if_exists
    if ifexists_replacer is None:
        ifexists_replacer = sub_if_exists

    tex = re.sub(r'\\input{(.*?)}', replacer, tex)
    tex = re.sub(r'\\InputIfFileExists{(.*?)}{.*?}{.*?}', ifexists_replacer, tex)
    log.debug("inline: Finished inlining process.")
    return tex


def inline_bbl(tex, bbl_text):
    """Inline a .bbl file."""
    log.debug("inline_bbl: Attempting to inline .bbl content.")
    soup = TexSoup(tex)
    
    # Find the \bibliography command and replace it with the bbl content
    bib_node = soup.find('bibliography') # Use find for direct command
    if bib_node:
        log.debug("inline_bbl: Found \\bibliography command, replacing with .bbl content.")
        bib_node.replace_with(bbl_text)
    else:
        # If no \bibliography command is found, try to find a \begin{document}
        # and insert the bbl_text before it, as a fallback.
        begin_document = soup.find('document')
        if begin_document:
            log.debug("inline_bbl: \\bibliography not found, falling back to inserting before \\begin{document}.")
            begin_document.insert_before(bbl_text)
        else:
            log.warning("inline_bbl: Neither \\bibliography nor \\begin{document} found for bbl inlining.")

    inlined_tex = str(soup)
    log.debug("inline_bbl: Finished inlining .bbl content.")
    return inlined_tex


def inline_blob(commit_ref, tex, base_dir='.', repo_dir='.'):
    """Inline LaTeX files from a git blob."""
    log.debug("inline_blob: Starting inlining from blob for commit %s, base_dir: %s, repo_dir: %s",
              commit_ref, base_dir, repo_dir)
    soup = TexSoup(tex)
    for node in soup.find_all(('input', 'InputIfFileExists')):
        if not node.args:
            log.debug("inline_blob: Node %s has no arguments, skipping.", node.name)
            continue

        original_file_path = node.args[0]
        file_path_to_read = os.path.join(base_dir, original_file_path + '.tex')
        log.debug("inline_blob: Attempting to read blob for file: %s", file_path_to_read)
        try:
            content = read_git_blob(commit_ref, file_path_to_read, repo_dir=repo_dir)
            log.debug("inline_blob: Successfully read blob for %s", original_file_path)
            # Recursively inline content
            content = inline_blob(commit_ref, content,
                                  base_dir=os.path.dirname(file_path_to_read),
                                  repo_dir=repo_dir)
            node.replace_with(content)
            log.debug("inline_blob: Successfully inlined %s from blob.", original_file_path)
        except Exception as e:
            log.warning("inline_blob: Could not read blob for %s (Error: %s), replacing with empty string.", original_file_path, e)
            node.replace_with('')
    log.debug("inline_blob: Finished inlining from blob.")
    return str(soup)


def find_root_tex_document(base_dir='.'):
    """Find the root .tex document in a directory by looking for \\documentclass."""
    log.debug("find_root_tex_document: Searching for root .tex document in: %s", base_dir)
    documentclass_pattern = re.compile(r'^\s*\\documentclass', re.MULTILINE)
    for root, dirs, files in os.walk(base_dir):
        log.debug("find_root_tex_document: Checking directory: %s", root)
        for file in files:
            if file.endswith('.tex'):
                file_path = os.path.join(root, file)
                log.debug("find_root_tex_document: Found .tex file: %s", file_path)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        # Read a chunk of the file to efficiently find \documentclass
                        # No need to read the whole file if it's huge
                        content = f.read(2048) # Read first 2KB
                        if documentclass_pattern.search(content):
                            log.debug("find_root_tex_document: Identified root tex document by \\documentclass: %s", file_path)
                            return file_path
                except Exception as e:
                    log.warning("find_root_tex_document: Could not read file %s: %s", file_path, e)
    log.error("find_root_tex_document: No root .tex document found in %s containing \\documentclass.", base_dir)
    raise RootNotFound("No root .tex document found.")


def _find_exts(fig_path, ext_priority):
    """Return a tuple of all formats for which a figure exists."""
    log.debug("_find_exts: Searching for extensions for %s with priority: %s", fig_path, ext_priority)
    basepath = os.path.splitext(fig_path)[0]
    has_exts = []
    for ext in ext_priority:
        p = ".".join((basepath, ext))
        if os.path.exists(p):
            log.debug("_find_exts: Found existing file: %s", p)
            has_exts.append(ext)
    log.debug("_find_exts: Found extensions for %s: %s", fig_path, has_exts)
    return tuple(has_exts)