#! /usr/bin/python
"""Create a backup.
"""

import argparse
import datetime
import logging
import os
from pathlib import Path
import pwd
import socket
import sys
import archive.config
from archive.exception import ConfigError
from archive.tools import now_str

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

schedules = {'full', 'cumu', 'incr'}
def get_config_file():
    try:
        return os.environ['BACKUP_CFG']
    except KeyError:
        return "/etc/backup.cfg"

class Config(archive.config.Config):

    defaults = {
        'dirs': None,
        'excludes': "",
        'targetdir': None,
        'backupdir': "%(targetdir)s",
        'name': "%(host)s-%(date)s-%(schedule)s.tar.bz2",
        'tags': "",
    }
    config_file = get_config_file()
    args_options = ('policy', 'user', 'schedule')

    def __init__(self, args):
        host = socket.gethostname()
        sections = ("%s/%s" % (host, args.policy), host, args.policy)
        super().__init__(args, config_section=sections)
        if not self.config_file:
            raise ConfigError("configuration file %s not found"
                              % self.config_file)
        self.config['host'] = host
        self.config['date'] = datetime.date.today().strftime("%y%m%d")
        if args.user:
            try:
                self.config['home'] = pwd.getpwnam(self.config['user']).pw_dir
            except KeyError:
                pass
        self.config['name'] = self.get('name', required=True)
        self.config['dirs'] = self.get('dirs', required=True, split=True)
        self.config['excludes'] = self.get('excludes', split=True)
        self.config['targetdir'] = self.get('targetdir', required=True)
        self.config['backupdir'] = self.get('backupdir')
        self.config['tags'] = self.get('tags', split=True)

argparser = argparse.ArgumentParser()
clsgrp = argparser.add_mutually_exclusive_group()
clsgrp.add_argument('--policy', default='sys')
clsgrp.add_argument('--user')
argparser.add_argument('--schedule', choices=schedules, default='full')
argparser.add_argument('-v', '--verbose', action='store_true',
                       help=("verbose diagnostic output"))
args = argparser.parse_args()

if args.verbose:
    logging.getLogger().setLevel(logging.DEBUG)
if args.user:
    args.policy = 'user'

try:
    config = Config(args).config
except ConfigError as e:
    print("%s: configuration error: %s" % (argparser.prog, e), file=sys.stderr)
    sys.exit(2)
