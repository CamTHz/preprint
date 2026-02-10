#!/usr/bin/env python
# encoding: utf-8
import logging
import os
import json

from cliff.command import Command
from .texutils import find_root_tex_document, RootNotFound

from preprint.config import Configurations


class Init(Command):
    """Initialze the project with preprint.json configurations."""

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(Init, self).get_parser(prog_name)
        return parser

    def take_action(self, parsed_args):
        # Explicitly set this command's logger to DEBUG if global debug is on
        if self.app.options.debug:
            self.log.setLevel(logging.DEBUG)

        self.log.debug("init: take_action started.")
        # Pass the globally parsed self.app.options.master AND self.log to write_configs
        write_configs(master_override=self.app.options.master, logger=self.log) # Use self.app.options.master
        self.log.info("Wrote preprint.json")


def write_configs(master_override=None, logger=None): # Add logger argument
    """Write a default configurations file for the current project."""
    # Fallback if logger is not provided (e.g., direct call outside command context)
    if logger is None:
        logger = logging.getLogger(__name__)

    logger.debug("write_configs: Function called with master_override = %s", master_override)
    logger.debug("write_configs: Starting configuration process.")

    configs = Configurations()
    config_dict = configs.default_dict

    if master_override:
        config_dict['master'] = master_override
        logger.debug("write_configs: Master file set from --master argument: %s", master_override)
    else:
        logger.debug("write_configs: No --master argument provided, attempting auto-detection.")
        try:
            root_tex = find_root_tex_document(base_dir=".")
            config_dict['master'] = root_tex
            logger.debug("write_configs: Found root tex document by auto-detection: %s", root_tex)
        except RootNotFound:
            config_dict['master'] = "article.tex" # Default if not found
            logger.warning("write_configs: Root tex document not found by auto-detection, defaulting master to: %s", config_dict['master'])

    logger.debug("write_configs: Final configuration for master: %s", config_dict['master'])

    if os.path.exists("preprint.json"):
        logger.debug("write_configs: preprint.json already exists at %s. Removing it to write new configurations.", os.path.abspath("preprint.json"))
        os.remove("preprint.json")
    else:
        logger.debug("write_configs: preprint.json does not exist, creating new file.")
    with open("preprint.json", 'w', encoding='utf-8') as f: # Ensure encoding is specified
        json_content = json.dumps(config_dict,
                           sort_keys=True,
                           indent=4,
                           separators=(',', ': '))
        f.write(json_content)
        logger.debug("write_configs: Successfully wrote content to preprint.json: %s", json_content)

