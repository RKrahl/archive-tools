"""Provide the Archive class.
"""

from pathlib import Path
import stat
import sys
import tarfile
import tempfile
from archive.manifest import Manifest

def _is_normalized(p):
    """Check if the path is normalized.
    """
    p = Path.cwd() / p
    if p.resolve() == p:
        return True
    if p.is_symlink():
        return p.resolve().parent == p.parent
    else:
        return False

class Archive:

    def __init__(self, path, mode='r', paths=None, basedir=None):
        self.path = Path(path)
        if mode.startswith('r'):
            self._read_manifest(mode)
        elif mode.startswith('x'):
            if sys.version_info < (3, 5):
                # The 'x' (exclusive creation) mode was added to
                # tarfile in Python 3.5.
                mode = 'w' + mode[1:]
            self._create(mode, paths, basedir)
        else:
            raise ValueError("invalid mode '%s'" % mode)

    def _create(self, mode, paths, basedir):
        if not paths:
            raise ValueError("refusing to create an empty archive")
        if not basedir:
            p = Path(paths[0])
            if p.is_absolute():
                basedir = Path(self.path.name.split('.')[0])
            else:
                basedir = Path(p.parts[0])
        self.basedir = Path(basedir)
        if self.basedir.is_absolute():
            raise ValueError("basedir must be relative")
        # We allow two different cases: either
        # - all paths are absolute, or
        # - all paths are relative and start with basedir.
        abspath = None
        _paths = []
        for p in paths:
            if not _is_normalized(p):
                raise ValueError("invalid path %s: must be normalized" % p)
            p = Path(p)
            if abspath is None:
                abspath = p.is_absolute()
            else:
                if abspath != p.is_absolute():
                    raise ValueError("mixing of absolute and relative "
                                     "paths is not allowed")
            if not p.is_absolute():
                # This will raise ValueError if p does not start
                # with basedir:
                p.relative_to(self.basedir)
            _paths.append(p)
        if not abspath:
            if self.basedir.is_symlink() or not self.basedir.is_dir():
                raise ValueError("basedir must be a directory")
        self.manifest = Manifest(paths=_paths)
        with tarfile.open(str(self.path), mode) as tarf:
            with tempfile.TemporaryFile() as tmpf:
                self.manifest.write(tmpf)
                tmpf.seek(0)
                name = str(self.basedir / ".manifest.yaml")
                manifest_info = tarf.gettarinfo(arcname=name, fileobj=tmpf)
                manifest_info.mode = stat.S_IFREG | 0o444
                tarf.addfile(manifest_info, tmpf)
            for fi in self.manifest:
                p = fi.path
                if p.is_absolute():
                    name = str(self.basedir / p.relative_to(p.anchor))
                else:
                    name = str(p)
                tarf.add(str(p), arcname=name, recursive=False)

    def _read_manifest(self, mode):
        assert mode.startswith('r')
        with tarfile.open(str(self.path), mode) as tarf:
            ti = tarf.next()
            path = Path(ti.path)
            if path.name != ".manifest.yaml":
                raise ValueError("invalid archive: manifest not found")
            self.basedir = path.parent
            self.manifest = Manifest(fileobj=tarf.extractfile(ti))
