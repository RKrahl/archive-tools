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

def _next(it, skip=None):
    try:
        while True:
            fi = next(it)
            if skip:
                try:
                    fi.path.relative_to(skip)
                except ValueError:
                    pass
                else:
                    continue
            return fi
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
    # as we depend on this, we sort them again to be on the safe side.
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
            if args.skip_dir_content and fi2.is_dir():
                fi2 = _next(it2, skip=fi2.path)
            else:
                fi2 = _next(it2)
            status = max(status, 102)
        elif path2 is None or path2 > path1:
            print("Only in %s: %s" % (archive1.path, fi1.path))
            if args.skip_dir_content and fi1.is_dir():
                fi1 = _next(it1, skip=fi1.path)
            else:
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
                # Note: we don't need to compare the size, because if
                # the size differs, it's mostly certain that also the
                # checksums do.
                if fi1.checksum[algorithm] != fi2.checksum[algorithm]:
                    print("Files %s:%s and %s:%s differ"
                          % (archive1.path, fi1.path, archive2.path, fi2.path))
                    status = max(status, 101)
                elif args.report_meta and (fi1.uid != fi2.uid or
                                           fi1.uname != fi2.uname or
                                           fi1.gid != fi2.gid or
                                           fi1.gname != fi2.gname or
                                           fi1.mode != fi2.mode or
                                           int(fi1.mtime) != int(fi2.mtime)):
                    print("File system metadata for %s:%s and %s:%s differ"
                          % (archive1.path, fi1.path, archive2.path, fi2.path))
                    status = max(status, 100)
            fi1 = _next(it1)
            fi2 = _next(it2)
    return status

def add_parser(subparsers):
    parser = subparsers.add_parser('diff',
                                   help=("show the differences between "
                                         "two archives"))
    parser.add_argument('--report-meta', action='store_true',
                        help=("also show differences in file system metadata"))
    parser.add_argument('--skip-dir-content', action='store_true',
                        help=("in the case of a subdirectory missing from "
                              "one archive, only report the directory, but "
                              "skip its content"))
    parser.add_argument('archive1', type=Path,
                        help=("first archive to compare"))
    parser.add_argument('archive2', type=Path,
                        help=("second archive to compare"))
    parser.set_defaults(func=diff)
