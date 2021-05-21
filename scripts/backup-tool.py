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
from archive.archive import Archive
import archive.config
from archive.exception import ConfigError, ArchiveCreateError
from archive.index import ArchiveIndex
from archive.manifest import Manifest, DiffStatus, diff_manifest

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

os.umask(0o277)

# Note: in the long run, we want to select the schedule (e.g. set the
# conditions, when to choose which schedule) in the configuration
# file, and even put the definition and semantics (e.g. which
# schedules exist and what do they mean) there.  But this seem to be
# most tricky part of the whole project.  We want to get the basics
# working first.  So for the moment, we hard code definition and
# semantics here and select the schedule as a command line argument.

# TODO:
# - consider add configuration options for dedup mode and for checksum
#   algorithm.
# - consider adding more log messages and logging configuration.

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


def filter_fileinfos(base, fileinfos):
    for stat, fi1, fi2 in diff_manifest(base, fileinfos):
        if stat == DiffStatus.MISSING_B or stat == DiffStatus.MATCH:
            continue
        yield fi2


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

log.info("host:%s, policy:%s", config.host, config.policy)

idx_file = config.backupdir / ".index.yaml"
if idx_file.is_file():
    log.debug("reading index file %s", str(idx_file))
    with idx_file.open("rb") as f:
        idx = ArchiveIndex(f)
else:
    log.debug("index file not found")
    idx = ArchiveIndex()
idx.sort()

f_d = dict(host=config.host, policy=config.policy)
if config.policy == 'user':
    f_d['user'] = config.user
last_full = None
last_cumu = None
last_incr = []
for i in filter(lambda i: i >= f_d, idx):
    if i.schedule == 'full':
        last_full = i
        last_cumu = None
        last_incr = []
    elif  i.schedule == 'cumu':
        last_cumu = i
        last_incr = []
    elif  i.schedule == 'incr':
        last_incr.append(i)

fileinfos = Manifest(paths=config.dirs, excludes=config.excludes)
tags = [
    "host:%s" % config.host,
    "policy:%s" % config.policy,
    "schedule:%s" % config.schedule,
]
if config.user:
    tags.append("user:%s" % config.user)

if config.schedule != 'full':
    if not last_full:
        raise ArchiveCreateError("No previous full backup found, "
                                 "can not create %s archive" % config.schedule)
    base_archives = [last_full.path]
    if config.schedule == 'incr':
        if last_cumu:
            base_archives.append(last_cumu.path)
        base_archives.extend([i.path for i in last_incr])
    for p in base_archives:
        log.debug("considering %s to create differential archive", p)
        with Archive().open(p) as base:
            fileinfos = filter_fileinfos(base.manifest, fileinfos)

log.debug("creating archive %s", config.path)
archive = Archive().create(config.path, fileinfos=fileinfos, tags=tags)
