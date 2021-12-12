"""Test creating an archive from an iterable of FileInfo objects.
"""

from pathlib import Path
import pytest
from archive import Archive
from archive.manifest import FileInfo, Manifest
from conftest import *


# Setup a directory with some test data to be put into an archive.
# Make sure that we have all kind of different things in there.
testdata = [
    DataDir(Path("base"), 0o755, mtime=1565100853),
    DataDir(Path("base", "data"), 0o750, mtime=1555271302),
    DataDir(Path("base", "empty"), 0o755, mtime=1547911753),
    DataFile(Path("base", "msg.txt"), 0o644, mtime=1547911753),
    DataFile(Path("base", "data", "rnd.dat"), 0o600, mtime=1563112510),
    DataSymLink(Path("base", "s.dat"), Path("data", "rnd.dat"),
                mtime=1565100853),
]
sha256sum = "sha256sum"

@pytest.fixture(scope="module")
def test_dir(tmpdir):
    setup_testdata(tmpdir, testdata)
    return tmpdir


def test_create_fileinfos_list(test_dir, monkeypatch):
    """Create the archive from a list of FileInfo objects.
    """
    monkeypatch.chdir(test_dir)
    fileinfos = list(FileInfo.iterpaths([Path("base")], set()))
    archive_path = Path("archive-fi-list.tar")
    Archive().create(archive_path, "", fileinfos=fileinfos)
    with Archive().open(archive_path) as archive:
        check_manifest(archive.manifest, testdata)
        archive.verify()

def test_create_fileinfos_generator(test_dir, monkeypatch):
    """Create the archive from FileInfo.iterpaths() which returns a generator.
    """
    monkeypatch.chdir(test_dir)
    fileinfos = FileInfo.iterpaths([Path("base")], set())
    archive_path = Path("archive-fi-generator.tar")
    Archive().create(archive_path, "", fileinfos=fileinfos)
    with Archive().open(archive_path) as archive:
        check_manifest(archive.manifest, testdata)
        archive.verify()

def test_create_fileinfos_manifest(test_dir, monkeypatch):
    """Create the archive from a Manifest.
    A Manifest is an iterable of FileInfo objects.
    """
    monkeypatch.chdir(test_dir)
    manifest = Manifest(paths=[Path("base")])
    archive_path = Path("archive-fi-manifest.tar")
    Archive().create(archive_path, "", fileinfos=manifest)
    with Archive().open(archive_path) as archive:
        check_manifest(archive.manifest, testdata)
        archive.verify()

def test_create_fileinfos_subset(test_dir, monkeypatch):
    """Do not include the content of a directory.
    This test verifies that creating an archive from fileinfos does
    not implicitly descend subdirectories.
    """
    monkeypatch.chdir(test_dir)
    excludes = [Path("base", "data", "rnd.dat")]
    fileinfos = FileInfo.iterpaths([Path("base")], set(excludes))
    data = sub_testdata(testdata, excludes[0])
    archive_path = Path("archive-fi-subset.tar")
    Archive().create(archive_path, "", fileinfos=fileinfos)
    with Archive().open(archive_path) as archive:
        check_manifest(archive.manifest, data)
        archive.verify()
