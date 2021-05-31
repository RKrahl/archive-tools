"""Update the index of backups.
"""

import logging
from archive.index import ArchiveIndex


log = logging.getLogger(__name__)

def update_index(args, config):
    idx_file = config.backupdir / ".index.yaml"
    if idx_file.is_file():
        log.debug("reading index file %s", str(idx_file))
        with idx_file.open("rb") as f:
            idx = ArchiveIndex(f)
    else:
        log.debug("index file not found")
        idx = ArchiveIndex()
    idx.add_archives(config.backupdir.glob("*.tar*"), prune=args.prune)
    idx.sort()
    with idx_file.open("wb") as f:
        idx.write(f)
    return 0

def add_parser(subparsers):
    parser = subparsers.add_parser('index', help="update backup index")
    parser.add_argument('--no-prune', action='store_false', dest='prune',
                        help="do not remove missing backups from the index")
    parser.set_defaults(func=update_index)
