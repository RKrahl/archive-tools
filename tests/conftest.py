"""pytest configuration.
"""

import hashlib
import os
from pathlib import Path
from random import getrandbits
import shutil
import stat
import subprocess
import sys
import tempfile
import pytest
from archive.tools import ft_mode


__all__ = [
    'DataDir', 'DataFile', 'DataRandomFile', 'DataSymLink',
    'absflag', 'archive_name', 'callscript',  'check_manifest',
    'get_output', 'gettestdata', 'require_compression', 'setup_testdata',
    'sub_testdata',
]

_cleanup = True
testdir = Path(__file__).parent

def pytest_addoption(parser):
    parser.addoption("--no-cleanup", action="store_true", default=False,
                     help="do not clean up temporary data after the test.")

def pytest_configure(config):
    global _cleanup
    _cleanup = not config.getoption("--no-cleanup")

def require_compression(compression):
    """Check if the library module needed for compression is available.
    Skip if this is not the case.
    """
    msg = "%s module needed for '%s' compression is not available"
    if not compression:
        pass
    elif compression == "gz":
        try:
            import zlib
        except ImportError:
            pytest.skip(msg % ("zlib", "gz"))
    elif compression == "bz2":
        try:
            import bz2
        except ImportError:
            pytest.skip(msg % ("bz2", "bz2"))
    elif compression == "xz":
        try:
            import lzma
        except ImportError:
            pytest.skip(msg % ("lzma", "xz"))

class TmpDir(object):
    """Provide a temporary directory.
    """
    def __init__(self):
        self.dir = Path(tempfile.mkdtemp(prefix="archive-tools-test-"))
    def cleanup(self):
        if self.dir and _cleanup:
            shutil.rmtree(str(self.dir))
        self.dir = None
    def __enter__(self):
        return self.dir
    def __exit__(self, type, value, tb):
        self.cleanup()
    def __del__(self):
        self.cleanup()

@pytest.fixture(scope="module")
def tmpdir(request):
    with TmpDir() as td:
        yield td

@pytest.fixture(scope="function")
def testname(request):
    return request.function.__name__

def absflag(a):
    return "abs" if a else "rel"

_counter = {}
def archive_name(ext="", tags=(), counter=None):
    l = ["archive"]
    l.extend(tags)
    if counter:
        _counter.setdefault(counter, 0)
        _counter[counter] += 1
        l.append(str(_counter[counter]))
    name = "-".join(l)
    ext = ("tar.%s" % ext) if ext else "tar"
    return ".".join((name, ext))

def gettestdata(fname):
    path = testdir / "data" / fname
    assert path.is_file()
    return path

def _get_checksums():
    checksums_file = testdir / "data" / ".sha256"
    checksums = dict()
    with checksums_file.open("rt") as f:
        while True:
            l = f.readline()
            if not l:
                break
            cs, fp = l.split()
            checksums[fp] = cs
    return checksums

def _mk_dir(path):
    # path.mkdir(parents=True, exist_ok=True) requires Python 3.5.
    try:
        path.mkdir(parents=True)
    except FileExistsError:
        pass

def _set_fs_attrs(path, mode, mtime):
    if mode is not None:
        path.chmod(mode)
    if mtime is not None:
        os.utime(str(path), (mtime, mtime), follow_symlinks=False)

class DataItem:

    def __init__(self, path, mtime):
        self.path = path
        self.mtime = mtime

    @property
    def type(self):
        raise NotImplementedError

    @property
    def mode(self):
        raise NotImplementedError

    @property
    def st_mode(self):
        return ft_mode[self.type] | self.mode

    def create(self, main_dir):
        raise NotImplementedError

class DataFileOrDir(DataItem):

    def __init__(self, path, mode, *, mtime=None):
        super().__init__(path, mtime)
        self._mode = mode

    @property
    def mode(self):
        return self._mode

class DataDir(DataFileOrDir):

    @property
    def type(self):
        return 'd'

    def create(self, main_dir):
        path = main_dir / self.path
        _mk_dir(path)
        _set_fs_attrs(path, self.mode, self.mtime)

class DataFile(DataFileOrDir):

    Checksums = _get_checksums()

    def __init__(self, path, mode, *, mtime=None, checksum=None):
        super().__init__(path, mode, mtime=mtime)
        self._checksum = checksum

    @property
    def type(self):
        return 'f'

    @property
    def checksum(self):
        return self._checksum or self.Checksums[self.path.name]

    def create(self, main_dir):
        path = main_dir / self.path
        _mk_dir(path.parent)
        shutil.copy(str(gettestdata(self.path.name)), str(path))
        _set_fs_attrs(path, self.mode, self.mtime)

class DataRandomFile(DataFileOrDir):

    def __init__(self, path, mode, *, mtime=None, size=1024):
        super().__init__(path, mode, mtime=mtime)
        self._size = size

    @property
    def type(self):
        return 'f'

    @property
    def checksum(self):
        return self._checksum

    def create(self, main_dir):
        path = main_dir / self.path
        h = hashlib.new("sha256")
        data = bytearray(getrandbits(8) for _ in range(self._size))
        h.update(data)
        self._checksum = h.hexdigest()
        _mk_dir(path.parent)
        with path.open("wb") as f:
            f.write(data)
        _set_fs_attrs(path, self.mode, self.mtime)

class DataSymLink(DataItem):

    def __init__(self, path, target, *, mtime=None):
        super().__init__(path, mtime)
        self.target = target

    @property
    def type(self):
        return 'l'

    @property
    def mode(self):
        return 0o777

    def create(self, main_dir):
        path = main_dir / self.path
        _mk_dir(path.parent)
        path.symlink_to(self.target)
        _set_fs_attrs(path, None, self.mtime)

def setup_testdata(main_dir, items):
    for item in sorted(items, key=lambda i: i.path, reverse=True):
        item.create(main_dir)

def sub_testdata(items, exclude, include=None):
    """Compile a subset of the testdata with some items removed.
    """
    def _startswith(p, o):
        try:
            p.relative_to(o)
            return True
        except ValueError:
            return False
    for item in items:
        if _startswith(item.path, exclude):
            if include and _startswith(item.path, include):
                pass
            else:
                continue
        yield item

def check_manifest(manifest, items, prefix_dir=Path(".")):
    items = sorted(items, key=lambda i: i.path)
    assert len(manifest) == len(items)
    for entry, fileinfo in zip(items, manifest):
        assert fileinfo.type == entry.type
        assert fileinfo.path == prefix_dir / entry.path
        if entry.type == "d":
            assert fileinfo.mode == entry.mode
            if entry.mtime is not None:
                assert int(fileinfo.mtime) == int(entry.mtime)
        elif entry.type == "f":
            assert fileinfo.mode == entry.mode
            if entry.mtime is not None:
                assert int(fileinfo.mtime) == int(entry.mtime)
            assert fileinfo.checksum['sha256'] == entry.checksum
        elif entry.type == "l":
            assert fileinfo.target == entry.target

def callscript(scriptname, args, returncode=0,
               stdin=None, stdout=None, stderr=None):
    try:
        script_dir = os.environ['BUILD_SCRIPTS_DIR']
    except KeyError:
        pytest.skip("BUILD_SCRIPTS_DIR is not set.")
    script = Path(script_dir, scriptname)
    cmd = [sys.executable, str(script)] + args
    print("\n>", *cmd)
    retcode = subprocess.call(cmd, stdin=stdin, stdout=stdout, stderr=stderr)
    assert retcode == returncode

def get_output(fileobj):
    while True:
        line = fileobj.readline()
        if not line:
            break
        line = line.strip()
        print("< %s" % line)
        yield line
