import os
import json
import logging


class Configurations(object):
    """Manager for configuration defaults."""

    log = logging.getLogger(__name__)

    _DEFAULTS = {
        "master": "paper.tex",
        "exts": ["tex", "pdf", "eps"],
        "cmd": "latexmk -f -pdf -bibtex-cond {master}"}

    def __init__(self):
        super(Configurations, self).__init__()
        self._confs = dict(self._DEFAULTS)
        # Read configurations
        if os.path.exists("preprint.json"):
            self.log.debug("Found preprint.json, loading configurations.")
            with open("preprint.json", 'r') as f:
                self._confs.update(json.load(f))
        else:
            self.log.debug("No preprint.json found, using default configurations.")
        self._sanitize_path('master')

    def default(self, name):
        """Get the default value for the named config, given the section."""
        return self._DEFAULTS[name]

    def config(self, name):
        """Get the configuration."""
        if name == "cmd":
            return self._confs['cmd'].format(master=self._confs['master'])
        else:
            return self._confs[name]

    @property
    def default_dict(self):
        return dict(self._DEFAULTS)

    def _sanitize_path(self, key):
        """Sanitize the path of a configuration given `key`."""
        p = self._confs[key]
        p = os.path.expandvars(os.path.expanduser(p))
        if os.path.dirname(p) == ".":
            p = os.path.basename(p)
        self._confs[key] = p


if __name__ == '__main__':
    conf = Configurations()
    Configurations.log.debug("Default master: %s", conf.default("master"))
    Configurations.log.debug("Default exts: %s", conf.default("exts"))
    Configurations.log.debug("Default cmd: %s", conf.default("cmd"))
    Configurations.log.debug("Configured exts: %s", conf.config("exts"))
    Configurations.log.debug("Type of configured exts: %s", type(conf.config("exts")))
    Configurations.log.debug("Configured cmd: %s", conf.config("cmd"))
