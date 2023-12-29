"""Implement the diff subcommand.
"""

from pathlib import Path
from archive.archive import Archive
from archive.exception import ArchiveReadError
from archive.manifest import DiffStatus, _common_checksum, diff_manifest


def _skip_dir_filter(diff):
    skip_path = None
    for t in diff:
        diff_stat, fi1, fi2 = t
        if skip_path:
            p = (fi1 or fi2).path
            try:
                p.relative_to(skip_path)
            except ValueError:
                pass
            else:
                continue
        yield t
        if diff_stat == DiffStatus.MISSING_A and fi2.type == 'd':
            skip_path = fi2.path
        elif diff_stat == DiffStatus.MISSING_B and fi1.type == 'd':
            skip_path = fi1.path
        else:
            skip_path = None


def diff(args):
    archive1 = Archive().open(args.archive1)
    manifest1 = archive1.manifest
    archive1.close()
    archive2 = Archive().open(args.archive2)
    manifest2 = archive2.manifest
    archive2.close()
    algorithm = _common_checksum(manifest1, manifest2)
    diff = diff_manifest(manifest1, manifest2, algorithm)
    if args.skip_dir_content:
        diff = _skip_dir_filter(diff)
    status = 0
    for diff_stat, fi1, fi2 in diff:
        if diff_stat == DiffStatus.MISSING_A:
            print("Only in %s: %s" % (args.archive2, fi2.path))
            status = max(status, 102)
        elif diff_stat == DiffStatus.MISSING_B:
            print("Only in %s: %s" % (args.archive1, fi1.path))
            status = max(status, 102)
        elif diff_stat == DiffStatus.TYPE:
            print("Entries %s:%s and %s:%s have different type"
                  % (args.archive1, fi1.path, args.archive2, fi2.path))
            status = max(status, 102)
        elif diff_stat == DiffStatus.SYMLNK_TARGET:
            print("Symbol links %s:%s and %s:%s have different target"
                  % (args.archive1, fi1.path, args.archive2, fi2.path))
            status = max(status, 101)
        elif diff_stat == DiffStatus.CONTENT:
            print("Files %s:%s and %s:%s differ"
                  % (args.archive1, fi1.path, args.archive2, fi2.path))
            status = max(status, 101)
        elif diff_stat == DiffStatus.META and args.report_meta:
            print("File system metadata for %s:%s and %s:%s differ"
                  % (args.archive1, fi1.path, args.archive2, fi2.path))
            status = max(status, 100)
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
