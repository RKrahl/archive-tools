"""Test class archive.manifest.FileInfo.
"""

from pathlib import Path
import pytest
import archive.manifest
import archive.tools
from conftest import setup_testdata, DataDir, DataFile


# Setup a directory with some test data.
testdata = [
    DataDir(Path("base", "data"), 0o750),
    DataFile(Path("base", "data", "rnd.dat"), 0o600),
]

class ChecksumCounter():
    """Call archive.tools.checksum(), counting the number of calls.
    """
    def __init__(self):
        self.counter = 0
    def checksum(self, *args):
        self.counter += 1
        return archive.tools.checksum(*args)

@pytest.fixture(scope="module")
def test_dir(tmpdir):
    setup_testdata(tmpdir, testdata)
    return tmpdir

def test_fileinfo_lazy_checksum(test_dir, monkeypatch):
    """Check that checksums are calculated lazily.  Ref. #35.
    """
    monkeypatch.chdir(test_dir)
    checksum_count = ChecksumCounter()
    entry = next(filter(lambda i: i.type == 'f', testdata))
    monkeypatch.setattr(archive.manifest, "checksum", checksum_count.checksum)
    fi = archive.manifest.FileInfo(path=entry.path)
    assert checksum_count.counter == 0
    assert fi.checksum['sha256'] == entry.checksum
    assert checksum_count.counter == 1
