"""Misc issues around creating an archive.
"""

from pathlib import Path
import pytest
from archive import Archive
from conftest import setup_testdata, check_manifest


# Setup a directory with some test data to be put into an archive.
# Make sure that we have all kind if different things in there.
testdata = {
    "dirs": [
        (Path("base", "data"), 0o755),
        (Path("base", "data", "misc"), 0o755),
        (Path("base", "data", "other"), 0o755),
    ],
    "files": [
        (Path("base", "data", "misc", "rnd.dat"), 0o644),
    ],
}

@pytest.fixture(scope="module")
def test_dir(tmpdir):
    setup_testdata(tmpdir, **testdata)
    return tmpdir


def test_create_default_basedir_rel(test_dir, monkeypatch):
    """Check the default basedir with relative paths.  (Issue #8)
    """
    monkeypatch.chdir(str(test_dir))
    archive_path = "archive-rel.tar"
    p = Path("base", "data")
    Archive(archive_path, mode="x:", paths=[p])
    archive = Archive(archive_path, mode="r")
    assert archive.basedir == Path("base")
    check_manifest(archive.manifest, **testdata)
    archive.verify()

def test_create_default_basedir_abs(test_dir, monkeypatch):
    """Check the default basedir with absolute paths.  (Issue #8)
    """
    monkeypatch.chdir(str(test_dir))
    archive_path = "archive-abs.tar"
    p = test_dir / Path("base", "data")
    Archive(archive_path, mode="x:", paths=[p])
    archive = Archive(archive_path, mode="r")
    assert archive.basedir == Path("archive-abs")
    check_manifest(archive.manifest, prefix_dir=test_dir, **testdata)
    archive.verify()

def test_create_sorted(test_dir, monkeypatch):
    """The entries in the manifest should be sorted.  (Issue #11)
    """
    monkeypatch.chdir(str(test_dir))
    archive_path = "archive-sort.tar"
    files = [ Path("base", fn) for fn in ("c", "a", "d", "b") ]
    for p in files:
        with p.open("wt") as f:
            print("Some content for file %s" % p, file=f)
    try:
        Archive(archive_path, mode="x:", paths=files)
        archive = Archive(archive_path, mode="r")
        assert [fi.path for fi in archive.manifest] == sorted(files)
        archive.verify()
    finally:
        for p in files:
            p.unlink()
