"""Test warnings issued by the command line tool.
"""

from pathlib import Path
import socket
from tempfile import TemporaryFile
import pytest
from archive import Archive
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

def test_cli_warn_ignore_socket(test_dir, testname, monkeypatch):
    """Create an archive from a directory containing a socket.

    archive-tool.py should issue a warning that the socket has been
    ignored, but otherwise proceed to create the archive.
    """
    monkeypatch.chdir(test_dir)
    name = archive_name(tags=[testname])
    basedir = Path("base")
    fp = basedir / "socket"
    with tmp_socket(fp):
        with TemporaryFile(mode="w+t", dir=test_dir) as f:
            args = ["create", name, "base"]
            callscript("archive-tool.py", args, stderr=f)
            f.seek(0)
            line = f.readline().strip()
            assert line == ("archive-tool.py: %s: socket ignored" % fp)
    with Archive().open(Path(name)) as archive:
        assert archive.basedir == basedir
        check_manifest(archive.manifest, testdata)
        archive.verify()
