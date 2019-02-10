"""Misc issues around creating an archive.
"""

from pathlib import Path
import pytest
from archive import Archive
from conftest import tmpdir, setup_testdata, check_manifest


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


def test_create__default_basedir_rel(test_dir, monkeypatch):
    """Check the default basedir with relative paths.
    """
    monkeypatch.chdir(str(test_dir))
    archive_path = "archive-rel.tar"
    p = Path("base", "data")
    Archive(archive_path, mode="x:", paths=[p])
    archive = Archive(archive_path, mode="r")
    assert archive.basedir == Path("base")
    check_manifest(archive.manifest, **testdata)


def test_create__default_basedir_abs(test_dir, monkeypatch):
    """Check the default basedir with absolute paths.
    """
    monkeypatch.chdir(str(test_dir))
    archive_path = "archive-abs.tar"
    p = test_dir / Path("base", "data")
    Archive(archive_path, mode="x:", paths=[p])
    archive = Archive(archive_path, mode="r")
    assert archive.basedir == Path("archive-abs")
    check_manifest(archive.manifest, prefix_dir=test_dir, **testdata)
