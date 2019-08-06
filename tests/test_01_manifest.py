"""Test class archive.manifest.Manifest.
"""

import datetime
from pathlib import Path
import pytest
from archive.manifest import FileInfo, Manifest
from conftest import gettestdata, setup_testdata, sub_testdata, check_manifest


# Setup a directory with some test data to be put into an archive.
# Make sure that we have all kind of different things in there.
testdata = {
    "dirs": [
        (Path("base"), 0o755),
        (Path("base", "data"), 0o750),
        (Path("base", "empty"), 0o755),
    ],
    "files": [
        (Path("base", "msg.txt"), 0o644),
        (Path("base", "data", "rnd.dat"), 0o600),
    ],
    "symlinks": [
        (Path("base", "s.dat"), Path("data", "rnd.dat")),
    ]
}

@pytest.fixture(scope="module")
def test_dir(tmpdir):
    setup_testdata(tmpdir, **testdata)
    return tmpdir


def test_manifest_from_paths(test_dir, monkeypatch):
    """Create a manifest reading the files in test_dir.
    """
    monkeypatch.chdir(str(test_dir))
    manifest = Manifest(paths=[Path("base")])
    head = manifest.head
    assert set(head.keys()) == {
        "Checksums", "Date", "Generator", "Metadata", "Version"
    }
    assert manifest.version == Manifest.Version
    assert isinstance(manifest.date, datetime.datetime)
    assert manifest.checksums == tuple(FileInfo.Checksums)
    check_manifest(manifest, **testdata)


def test_manifest_from_fileobj():
    """Read a manifest from a YAML file.
    """
    with gettestdata("manifest.yaml").open("rt") as f:
        manifest = Manifest(fileobj=f)
    head = manifest.head
    assert set(head.keys()) == {
        "Checksums", "Date", "Generator", "Metadata", "Version"
    }
    assert manifest.version == "1.1"
    assert isinstance(manifest.date, datetime.datetime)
    assert manifest.checksums == ("sha256",)
    check_manifest(manifest, **testdata)


def test_manifest_exclude_nonexistent(test_dir, monkeypatch):
    """Test excludes argument to Manifest: excluding a nonexistent file.

    This is legal, but should have no effect.
    """
    monkeypatch.chdir(str(test_dir))
    paths = [Path("base")]
    excludes = [Path("base", "non-existent.dat")]
    manifest = Manifest(paths=paths, excludes=excludes)
    data = sub_testdata(testdata, excludes[0])
    check_manifest(manifest, **data)


def test_manifest_exclude_file(test_dir, monkeypatch):
    """Test excludes: excluding one single file.
    """
    monkeypatch.chdir(str(test_dir))
    paths = [Path("base")]
    excludes = [Path("base", "msg.txt")]
    manifest = Manifest(paths=paths, excludes=excludes)
    data = sub_testdata(testdata, excludes[0])
    check_manifest(manifest, **data)


def test_manifest_exclude_subdir(test_dir, monkeypatch):
    """Test excludes: excluding a subdirectory.
    """
    monkeypatch.chdir(str(test_dir))
    paths = [Path("base")]
    excludes = [Path("base", "data")]
    manifest = Manifest(paths=paths, excludes=excludes)
    data = sub_testdata(testdata, excludes[0])
    check_manifest(manifest, **data)


def test_manifest_exclude_samelevel(test_dir, monkeypatch):
    """Test excludes: exclude things explictely named in paths.
    """
    monkeypatch.chdir(str(test_dir))
    paths = [Path("base", "data"), Path("base", "empty")]
    excludes = [paths[1]]
    manifest = Manifest(paths=paths, excludes=excludes)
    data = sub_testdata(testdata, Path("base"), paths[0])
    check_manifest(manifest, **data)


def test_manifest_exclude_explicit_include(test_dir, monkeypatch):
    """Test excludes: it is possible to explicitely include files, even if
    their parent directory is excluded.
    """
    monkeypatch.chdir(str(test_dir))
    paths = [Path("base"), Path("base", "data", "rnd.dat")]
    excludes = [Path("base", "data")]
    manifest = Manifest(paths=paths, excludes=excludes)
    data = sub_testdata(testdata, excludes[0], paths[1])
    check_manifest(manifest, **data)
