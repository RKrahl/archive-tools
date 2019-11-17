"""Implement the diff subcommand.
"""

from pathlib import Path
from archive.archive import Archive
from archive.exception import ArchiveReadError


def _common_checksum(manifest1, manifest2):
    for algorithm in manifest1.checksums:
        if algorithm in manifest2.checksums:
            return algorithm
    else:
        raise ArchiveReadError("No common checksum algorithm, "
                               "cannot compare archive content.")

def _next(it):
    try:
        return next(it)
    except StopIteration:
        return None

def _relpath(fi, basedir):
    if fi is not None:
        if fi.path.is_absolute():
            return fi.path
        else:
            return fi.path.relative_to(basedir)
    else:
        return None

def diff(args):
    archive1 = Archive().open(args.archive1)
    archive1.close()
    archive2 = Archive().open(args.archive2)
    archive2.close()
    algorithm = _common_checksum(archive1.manifest, archive2.manifest)
    # In principle, we might rely on the fact that the manifest of an
    # archive is always sorted at creation time.  On the other hand,
    # as we need to rely on this, we sort them again to be on the safe
    # side.
    archive1.manifest.sort()
    archive2.manifest.sort()
    it1 = iter(archive1.manifest)
    it2 = iter(archive2.manifest)
    fi1 = _next(it1)
    fi2 = _next(it2)
    status = 0
    while True:
        path1 = _relpath(fi1, archive1.basedir)
        path2 = _relpath(fi2, archive2.basedir)
        if path1 is None and path2 is None:
            break
        elif path1 is None or path1 > path2:
            print("Only in %s: %s" % (archive2.path, fi2.path))
            fi2 = _next(it2)
            status = max(status, 102)
        elif path2 is None or path2 > path1:
            print("Only in %s: %s" % (archive1.path, fi1.path))
            fi1 = _next(it1)
            status = max(status, 102)
        else:
            assert path1 == path2
            if fi1.type != fi2.type:
                print("Entries %s:%s and %s:%s have different type"
                      % (archive1.path, fi1.path, archive2.path, fi2.path))
                status = max(status, 102)
            elif fi1.type == "l":
                if fi1.target != fi2.target:
                    print("Symbol links %s:%s and %s:%s have different target"
                          % (archive1.path, fi1.path, archive2.path, fi2.path))
                    status = max(status, 101)
            elif fi1.type == "f":
                if fi1.checksum[algorithm] != fi2.checksum[algorithm]:
                    print("Files %s:%s and %s:%s differ"
                          % (archive1.path, fi1.path, archive2.path, fi2.path))
                    status = max(status, 101)
            fi1 = _next(it1)
            fi2 = _next(it2)
    return status

def add_parser(subparsers):
    parser = subparsers.add_parser('diff',
                                   help=("show the differences between "
                                         "two archives"))
    parser.add_argument('archive1', type=Path,
                        help=("first archive to compare"))
    parser.add_argument('archive2', type=Path,
                        help=("second archive to compare"))
    parser.set_defaults(func=diff)
