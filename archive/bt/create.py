"""Create a backup.
"""

import logging
import os
from archive.archive import Archive
from archive.exception import ArchiveCreateError
from archive.index import ArchiveIndex
from archive.manifest import Manifest, DiffStatus, diff_manifest


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
    return filter(lambda i: i >= f_d, idx)

def filter_fileinfos(base, fileinfos):
    for stat, fi1, fi2 in diff_manifest(base, fileinfos):
        if stat == DiffStatus.MISSING_B or stat == DiffStatus.MATCH:
            continue
        yield fi2

def get_fileinfos(config):

    last_full = None
    last_cumu = None
    last_incr = []
    for i in get_prev_backups(config):
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

    if config.schedule != 'full':
        if not last_full:
            raise ArchiveCreateError("No previous full backup found, can not "
                                     "create %s archive" % config.schedule)
        base_archives = [last_full.path]
        if config.schedule == 'incr':
            if last_cumu:
                base_archives.append(last_cumu.path)
            base_archives.extend([i.path for i in last_incr])
        for p in base_archives:
            log.debug("considering %s to create differential archive", p)
            with Archive().open(p) as base:
                fileinfos = filter_fileinfos(base.manifest, fileinfos)

    return fileinfos

def create(config):
    os.umask(0o277)
    fileinfos = get_fileinfos(config)

    log.debug("creating archive %s", config.path)

    tags = [
        "host:%s" % config.host,
        "policy:%s" % config.policy,
        "schedule:%s" % config.schedule,
    ]
    if config.user:
        tags.append("user:%s" % config.user)
    Archive().create(config.path, fileinfos=fileinfos, tags=tags)
