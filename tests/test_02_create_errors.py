"""Test error conditions during creating an archive.
"""

from pathlib import Path
import pytest
from archive import Archive
from archive.exception import ArchiveCreateError
from conftest import archive_name, setup_testdata


# Setup a directory with some test data to be put into an archive.
# Make sure that we have all kind if different things in there.
testdata = {
    "dirs": [
        (Path("base"), 0o755),
        (Path("base", "empty"), 0o755),
        (Path("base", "data"), 0o755),
        (Path("other"), 0o755),
    ],
    "files": [
        (Path("base", "msg.txt"), 0o644),
        (Path("other", "rnd.dat"), 0o600),
        (Path("msg.txt"), 0o644),
    ],
}

@pytest.fixture(scope="module")
def test_dir(tmpdir):
    setup_testdata(tmpdir, **testdata)
    return tmpdir

def test_create_empty(test_dir, archive_name, monkeypatch):
    """Creating an empty archive will be refused.
    """
    monkeypatch.chdir(str(test_dir))
    with pytest.raises(ArchiveCreateError):
        Archive(archive_name, mode="x:", paths=[], basedir="base")

def test_create_abs_basedir(test_dir, archive_name, monkeypatch):
    """Base dir must be a a relative path.
    """
    monkeypatch.chdir(str(test_dir))
    basedir = test_dir / "base"
    with pytest.raises(ArchiveCreateError):
        Archive(archive_name, mode="x:", paths=["base"], basedir=basedir)

def test_create_mixing_abs_rel(test_dir, archive_name, monkeypatch):
    """Mixing absolute and relative paths is not allowed.
    """
    monkeypatch.chdir(str(test_dir))
    paths = [ Path("base", "msg.txt"), test_dir / "base" / "data" ]
    with pytest.raises(ArchiveCreateError):
        Archive(archive_name, mode="x:", paths=paths, basedir="base")

def test_create_rel_not_in_base(test_dir, archive_name, monkeypatch):
    """Relative paths must be in the base directory.
    """
    monkeypatch.chdir(str(test_dir))
    paths = [ Path("other", "rnd.dat") ]
    with pytest.raises(ArchiveCreateError):
        Archive(archive_name, mode="x:", paths=paths, basedir="base")

def test_create_norm_path(test_dir, archive_name, monkeypatch):
    """Items in paths must be normalized.  (Issue #6)
    """
    monkeypatch.chdir(str(test_dir))
    paths = [ "base", "base/../../../etc/passwd" ]
    with pytest.raises(ArchiveCreateError):
        Archive(archive_name, mode="x:", paths=paths, basedir="base")

def test_create_rel_check_basedir(test_dir, archive_name, monkeypatch):
    """Base directory must be a directory.  (Issue #9)
    """
    monkeypatch.chdir(str(test_dir))
    p = Path("msg.txt")
    with pytest.raises(ArchiveCreateError):
        Archive(archive_name, mode="x:", paths=[p], basedir=p)

def test_create_rel_no_manifest_file(test_dir, archive_name, monkeypatch):
    """The filename .manifest.yaml is reserved by archive-tools.

    If created with relative paths, the archive content must not have
    an actual file with that name in the base directory.  (Issue #10)

    Note that we can only test this case with relative paths.  The
    case using absolute paths would mean adding a file named
    /.manifest.yaml to the archive.  Obviously, we cannot create such
    a file for the test.
    """
    monkeypatch.chdir(str(test_dir))
    base = Path("base")
    manifest = base / ".manifest.yaml"
    with manifest.open("wt") as f:
        print("This is not a YAML file!", file=f)
    try:
        with pytest.raises(ArchiveCreateError):
            Archive(archive_name, mode="x:", paths=[base])
    finally:
        manifest.unlink()
