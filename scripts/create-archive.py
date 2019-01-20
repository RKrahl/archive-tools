#! /usr/bin/python

import argparse
import pathlib
import stat
import tarfile
import tempfile
from archive.manifest import Manifest

argparser = argparse.ArgumentParser()
argparser.add_argument('--compression',
                       choices=['none', 'gz', 'bz2', 'xz'], default='gz',
                       help=("compression mode"))
argparser.add_argument('archive', help=("path to the archive file"))
argparser.add_argument('files', nargs='+', type=pathlib.Path,
                       help="files to add to the archive")
args = argparser.parse_args()
if args.compression == 'none':
    args.compression = ''

manifest = Manifest(paths=args.files)

with tarfile.open(args.archive, 'w:%s' % args.compression) as tf:
    with tempfile.TemporaryFile() as tmpf:
        manifest.write(tmpf)
        tmpf.seek(0)
        manifest_info = tf.gettarinfo(arcname=".manifest.yaml", fileobj=tmpf)
        manifest_info.mode = stat.S_IFREG | 0o444
        tf.addfile(manifest_info, tmpf)
    for fi in manifest:
        tf.add(str(fi.path), recursive=False)
