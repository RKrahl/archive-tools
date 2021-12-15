"""Test class archive.manifest.Manifest.
"""

import datetime
from pathlib import Path
import pytest
from archive.manifest import FileInfo, Manifest
from conftest import *


# Setup a directory with some test data to be put into an archive.
# Make sure that we have all kind of different things in there.
testdata = [
    DataDir(Path("base"), 0o755, mtime=1564333266),
    DataDir(Path("base", "data"), 0o750, mtime=1564333266),
    DataDir(Path("base", "empty"), 0o755, mtime=1564333266),
    DataFile(Path("base", "msg.txt"), 0o644, mtime=1564333266),
    DataFile(Path("base", "data", "rnd.dat"), 0o600, mtime=1564333266),
    DataSymLink(Path("base", "s.dat"), Path("data", "rnd.dat"),
                mtime=1564333266),
]

@pytest.fixture(scope="module")
def test_dir(tmpdir):
    setup_testdata(tmpdir, testdata)
    return tmpdir


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
    assert manifest.tags == ()
    check_manifest(manifest, testdata)


def test_manifest_from_paths(test_dir, monkeypatch):
    """Create a manifest reading the files in test_dir.
    """
    monkeypatch.chdir(test_dir)
    manifest = Manifest(paths=[Path("base")])
    head = manifest.head
    assert set(head.keys()) == {
        "Checksums", "Date", "Generator", "Metadata", "Version"
    }
    assert manifest.version == Manifest.Version
    assert isinstance(manifest.date, datetime.datetime)
    assert manifest.checksums == tuple(FileInfo.Checksums)
    assert manifest.tags == ()
    check_manifest(manifest, testdata)


def test_manifest_exclude_nonexistent(test_dir, monkeypatch):
    """Test excludes argument to Manifest: excluding a nonexistent file.

    This is legal, but should have no effect.
    """
    monkeypatch.chdir(test_dir)
    paths = [Path("base")]
    excludes = [Path("base", "non-existent.dat")]
    manifest = Manifest(paths=paths, excludes=excludes)
    data = sub_testdata(testdata, excludes[0])
    check_manifest(manifest, data)


def test_manifest_exclude_file(test_dir, monkeypatch):
    """Test excludes: excluding one single file.
    """
    monkeypatch.chdir(test_dir)
    paths = [Path("base")]
    excludes = [Path("base", "msg.txt")]
    manifest = Manifest(paths=paths, excludes=excludes)
    data = sub_testdata(testdata, excludes[0])
    check_manifest(manifest, data)


def test_manifest_exclude_subdir(test_dir, monkeypatch):
    """Test excludes: excluding a subdirectory.
    """
    monkeypatch.chdir(test_dir)
    paths = [Path("base")]
    excludes = [Path("base", "data")]
    manifest = Manifest(paths=paths, excludes=excludes)
    data = sub_testdata(testdata, excludes[0])
    check_manifest(manifest, data)


def test_manifest_exclude_samelevel(test_dir, monkeypatch):
    """Test excludes: exclude things explictely named in paths.
    """
    monkeypatch.chdir(test_dir)
    paths = [Path("base", "data"), Path("base", "empty")]
    excludes = [paths[1]]
    manifest = Manifest(paths=paths, excludes=excludes)
    data = sub_testdata(testdata, Path("base"), paths[0])
    check_manifest(manifest, data)


def test_manifest_exclude_explicit_include(test_dir, monkeypatch):
    """Test excludes: it is possible to explicitely include files, even if
    their parent directory is excluded.
    """
    monkeypatch.chdir(test_dir)
    paths = [Path("base"), Path("base", "data", "rnd.dat")]
    excludes = [Path("base", "data")]
    manifest = Manifest(paths=paths, excludes=excludes)
    data = sub_testdata(testdata, excludes[0], paths[1])
    check_manifest(manifest, data)


def test_manifest_from_fileinfos(test_dir, monkeypatch):
    """Create a manifest providing an iterable of fileinfos.
    """
    monkeypatch.chdir(test_dir)
    fileinfos = FileInfo.iterpaths([Path("base")], set())
    manifest = Manifest(fileinfos=fileinfos)
    head = manifest.head
    assert set(head.keys()) == {
        "Checksums", "Date", "Generator", "Metadata", "Version"
    }
    assert manifest.version == Manifest.Version
    assert isinstance(manifest.date, datetime.datetime)
    assert manifest.checksums == tuple(FileInfo.Checksums)
    assert manifest.tags == ()
    check_manifest(manifest, testdata)


def test_manifest_sort(test_dir, monkeypatch):
    """Test the Manifest.sort() method.
    """
    monkeypatch.chdir(test_dir)
    manifest = Manifest(paths=[Path("base")])
    check_manifest(manifest, testdata)
    fileinfos = set(manifest)
    manifest.sort(key = lambda fi: getattr(fi, "size", 0), reverse=True)
    assert set(manifest) == fileinfos
    prev = None
    for fi in manifest:
        k = getattr(fi, "size", 0)
        if prev is not None:
            assert k <= prev
        prev = k
    manifest.sort(key = lambda fi: (fi.type, fi.path))
    assert set(manifest) == fileinfos
    prev = None
    for fi in manifest:
        if prev is not None:
            assert fi.type >= prev.type
            if fi.type == prev.type:
                assert fi.path >= prev.path
        prev = fi
    manifest.sort()
    assert set(manifest) == fileinfos
    prev = None
    for fi in manifest:
        if prev is not None:
            assert fi.path >= prev.path
        prev = fi


@pytest.mark.parametrize(("tags", "expected"), [
    (None, ()),
    ([], ()),
    (["a"], ("a",)),
    (["a", "b"], ("a", "b")),
])
def test_manifest_tags(test_dir, monkeypatch, tags, expected):
    """Set tags in a manifest reading the files in test_dir.
    """
    monkeypatch.chdir(test_dir)
    manifest = Manifest(paths=[Path("base")], tags=tags)
    assert manifest.tags == expected
