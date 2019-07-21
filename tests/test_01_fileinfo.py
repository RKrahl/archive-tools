"""Test class archive.manifest.FileInfo.
"""

from pathlib import Path
import pytest
import archive.manifest
import archive.tools
from conftest import checksums, setup_testdata


# Setup a directory with some test data.
testdata = {
    "dirs": [
        (Path("base", "data"), 0o750),
    ],
    "files": [
        (Path("base", "data", "rnd.dat"), 0o600),
    ],
}

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
    setup_testdata(tmpdir, **testdata)
    return tmpdir

def test_fileinfo_lazy_checksum(test_dir, monkeypatch):
    """Check that checksums are calculated lazily.  Ref. #35.
    """
    monkeypatch.chdir(str(test_dir))
    checksum_count = ChecksumCounter()
    p = testdata["files"][0][0]
    monkeypatch.setattr(archive.manifest, "checksum", checksum_count.checksum)
    fi = archive.manifest.FileInfo(path=p)
    assert checksum_count.counter == 0
    assert fi.checksum['sha256'] == checksums[p.name]
    assert checksum_count.counter == 1
