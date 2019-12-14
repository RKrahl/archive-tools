"""pytest configuration.
"""

import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import pytest
from archive.tools import ft_mode


_cleanup = True
testdir = Path(__file__).parent

def pytest_addoption(parser):
    parser.addoption("--no-cleanup", action="store_true", default=False,
                     help="do not clean up temporary data after the test.")

def pytest_configure(config):
    global _cleanup
    _cleanup = not config.getoption("--no-cleanup")

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

checksums = _get_checksums()

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
def archive_name(request):
    return "archive-%s.tar" % request.function.__name__

class TestDataItem:

    def __init__(self, path):
        self.path = path

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

class TestDataFileOrDir(TestDataItem):

    def __init__(self, path, mode):
        super().__init__(path)
        self._mode = mode

    @property
    def mode(self):
        return self._mode

class TestDataDir(TestDataFileOrDir):

    @property
    def type(self):
        return 'd'

    def create(self, main_dir):
        path = main_dir / self.path
        path.mkdir(parents=True)
        path.chmod(self.mode)

class TestDataFile(TestDataFileOrDir):

    @property
    def type(self):
        return 'f'

    def create(self, main_dir):
        path = main_dir / self.path
        shutil.copy(str(gettestdata(self.path.name)), str(path))
        path.chmod(self.mode)

class TestDataSymLink(TestDataItem):

    def __init__(self, path, target):
        super().__init__(path)
        self.target = target

    @property
    def type(self):
        return 'l'

    @property
    def mode(self):
        return 0o777

    def create(self, main_dir):
        path = main_dir / self.path
        path.symlink_to(self.target)

def setup_testdata(main_dir, items):
    for item in sorted(items, key=lambda i: i.path):
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
        elif entry.type == "f":
            assert fileinfo.mode == entry.mode
            assert fileinfo.checksum['sha256'] == checksums[entry.path.name]
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
