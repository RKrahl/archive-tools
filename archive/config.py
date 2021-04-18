"""Manage configuration.

.. note::
   This module is intended as a helper for the internal use in some
   command line scripts.  It is not considered to be part of the API
   of archive-tools.  Most users will not need to use it directly or
   even care about it.
"""

from collections import ChainMap
import configparser
from archive.exception import ConfigError

class Config:

    defaults = dict()
    config_file = None
    args_options = ()

    def __init__(self, args, config_section=None):
        args_cfg = { k:vars(args)[k]
                     for k in self.args_options
                     if vars(args)[k] is not None }
        self.config = ChainMap({}, args_cfg)
        if self.config_file and config_section:
            cp = configparser.ConfigParser(comment_prefixes=('#', '!'))
            self.config_file = cp.read(self.config_file)
            if isinstance(config_section, str):
                config_section = (config_section,)
            self.config_section = []
            for section in config_section:
                try:
                    self.config.maps.append(cp[section])
                    self.config_section.append(section)
                except KeyError:
                    pass
        self.config.maps.append(self.defaults)
