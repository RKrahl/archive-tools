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


# Note: in the long run, we want to select the schedule (e.g. set the
# conditions, when to choose which schedule) in the configuration
# file, and even put the definition and semantics (e.g. which
# schedules exist and what do they mean) there.  But this seem to be
# most tricky part of the whole project.  We want to get the basics
# working first.  So for the moment, we hard code definition and
# semantics here and select the schedule as a command line argument.

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
        'backupdir': None,
        'targetdir': "%(backupdir)s",
        'name': "%(host)s-%(date)s-%(schedule)s.tar.bz2",
    }
    args_options = ('policy', 'user', 'schedule')

    def __init__(self, args):
        host = socket.gethostname()
        config_file = get_config_file()
        sections = ("%s/%s" % (host, args.policy), host, args.policy)
        self.config_file = config_file
        super().__init__(args, config_section=sections)
        if not self.config_file:
            raise ConfigError("configuration file %s not found" % config_file)
        self['host'] = host
        self['date'] = datetime.date.today().strftime("%y%m%d")
        if args.user:
            try:
                self['home'] = pwd.getpwnam(args.user).pw_dir
            except KeyError:
                pass

    @property
    def host(self):
        return self.get('host')

    @property
    def policy(self):
        return self.get('policy')

    @property
    def user(self):
        return self.get('user')

    @property
    def schedule(self):
        return self.get('schedule')

    @property
    def name(self):
        return self.get('name', required=True)

    @property
    def dirs(self):
        return self.get('dirs', required=True, split=True, type=Path)

    @property
    def excludes(self):
        return self.get('excludes', split=True, type=Path)

    @property
    def backupdir(self):
        return self.get('backupdir', required=True, type=Path)

    @property
    def targetdir(self):
        return self.get('targetdir', required=True, type=Path)

    @property
    def path(self):
        return self.targetdir / self.name

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
    config = Config(args)
except ConfigError as e:
    print("%s: configuration error: %s" % (argparser.prog, e), file=sys.stderr)
    sys.exit(2)
