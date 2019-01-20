"""Provide the Manifest class that defines the archive metadata.
"""

from collections import Sequence
import grp
import hashlib
import os
import pathlib
import pwd
import stat
import yaml
import archive


def _checksum(path, hashalg):
    """Calculate hashes for a file.
    """
    if not hashalg:
        return {}
    m = { h:hashlib.new(h) for h in hashalg }
    chunksize = 8192
    with path.open('rb') as f:
        while True:
            chunk = f.read(chunksize)
            if not chunk:
                break
            for h in hashalg:
                m[h].update(chunk)
    return { h: m[h].hexdigest() for h in hashalg }


class FileInfo:

    def __init__(self, data=None, path=None):
        if data is not None:
            self.type = data['type']
            self.path = pathlib.Path(data['path'])
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
                self.target = data['target']
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
                self.checksum = _checksum(self.path, ['sha256'])
            elif stat.S_ISDIR(fstat.st_mode):
                self.type = 'd'
            elif stat.S_ISLNK(fstat.st_mode):
                self.type = 'l'
                self.target = os.readlink(str(self.path))
            else:
                raise ValueError("%s: invalid file type" % str(self.path))
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
            d['target'] = self.target
        return d


def _iterpaths(paths):
    """Iterate over paths, descending directories.
    Return a FileInfo object for each path.
    """
    for p in paths:
        info = FileInfo(path=p)
        yield info
        if info.is_dir():
            for cinfo in _iterpaths(p.iterdir()):
                yield cinfo


class Manifest(Sequence):

    def __init__(self, fileobj=None, paths=None):
        if fileobj is not None:
            self.fileinfos = [ FileInfo(data=d) for d in yaml.load(fileobj) ]
        elif paths is not None:
            self.fileinfos = list(_iterpaths(paths))
        else:
            raise TypeError("Either fileobj or paths must be provided")

    def __len__(self):
        return len(self.fileinfos)

    def __getitem__(self, index):
        return self.fileinfos.__getitem__(index)

    def write(self, fileobj):
        head = """%%YAML 1.1
# Generator: archive-tools %s
""" % (archive.__version__)
        fileobj.write(head.encode("ascii"))
        yaml.dump([ fi.as_dict() for fi in self ],
                  stream=fileobj, encoding="ascii",
                  default_flow_style=False, explicit_start=True)
