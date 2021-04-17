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

def get_config(args, defaults):
    args_cfg_options = ('host', 'port', 'security', 'user')
    args_cfg = { k:vars(args)[k] for k in args_cfg_options if vars(args)[k] }
    config = ChainMap({}, args_cfg)
    if args.config_section:
        cp = configparser.ConfigParser()
        if not cp.read(args.config_file):
            raise ConfigError("configuration file %s not found"
                              % args.config_file)
        try:
            config.maps.append(cp[args.config_section])
        except KeyError:
            raise ConfigError("configuration section %s not found"
                              % args.config_section)
    config.maps.append(defaults)
    return config

