"""Tests related to the type of files while creating archives.
"""

import os
from pathlib import Path
import socket
import pytest
from archive import Archive
from archive.exception import ArchiveWarning
from conftest import *


# Setup a directory with some test data to be put into an archive.
# Make sure that we have all kind of different things in there.
testdata = [
    DataDir(Path("base"), 0o755),
    DataDir(Path("base", "data"), 0o750),
    DataDir(Path("base", "empty"), 0o755),
    DataFile(Path("base", "msg.txt"), 0o644),
    DataFile(Path("base", "data", "rnd.dat"), 0o600),
    DataSymLink(Path("base", "s.dat"), Path("data", "rnd.dat")),
]

@pytest.fixture(scope="module")
def test_dir(tmpdir):
    setup_testdata(tmpdir, testdata)
    return tmpdir

class tmp_socket():
    """A context manager temporarily creating a unix socket.
    """
    def __init__(self, path):
        self.path = path
        self.socket = socket.socket(socket.AF_UNIX)
        self.socket.bind(str(self.path))
    def __enter__(self):
        return self.socket
    def __exit__(self, type, value, tb):
        self.socket.close()
        self.path.unlink()

class tmp_fifo():
    """A context manager temporarily creating a FIFO.
    """
    def __init__(self, path):
        self.path = path
        os.mkfifo(str(self.path))
    def __enter__(self):
        return self.path
    def __exit__(self, type, value, tb):
        self.path.unlink()

def test_create_invalid_file_socket(test_dir, testname, monkeypatch):
    """Create an archive from a directory containing a socket.
    """
    monkeypatch.chdir(str(test_dir))
    name = archive_name(tags=[testname])
    p = Path("base")
    fp = p / "socket"
    with tmp_socket(fp):
        with pytest.warns(ArchiveWarning, match="%s: socket ignored" % fp):
            Archive().create(name, "", [p])
    with Archive().open(name) as archive:
        assert archive.basedir == Path("base")
        check_manifest(archive.manifest, testdata)
        archive.verify()

def test_create_invalid_file_fifo(test_dir, testname, monkeypatch):
    """Create an archive from a directory containing a FIFO.
    """
    monkeypatch.chdir(str(test_dir))
    name = archive_name(tags=[testname])
    p = Path("base")
    fp = p / "fifo"
    with tmp_fifo(fp):
        with pytest.warns(ArchiveWarning, match="%s: FIFO ignored" % fp):
            Archive().create(name, "", [p])
    with Archive().open(name) as archive:
        assert archive.basedir == Path("base")
        check_manifest(archive.manifest, testdata)
        archive.verify()
