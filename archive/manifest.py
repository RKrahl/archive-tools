"""Provide the Manifest class that defines the archive metadata.
"""

from collections.abc import Sequence
import datetime
import grp
import os
from pathlib import Path
import pwd
import stat
import yaml
import archive
from archive.exception import ArchiveCreateError
from archive.tools import now_str, checksum, modstr


class FileInfo:

    Checksums = ['sha256']

    def __init__(self, data=None, path=None):
        if data is not None:
            self.type = data['type']
            self.path = Path(data['path'])
            self.uid = data['uid']
            self.uname = data['uname']
            self.gid = data['gid']
            self.gname = data['gname']
            self.mode = data['mode']
            self.mtime = data['mtime']
            if self.is_file():
                self.size = data['size']
                self.checksum = data['checksum']
            elif self.is_symlink():
                self.target = Path(data['target'])
        elif path is not None:
            self.path = path
            fstat = self.path.lstat()
            self.uid = fstat.st_uid
            try:
                self.uname = pwd.getpwuid(self.uid)[0]
            except KeyError:
                self.uname = None
            self.gid = fstat.st_gid
            try:
                self.gname = grp.getgrgid(self.gid)[0]
            except KeyError:
                self.gname = None
            self.mode = stat.S_IMODE(fstat.st_mode)
            self.mtime = fstat.st_mtime
            if stat.S_ISREG(fstat.st_mode):
                self.type = 'f'
                self.size = fstat.st_size
                with self.path.open('rb') as f:
                    self.checksum = checksum(f, self.Checksums)
            elif stat.S_ISDIR(fstat.st_mode):
                self.type = 'd'
            elif stat.S_ISLNK(fstat.st_mode):
                self.type = 'l'
                self.target = Path(os.readlink(str(self.path)))
            else:
                raise ArchiveCreateError("%s: invalid file type" 
                                         % str(self.path))
        else:
            raise TypeError("Either data or path must be provided")

    def is_dir(self):
        return self.type == 'd'

    def is_file(self):
        return self.type == 'f'

    def is_symlink(self):
        return self.type == 'l'

    def as_dict(self):
        d = {
            'type': self.type,
            'path': str(self.path),
            'uid': self.uid,
            'uname': self.uname,
            'gid': self.gid,
            'gname': self.gname,
            'mode': self.mode,
            'mtime': self.mtime,
        }
        if self.is_file():
            d['size'] = self.size
            d['checksum'] = self.checksum
        elif self.is_symlink():
            d['target'] = str(self.target)
        return d

    def __str__(self):
        m = modstr(self.type, self.mode)
        ug = "%s/%s" % (self.uname or self.uid, self.gname or self.gid)
        s = str(self.size if self.type == 'f' else 0)
        mtime = datetime.datetime.fromtimestamp(self.mtime)
        d = mtime.strftime("%Y-%m-%d %H:%M")
        if self.type == 'l':
            p = "%s -> %s" % (self.path, self.target)
        else:
            p = str(self.path)
        return "%s  %s  %s  %s  %s" % (m, ug, s, d, p)

    @classmethod
    def iterpaths(cls, paths):
        """Iterate over paths, descending directories.
        Yield a FileInfo object for each path.

        If last FileInfo object did correspond to a directory, the caller
        may send a true value to the generator to skip descending into the
        directory.  For other file types, any value sent to the generator
        will have no effect.
        """
        for p in paths:
            info = cls(path=p)
            if (yield info):
                continue
            if info.is_dir():
                yield from cls.iterpaths(p.iterdir())


class Manifest(Sequence):

    Version = "1.0"

    def __init__(self, fileobj=None, paths=None):
        if fileobj is not None:
            docs = yaml.safe_load_all(fileobj)
            self.head = next(docs)
            self.fileinfos = [ FileInfo(data=d) for d in next(docs) ]
        elif paths is not None:
            self.head = {
                "Date": now_str(),
                "Generator": "archive-tools %s" % archive.__version__,
                "Version": self.Version,
                "Checksums": FileInfo.Checksums,
            }
            fileinfos = FileInfo.iterpaths(paths)
            self.fileinfos = sorted(fileinfos, key=lambda fi: fi.path)
        else:
            raise TypeError("Either fileobj or paths must be provided")

    def __len__(self):
        return len(self.fileinfos)

    def __getitem__(self, index):
        return self.fileinfos.__getitem__(index)

    def find(self, path):
        for fi in self:
            if fi.path == path:
                return fi
        else:
            return None

    def write(self, fileobj):
        fileobj.write("%YAML 1.1\n".encode("ascii"))
        yaml.dump(self.head, stream=fileobj, encoding="ascii", 
                  default_flow_style=False, explicit_start=True)
        yaml.dump([ fi.as_dict() for fi in self ],
                  stream=fileobj, encoding="ascii",
                  default_flow_style=False, explicit_start=True)
