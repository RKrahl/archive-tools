#! /usr/bin/python

import argparse
import datetime
from pathlib import Path
import stat
from archive import Archive

argparser = argparse.ArgumentParser()
argparser.add_argument('archive',
                       help=("path to the archive file"), type=Path)
args = argparser.parse_args()

def modstr(t, m):
    ftch = '-' if t == 'f' else t
    urch = 'r' if m & stat.S_IRUSR else '-'
    uwch = 'w' if m & stat.S_IWUSR else '-'
    if m & stat.S_ISUID:
        uxch = 's' if m & stat.S_IXUSR else 'S'
    else:
        uxch = 'x' if m & stat.S_IXUSR else '-'
    grch = 'r' if m & stat.S_IRGRP else '-'
    gwch = 'w' if m & stat.S_IWGRP else '-'
    if m & stat.S_ISGID:
        gxch = 's' if m & stat.S_IXGRP else 'S'
    else:
        gxch = 'x' if m & stat.S_IXGRP else '-'
    orch = 'r' if m & stat.S_IROTH else '-'
    owch = 'w' if m & stat.S_IWOTH else '-'
    if m & stat.S_ISVTX:
        oxch = 't' if m & stat.S_IXOTH else 'T'
    else:
        oxch = 'x' if m & stat.S_IXOTH else '-'
    return ''.join((ftch, urch, uwch, uxch, grch, gwch, gxch, orch, owch, oxch))


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
