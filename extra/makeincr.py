#! /usr/bin/python3
"""Create an incremental archive.

The script takes one or more basis archives and an input archive as
input.  It creates an output archive that contains all items from the
input archive that are not present in any of the basis archives.
"""

import argparse
from pathlib import Path
import tarfile
from archive.archive import Archive
from archive.manifest import DiffStatus, _common_checksum, diff_manifest


class CopyArchive(Archive):
    """Read items from a TarFile.

    An Archive that copies all items from another Archive rather then
    reading them from the file system on create().
    """

    def __init__(self, inp_arch):
        self.inp_arch = inp_arch
        super().__init__()

    def _create(self, mode):
        self.manifest.head['Date'] = self.inp_arch.manifest.head['Date']
        tags = []
        for t in self.inp_arch.manifest.tags:
            try:
                k, v = t.split(':')
            except ValueError:
                continue
            else:
                if k in ('host', 'policy', 'user'):
                    tags.append(t)
        if tags:
            self.manifest.head['Tags'] = tags
        super()._create(mode)

    def _add_item(self, tarf, fi, arcname):
        inp_tarf = self.inp_arch._file
        inp_arcname = self.inp_arch._arcname(fi.path)
        ti = inp_tarf._getmember(inp_arcname, normalize=True)
        if fi.is_file():
            dup = self._check_duplicate(ti, arcname)
            if dup:
                ti.type = tarfile.LNKTYPE
                ti.linkname = dup
                ti.name = arcname
                tarf.addfile(ti)
            else:
                with inp_tarf.extractfile(ti) as f:
                    ti.type = tarfile.REGTYPE
                    ti.linkname = ''
                    ti.name = arcname
                    tarf.addfile(ti, fileobj=f)
        else:
            ti.name = arcname
            tarf.addfile(ti)

    def _check_duplicate(self, ti, name):
        if ti.islnk() and ti.linkname in self._dupindex:
            return self._dupindex[ti.linkname]
        else:
            if ti.isreg():
                self._dupindex[ti.name] = name
            elif ti.islnk():
                self._dupindex[ti.linkname] = name
            return None

def filter_fileinfos(base, fileinfos, algorithm):
    for stat, fi1, fi2 in diff_manifest(base, fileinfos, algorithm):
        if stat == DiffStatus.MISSING_B or stat == DiffStatus.MATCH:
            continue
        yield fi2
        

def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument('base', type=Path, nargs='+',
                           help=("basis archives"))
    argparser.add_argument('input', type=Path,
                           help=("input archive"))
    argparser.add_argument('output', type=Path,
                           help=("input archive"))
    args = argparser.parse_args()

    inp_archive = Archive().open(args.input)
    fileinfos = inp_archive.manifest
    algorithm = fileinfos.checksums[0]
    for p in args.base:
        with Archive().open(p) as base:
            fileinfos = filter_fileinfos(base.manifest, fileinfos, algorithm)

    archive = CopyArchive(inp_archive).create(args.output, fileinfos=fileinfos)


if __name__ == "__main__":
    main()
