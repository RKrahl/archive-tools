"""Provide the Archive class.
"""

from collections.abc import Sequence
from enum import Enum
import itertools
import os
from pathlib import Path
import stat
import sys
import tarfile
import tempfile
from archive.manifest import Manifest
from archive.exception import *
from archive.tools import checksum

def _is_normalized(p):
    """Check if the path is normalized.
    """
    p = Path.cwd() / p
    if p.resolve() == p:
        return True
    if p.is_symlink():
        return p.parent.resolve() == p.parent
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

    def __init__(self, name=None, path=None, tarinfo=None, fileobj=None,
                 mode=None):
        self.name = name
        self.path = path
        self.fileobj = fileobj
        self.tarinfo = tarinfo
        self.mode = mode
        if self.path and self.name is None:
            self.name = self.path.name
        if self.tarinfo and self.mode is None:
            self.mode = self.tarinfo.mode

    def set_path(self, basedir):
        self.path = basedir / self.name


compression_map = {
    '.tar': '',
    '.tar.gz': 'gz',
    '.tar.bz2': 'bz2',
    '.tar.xz': 'xz',
}
"""Map path suffix to compression mode."""


class Archive:

    def __init__(self):
        self.path = None
        self.basedir = None
        self.manifest = None
        self._file = None
        self._metadata = []
        self._dedup = None
        self._dupindex = None

    def create(self, path, compression=None, paths=None, fileinfos=None,
               basedir=None, workdir=None, excludes=None,
               dedup=DedupMode.LINK, tags=None):
        if compression is None:
            try:
                compression = compression_map["".join(path.suffixes)]
            except KeyError:
                # Last ressort default
                compression = 'gz'
        mode = 'x:' + compression
        save_wd = None
        try:
            if workdir:
                save_wd = os.getcwd()
                os.chdir(workdir)
            self.path = path.resolve()
            self._dedup = dedup
            self._dupindex = {}
            if fileinfos is not None:
                if not isinstance(fileinfos, Sequence):
                    fileinfos = list(fileinfos)
                self._check_paths([fi.path for fi in fileinfos], basedir)
                try:
                    self.manifest = Manifest(fileinfos=fileinfos, tags=tags)
                except ValueError as e:
                    raise ArchiveCreateError("invalid fileinfos: %s" % e)
            else:
                self._check_paths(paths, basedir, excludes)
                self.manifest = Manifest(paths=paths, excludes=excludes,
                                         tags=tags)
            bd_fi = self.manifest.find(self.basedir)
            if bd_fi and not bd_fi.is_dir():
                raise ArchiveCreateError("base directory %s must "
                                         "be a directory" % self.basedir)
            self.manifest.add_metadata(self.basedir / ".manifest.yaml")
            for md in self._metadata:
                md.set_path(self.basedir)
                self.manifest.add_metadata(md.path)
            self._create(mode)
        finally:
            if save_wd:
                os.chdir(save_wd)
        return self

    def _create(self, mode):
        with tarfile.open(self.path, mode, format=tarfile.PAX_FORMAT) as tarf:
            with tempfile.TemporaryFile() as tmpf:
                self.manifest.write(tmpf)
                tmpf.seek(0)
                self.add_metadata(".manifest.yaml", tmpf)
                md_names = self._add_metadata_files(tarf)
            for fi in self.manifest:
                arcname = self._arcname(fi.path)
                if arcname in md_names:
                    raise ArchiveCreateError("invalid path '%s': this "
                                             "filename is reserved" % fi.path)
                self._add_item(tarf, fi, arcname)

    def _add_item(self, tarf, fi, arcname):
        ti = tarf.gettarinfo(str(fi.path), arcname=arcname)
        if fi.is_file():
            dup = self._check_duplicate(fi, arcname)
            if dup:
                ti.type = tarfile.LNKTYPE
                ti.linkname = dup
                tarf.addfile(ti)
            else:
                ti.size = fi.size
                ti.type = tarfile.REGTYPE
                ti.linkname = ''
                with fi.path.open("rb") as f:
                    tarf.addfile(ti, fileobj=f)
        else:
            tarf.addfile(ti)

    def _check_paths(self, paths, basedir, excludes=None):
        """Check the paths to be added to an archive for several error
        conditions.  Accept a list of path-like objects.  Also sets
        self.basedir.
        """
        if not paths:
            raise ArchiveCreateError("refusing to create an empty archive")
        abspath = paths[0].is_absolute()
        if not basedir:
            if abspath:
                self.basedir = Path(self.path.name.split('.')[0])
            else:
                self.basedir = Path(paths[0].parts[0])
        else:
            self.basedir = basedir
        if self.basedir.is_absolute():
            raise ArchiveCreateError("basedir must be relative")
        # We allow two different cases: either
        # - all paths are absolute, or
        # - all paths are relative and start with basedir.
        # The same rules for paths also apply to excludes, if
        # provided.  So we may just iterate over the chain of both
        # lists.
        for p in itertools.chain(paths, excludes or ()):
            if not _is_normalized(p):
                raise ArchiveCreateError("invalid path '%s': "
                                         "must be normalized" % p)
            if abspath != p.is_absolute():
                raise ArchiveCreateError("mixing of absolute and relative "
                                         "paths is not allowed")
            if not p.is_absolute():
                try:
                    # This will raise ValueError if p does not start
                    # with basedir:
                    p.relative_to(self.basedir)
                except ValueError:
                    raise ArchiveCreateError("invalid path '%s': must be a "
                                             "subpath of base directory %s"
                                             % (p, self.basedir))

    def _add_metadata_files(self, tarf):
        """Add the metadata files to the tar file.
        """
        md_names = set()
        for md in self._metadata:
            name = str(md.path)
            if name in md_names:
                raise ArchiveCreateError("duplicate metadata '%s'" % name)
            md_names.add(name)
            ti = tarf.gettarinfo(arcname=name, fileobj=md.fileobj)
            ti.mode = stat.S_IFREG | stat.S_IMODE(md.mode)
            tarf.addfile(ti, md.fileobj)
        return md_names

    def _check_duplicate(self, fileinfo, name):
        """Check if the archive item fileinfo should be linked
        to another item already added to the archive.
        """
        assert fileinfo.is_file()
        if self._dedup == DedupMode.LINK:
            st = fileinfo.path.stat()
            if st.st_nlink == 1:
                return None
            idxkey = (st.st_dev, st.st_ino)
        elif self._dedup == DedupMode.CONTENT:
            try:
                hashalg = fileinfo.Checksums[0]
            except IndexError:
                return None
            idxkey = fileinfo.checksum[hashalg]
        else:
            return None
        if idxkey in self._dupindex:
            return self._dupindex[idxkey]
        else:
            self._dupindex[idxkey] = name
            return None

    def add_metadata(self, name, fileobj, mode=0o444):
        path = self.basedir / name if self.basedir else None
        md = MetadataItem(name=name, path=path, fileobj=fileobj, mode=mode)
        self._metadata.insert(0, md)

    def open(self, path):
        try:
            self._file = tarfile.open(path, 'r')
        except OSError as e:
            raise ArchiveReadError(str(e))
        self.path = path.resolve()
        md = self.get_metadata(".manifest.yaml")
        self.basedir = md.path.parent
        self.manifest = Manifest(fileobj=md.fileobj)
        if not self.manifest.metadata:
            # Legacy: Manifest version 1.0 did not have metadata.
            self.manifest.add_metadata(self.basedir / ".manifest.yaml")
        return self

    def get_metadata(self, name):
        ti = self._file.next()
        path = Path(ti.path)
        if path.name != name:
            raise ArchiveIntegrityError("metadata item '%s' not found" % name)
        fileobj = self._file.extractfile(ti)
        md = MetadataItem(path=path, tarinfo=ti, fileobj=fileobj)
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
        # Verify that all metadata items are present in the proper
        # order at the beginning of the tar file.  Start iterating for
        # TarInfo objects in the tarfile from the beginning,
        # regardless of what has already been read:
        tarf_it = iter(self._file)
        for md in self.manifest.metadata:
            ti = next(tarf_it)
            if ti.name != md:
                raise ArchiveIntegrityError("metadata item '%s' not found"
                                            % md)
        # Check the content of the archive.
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
            _check_condition(tarinfo.isfile() or tarinfo.islnk(),
                             itemname, "wrong type, expected regular file")
            if tarinfo.isfile():
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

    def extract_member(self, fi, targetdir):
        arcname = self._arcname(fi.path)
        mtimes = (fi.mtime, fi.mtime)
        self._file.extract(arcname, path=str(targetdir))
        os.utime(targetdir / arcname, mtimes, follow_symlinks=False)

    def extract(self, targetdir, inclmeta=False):
        # We extract the directories last in reverse order.  This way,
        # the directory attributes, in particular the file modification
        # time, is set correctly after the file content is written into
        # the directory.
        dirstack = []
        if inclmeta:
            for mi in self.manifest.metadata:
                self._file.extract(mi, path=str(targetdir))
        for fi in self.manifest:
            if fi.is_dir():
                dirstack.append(fi)
            else:
                self.extract_member(fi, targetdir)
        while True:
            try:
                fi = dirstack.pop()
            except IndexError:
                break
            self.extract_member(fi, targetdir)
