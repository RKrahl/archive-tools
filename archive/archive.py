"""Provide the Archive class.
"""

from enum import Enum
from pathlib import Path
import stat
import sys
import tarfile
import tempfile
from archive.manifest import Manifest
from archive.exception import *
from archive.tools import tmp_chdir, checksum

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

class DedupMode(Enum):
    NEVER = 'never'
    LINK = 'link'
    CONTENT = 'content'
    def __repr__(self):
        return '<%s.%s>' % (self.__class__.__name__, self.name)
    def __bool__(self):
        return self != self.__class__.NEVER

class MetadataItem:

    def __init__(self, path, fileobj, mode):
        self.path = path
        self.fileobj = fileobj
        self.mode = mode

class Archive:

    def __init__(self):
        self.path = None
        self.basedir = None
        self.manifest = None
        self._file = None
        self._metadata = []

    def create(self, path, compression, paths, 
               basedir=None, workdir=None, dedup=DedupMode.LINK):
        if sys.version_info < (3, 5):
            # The 'x' (exclusive creation) mode was added to tarfile
            # in Python 3.5.
            mode = 'w:' + compression
        else:
            mode = 'x:' + compression
        if workdir:
            with tmp_chdir(workdir):
                self._create(Path(workdir, path), mode, paths, basedir, dedup)
        else:
            self._create(Path(path), mode, paths, basedir, dedup)
        return self

    def _create(self, path, mode, paths, basedir, dedup):
        self.path = path
        if not paths:
            raise ArchiveCreateError("refusing to create an empty archive")
        if not basedir:
            p = Path(paths[0])
            if p.is_absolute():
                self.basedir = Path(self.path.name.split('.')[0])
            else:
                self.basedir = Path(p.parts[0])
        else:
            self.basedir = Path(basedir)
        if self.basedir.is_absolute():
            raise ArchiveCreateError("basedir must be relative")
        # We allow two different cases: either
        # - all paths are absolute, or
        # - all paths are relative and start with basedir.
        abspath = None
        _paths = []
        for p in paths:
            if not _is_normalized(p):
                raise ArchiveCreateError("invalid path %s: must be normalized" 
                                         % p)
            p = Path(p)
            if abspath is None:
                abspath = p.is_absolute()
            else:
                if abspath != p.is_absolute():
                    raise ArchiveCreateError("mixing of absolute and relative "
                                             "paths is not allowed")
            if not p.is_absolute():
                try:
                    # This will raise ValueError if p does not start
                    # with basedir:
                    p.relative_to(self.basedir)
                except ValueError as e:
                    raise ArchiveCreateError(str(e))
            _paths.append(p)
        if not abspath:
            if self.basedir.is_symlink() or not self.basedir.is_dir():
                raise ArchiveCreateError("basedir must be a directory")
        self.manifest = Manifest(paths=_paths)
        with tarfile.open(str(self.path), mode) as tarf:
            with tempfile.TemporaryFile() as tmpf:
                self.manifest.write(tmpf)
                tmpf.seek(0)
                self.add_metadata(".manifest.yaml", tmpf)
                md_names = set()
                for md in self._metadata:
                    md.path = self.basedir / md.path
                    name = str(md.path)
                    if name in md_names:
                        raise ArchiveCreateError("duplicate metadata %s" % name)
                    md_names.add(name)
                    ti = tarf.gettarinfo(arcname=name, fileobj=md.fileobj)
                    ti.mode = stat.S_IFREG | stat.S_IMODE(md.mode)
                    tarf.addfile(ti, md.fileobj)
            dupindex = {}
            for fi in self.manifest:
                p = fi.path
                name = self._arcname(p)
                if name in md_names:
                    raise ArchiveCreateError("cannot add %s: "
                                             "this filename is reserved" % p)
                if fi.is_file():
                    ti = tarf.gettarinfo(str(p), arcname=name)
                    dup = self._check_duplicate(fi, name, dedup, dupindex)
                    if dup:
                        ti.type = tarfile.LNKTYPE
                        ti.linkname = dup
                        tarf.addfile(ti)
                    else:
                        ti.size = fi.size
                        ti.type = tarfile.REGTYPE
                        ti.linkname = ''
                        with p.open("rb") as f:
                            tarf.addfile(ti, fileobj=f)
                else:
                    tarf.add(str(p), arcname=name, recursive=False)

    def _check_duplicate(self, fileinfo, name, dedup, dupindex):
        """Check if the archive item fileinfo should be linked
        to another item already added to the archive.
        """
        assert fileinfo.is_file()
        if dedup == DedupMode.LINK:
            st = fileinfo.path.stat()
            if st.st_nlink == 1:
                return None
            idxkey = (st.st_dev, st.st_ino)
        elif dedup == DedupMode.CONTENT:
            try:
                hashalg = fileinfo.Checksums[0]
            except IndexError:
                return None
            idxkey = fileinfo.checksum[hashalg]
        else:
            return None
        if idxkey in dupindex:
            return dupindex[idxkey]
        else:
            dupindex[idxkey] = name
            return None

    def add_metadata(self, name, fileobj, mode=0o444):
        md = MetadataItem(name, fileobj, mode)
        self._metadata.insert(0, md)

    def open(self, path):
        self.path = Path(path)
        try:
            self._file = tarfile.open(str(self.path), 'r')
        except OSError as e:
            raise ArchiveReadError(str(e))
        md = self.get_metadata(".manifest.yaml")
        self.basedir = md.path.parent
        self.manifest = Manifest(fileobj=md.fileobj)
        return self

    def get_metadata(self, name):
        ti = self._file.next()
        path = Path(ti.path)
        if path.name != name:
            raise ArchiveIntegrityError("%s not found" % name)
        md = MetadataItem(path, self._file.extractfile(ti), ti.mode)
        self._metadata.append(md)
        return md

    def close(self):
        if self._file:
            self._file.close()
        self._file = None

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        self.close()

    def __del__(self):
        self.close()

    def _arcname(self, p):
        if p.is_absolute():
            return str(self.basedir / p.relative_to(p.root))
        else:
            return str(p)

    def verify(self):
        if not self._file:
            raise ValueError("archive is closed.")
        for fileinfo in self.manifest:
            self._verify_item(fileinfo)

    def _verify_item(self, fileinfo):

        def _check_condition(cond, item, message):
            if not cond:
                raise ArchiveIntegrityError("%s: %s" % (item, message))

        itemname = "%s:%s" % (self.path, fileinfo.path)
        try:
            tarinfo = self._file.getmember(self._arcname(fileinfo.path))
        except KeyError:
            raise ArchiveIntegrityError("%s: missing" % itemname)
        _check_condition(tarinfo.mode == fileinfo.mode,
                         itemname, "wrong mode")
        _check_condition(int(tarinfo.mtime) == int(fileinfo.mtime),
                         itemname, "wrong modification time")
        if fileinfo.is_dir():
            _check_condition(tarinfo.isdir(),
                             itemname, "wrong type, expected directory")
        elif fileinfo.is_file():
            _check_condition(tarinfo.isfile(),
                             itemname, "wrong type, expected regular file")
            _check_condition(tarinfo.size == fileinfo.size,
                             itemname, "wrong size")
            with self._file.extractfile(tarinfo) as f:
                cs = checksum(f, fileinfo.checksum.keys())
                _check_condition(cs == fileinfo.checksum,
                                 itemname, "checksum does not match")
        elif fileinfo.is_symlink():
            _check_condition(tarinfo.issym(),
                             itemname, "wrong type, expected symbolic link")
            _check_condition(tarinfo.linkname == str(fileinfo.target),
                             itemname, "wrong link target")
        else:
            raise ArchiveIntegrityError("%s: invalid type" % (itemname))
