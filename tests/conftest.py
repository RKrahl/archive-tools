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

def setup_testdata(main_dir, dirs=[], files=[], symlinks=[]):
    for d, m in dirs:
        p = main_dir / d
        p.mkdir(parents=True)
        p.chmod(m)
    for f, m in files:
        p = main_dir / f
        shutil.copy(str(gettestdata(f.name)), str(p))
        p.chmod(m)
    for f, t in symlinks:
        p = main_dir / f
        p.symlink_to(t)

def sub_testdata(data, exclude, include=None):
    """Compile a subset of the testdata with some items removed.
    """
    def _startswith(p, o):
        try:
            p.relative_to(o)
            return True
        except ValueError:
            return False
    sd = {}
    for k in data.keys():
        items = []
        for i in data[k]:
            if _startswith(i[0], exclude):
                if include and _startswith(i[0], include):
                    pass
                else:
                    continue
            items.append(i)
        sd[k] = items
    return sd

def get_testdata_items(prefix_dir=None, dirs=[], files=[], symlinks=[]):
    items = []
    for p, m in dirs:
        if prefix_dir:
            p = prefix_dir / p
        items.append({"Path": p, "Type": "d", "Mode": m, 
                      "st_Mode": (stat.S_IFDIR | m)})
    for p, m in files:
        if prefix_dir:
            p = prefix_dir / p
        items.append({"Path": p, "Type": "f", "Mode": m, 
                      "st_Mode": (stat.S_IFREG | m)})
    for p, t in symlinks:
        if prefix_dir:
            p = prefix_dir / p
        items.append({"Path": p, "Type": "l", "Mode": 0o777, 
                      "st_Mode": (stat.S_IFLNK | 0o777), "Target": t})
    items.sort(key=lambda e: e["Path"])
    return items

def check_manifest(manifest, prefix_dir=None, dirs=[], files=[], symlinks=[]):
    items = get_testdata_items(prefix_dir, dirs, files, symlinks)
    assert len(manifest) == len(items)
    for entry, fileinfo in zip(items, manifest):
        assert fileinfo.type == entry["Type"]
        assert fileinfo.path == entry["Path"]
        if entry["Type"] == "d":
            assert fileinfo.mode == entry["Mode"]
        elif entry["Type"] == "f":
            assert fileinfo.mode == entry["Mode"]
            assert fileinfo.checksum['sha256'] == checksums[entry["Path"].name]
        elif entry["Type"] == "l":
            assert fileinfo.target == entry["Target"]

def callscript(scriptname, args, stdin=None, stdout=None, stderr=None):
    try:
        script_dir = os.environ['BUILD_SCRIPTS_DIR']
    except KeyError:
        pytest.skip("BUILD_SCRIPTS_DIR is not set.")
    script = Path(script_dir, scriptname)
    cmd = [sys.executable, str(script)] + args
    print("\n>", *cmd)
    subprocess.check_call(cmd, stdin=stdin, stdout=stdout, stderr=stderr)
