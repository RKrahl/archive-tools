"""Provide the Manifest class that defines the archive metadata.
"""

from collections.abc import Sequence
import datetime
from distutils.version import StrictVersion
import grp
import os
from pathlib import Path
import pwd
import stat
import warnings
import yaml
import archive
from archive.exception import ArchiveInvalidTypeError, ArchiveWarning
from archive.tools import now_str, parse_date, checksum, mode_ft, ft_mode


class FileInfo:

    Checksums = ['sha256']

    def __init__(self, data=None, path=None):
        if data is not None:
            self.path = Path(data['path'])
            self.uid = data['uid']
            self.uname = data['uname']
            self.gid = data['gid']
            self.gname = data['gname']
            self.st_mode = ft_mode[data['type']] | data['mode']
            self.mtime = data['mtime']
            if self.is_file():
                self.size = data['size']
                self._checksum = data['checksum'] or []
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
            self.st_mode = fstat.st_mode
            self.mtime = fstat.st_mtime
            if stat.S_ISREG(fstat.st_mode):
                self.size = fstat.st_size
                self._checksum = None
            elif stat.S_ISDIR(fstat.st_mode):
                pass
            elif stat.S_ISLNK(fstat.st_mode):
                self.target = Path(os.readlink(str(self.path)))
            else:
                ftype = stat.S_IFMT(fstat.st_mode)
                raise ArchiveInvalidTypeError(self.path, ftype)
        else:
            raise TypeError("Either data or path must be provided")

    @property
    def type(self):
        return mode_ft[stat.S_IFMT(self.st_mode)]

    @property
    def mode(self):
        return stat.S_IMODE(self.st_mode)

    @property
    def checksum(self):
        if self._checksum is None:
            with self.path.open('rb') as f:
                self._checksum = checksum(f, self.Checksums)
        return self._checksum

    def is_dir(self):
        return stat.S_ISDIR(self.st_mode)

    def is_file(self):
        return stat.S_ISREG(self.st_mode)

    def is_symlink(self):
        return stat.S_ISLNK(self.st_mode)

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
        m = stat.filemode(self.st_mode)
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
    def iterpaths(cls, paths, excludes):
        """Iterate over paths, descending directories.
        Yield a FileInfo object for each path.

        If last FileInfo object did correspond to a directory, the caller
        may send a true value to the generator to skip descending into the
        directory.  For other file types, any value sent to the generator
        will have no effect.
        """
        for p in paths:
            if p in excludes:
                continue
            try:
                info = cls(path=p)
            except ArchiveInvalidTypeError as e:
                warnings.warn(ArchiveWarning("%s ignored" % e))
                continue
            if (yield info):
                continue
            if info.is_dir():
                yield from cls.iterpaths(p.iterdir(), excludes)


class Manifest(Sequence):

    Version = "1.1"

    def __init__(self, fileobj=None, paths=None, excludes=None, tags=None):
        if fileobj is not None:
            docs = yaml.safe_load_all(fileobj)
            self.head = next(docs)
            # Legacy: version 1.0 head did not have Metadata:
            self.head.setdefault("Metadata", [])
            self.fileinfos = [ FileInfo(data=d) for d in next(docs) ]
        elif paths is not None:
            self.head = {
                "Checksums": FileInfo.Checksums,
                "Date": now_str(),
                "Generator": "archive-tools %s" % archive.__version__,
                "Metadata": [],
                "Version": self.Version,
            }
            if tags is not None:
                self.head["Tags"] = tags
            fileinfos = FileInfo.iterpaths(paths, set(excludes or ()))
            self.fileinfos = sorted(fileinfos, key=lambda fi: fi.path)
        else:
            raise TypeError("Either fileobj or paths must be provided")

    def __len__(self):
        return len(self.fileinfos)

    def __getitem__(self, index):
        return self.fileinfos.__getitem__(index)

    @property
    def version(self):
        return StrictVersion(self.head["Version"])

    @property
    def date(self):
        return parse_date(self.head["Date"])

    @property
    def checksums(self):
        return tuple(self.head["Checksums"])

    @property
    def metadata(self):
        return tuple(self.head["Metadata"])

    @property
    def tags(self):
        return tuple(self.head.get("Tags", ()))

    def add_metadata(self, path):
        self.head["Metadata"].append(str(path))

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

    def sort(self, *, key=None, reverse=False):
        if key is None:
            key = lambda fi: fi.path
        self.fileinfos.sort(key=key, reverse=reverse)
