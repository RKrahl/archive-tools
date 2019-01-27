#! /usr/bin/python

import argparse
import datetime
from pathlib import Path
from archive import Archive
from archive.tools import modstr


argparser = argparse.ArgumentParser()
argparser.add_argument('archive',
                       help=("path to the archive file"), type=Path)
args = argparser.parse_args()


archive = Archive(args.archive, "r")
items = []
l_ug = 0
l_s = 0
for fi in archive.manifest:
    m = modstr(fi.type, fi.mode)
    ug = "%s/%s" % (fi.uname or fi.uid, fi.gname or fi.gid)
    s = str(fi.size if fi.type == 'f' else 0)
    d = datetime.datetime.fromtimestamp(fi.mtime).strftime("%Y-%m-%d %H:%M")
    if fi.type == 'l':
        p = "%s -> %s" % (fi.path, fi.target)
    else:
        p = str(fi.path)
    items.append( (m, ug, s, d, p) )
    l_ug = max(l_ug, len(ug))
    l_s = max(l_s, len(s))

format_str = "%%s  %%%ds  %%%ds  %%s  %%s" % (l_ug, l_s)

for i in items:
    print(format_str % i)
