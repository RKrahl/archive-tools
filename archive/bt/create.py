"""Create a backup.
"""

import datetime
import logging
import os
from archive.archive import Archive
from archive.exception import ArchiveCreateError
from archive.index import ArchiveIndex
from archive.manifest import Manifest, DiffStatus, diff_manifest
from archive.bt.schedule import ScheduleDate, BaseSchedule, NoFullBackupError


log = logging.getLogger(__name__)

def get_prev_backups(config):
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
    return list(filter(lambda i: i >= f_d, idx))

def filter_fileinfos(base, fileinfos):
    for stat, fi1, fi2 in diff_manifest(base, fileinfos):
        if stat == DiffStatus.MISSING_B or stat == DiffStatus.MATCH:
            continue
        yield fi2

def get_schedule(config):
    last_schedule = None
    schedules = []
    for s in config.schedules:
        sd_str = config.get('schedule.%s.date' % s, required=True)
        cls = BaseSchedule.SubClasses[s]
        last_schedule = cls(s, ScheduleDate(sd_str), last_schedule)
        schedules.append(last_schedule)
    now = datetime.datetime.now()
    for s in schedules:
        if s.match_date(now):
            return s
    else:
        log.debug("no schedule date matches now")
        return None

def get_fileinfos(config, schedule):
    fileinfos = Manifest(paths=config.dirs, excludes=config.excludes)
    try:
        base_archives = schedule.get_base_archives(get_prev_backups(config))
    except NoFullBackupError:
        raise ArchiveCreateError("No previous full backup found, can not "
                                 "create %s archive" % schedule.name)
    for p in [i.path for i in base_archives]:
        log.debug("considering %s to create differential archive", p)
        with Archive().open(p) as base:
            fileinfos = filter_fileinfos(base.manifest, fileinfos)
    return fileinfos

def create(args, config):
    os.umask(0o277)
    schedule = get_schedule(config)
    if schedule is None:
        return 0
    config['schedule'] = schedule.name
    fileinfos = get_fileinfos(config, schedule)

    log.debug("creating archive %s", config.path)

    tags = [
        "host:%s" % config.host,
        "policy:%s" % config.policy,
        "schedule:%s" % schedule.name,
    ]
    if config.user:
        tags.append("user:%s" % config.user)
    Archive().create(config.path, fileinfos=fileinfos, tags=tags)
    return 0

def add_parser(subparsers):
    parser = subparsers.add_parser('create', help="create a backup")
    clsgrp = parser.add_mutually_exclusive_group()
    clsgrp.add_argument('--policy', default='sys')
    clsgrp.add_argument('--user')
    parser.set_defaults(func=create)
