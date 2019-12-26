"""Test error conditions during creating an archive.
"""

from pathlib import Path
from tempfile import TemporaryFile
import pytest
from archive import Archive
from archive.exception import ArchiveCreateError
from conftest import *


# Setup a directory with some test data to be put into an archive.
# Make sure that we have all kind of different things in there.
testdata = [
    DataDir(Path("base"), 0o755),
    DataDir(Path("base", "empty"), 0o755),
    DataDir(Path("base", "data"), 0o755),
    DataDir(Path("other"), 0o755),
    DataFile(Path("base", "msg.txt"), 0o644),
    DataFile(Path("other", "rnd.dat"), 0o600),
    DataFile(Path("msg.txt"), 0o644),
]

@pytest.fixture(scope="module")
def test_dir(tmpdir):
    setup_testdata(tmpdir, testdata)
    return tmpdir

def test_create_empty(test_dir, testname, monkeypatch):
    """Creating an empty archive will be refused.
    """
    monkeypatch.chdir(str(test_dir))
    name = archive_name(tags=[testname])
    with pytest.raises(ArchiveCreateError):
        Archive().create(Path(name), "", [], basedir=Path("base"))

def test_create_abs_basedir(test_dir, testname, monkeypatch):
    """Base dir must be a a relative path.
    """
    monkeypatch.chdir(str(test_dir))
    name = archive_name(tags=[testname])
    paths = [Path("base")]
    basedir = test_dir / "base"
    with pytest.raises(ArchiveCreateError):
        Archive().create(Path(name), "", paths, basedir=basedir)

def test_create_mixing_abs_rel(test_dir, testname, monkeypatch):
    """Mixing absolute and relative paths is not allowed.
    """
    monkeypatch.chdir(str(test_dir))
    name = archive_name(tags=[testname])
    paths = [ Path("base", "msg.txt"), test_dir / "base" / "data" ]
    with pytest.raises(ArchiveCreateError):
        Archive().create(Path(name), "", paths, basedir=Path("base"))

def test_create_rel_not_in_base(test_dir, testname, monkeypatch):
    """Relative paths must be in the base directory.
    """
    monkeypatch.chdir(str(test_dir))
    name = archive_name(tags=[testname])
    paths = [ Path("other", "rnd.dat") ]
    with pytest.raises(ArchiveCreateError):
        Archive().create(Path(name), "", paths, basedir=Path("base"))

def test_create_norm_path(test_dir, testname, monkeypatch):
    """Items in paths must be normalized.  (Issue #6)
    """
    monkeypatch.chdir(str(test_dir))
    name = archive_name(tags=[testname])
    paths = [ Path("base"), Path("base/../../../etc/passwd") ]
    with pytest.raises(ArchiveCreateError):
        Archive().create(Path(name), "", paths, basedir=Path("base"))

def test_create_rel_check_basedir(test_dir, testname, monkeypatch):
    """Base directory must be a directory.  (Issue #9)
    """
    monkeypatch.chdir(str(test_dir))
    name = archive_name(tags=[testname])
    p = Path("msg.txt")
    with pytest.raises(ArchiveCreateError):
        Archive().create(Path(name), "", [p], basedir=p)

def test_create_rel_no_manifest_file(test_dir, testname, monkeypatch):
    """The filename .manifest.yaml is reserved by archive-tools.

    If created with relative paths, the archive content must not have
    an actual file with that name in the base directory.  (Issue #10)

    Note that we can only test this case with relative paths.  The
    case using absolute paths would mean adding a file named
    /.manifest.yaml to the archive.  Obviously, we cannot create such
    a file for the test.
    """
    monkeypatch.chdir(str(test_dir))
    name = archive_name(tags=[testname])
    base = Path("base")
    manifest = base / ".manifest.yaml"
    with manifest.open("wt") as f:
        print("This is not a YAML file!", file=f)
    try:
        with pytest.raises(ArchiveCreateError):
            Archive().create(Path(name), "", [base])
    finally:
        manifest.unlink()

def test_create_duplicate_metadata(test_dir, testname, monkeypatch):
    """Add additional custom metadata to the archive,
    using a name that is already taken.
    """
    monkeypatch.chdir(str(test_dir))
    name = archive_name(tags=[testname])
    p = Path("base")
    with TemporaryFile(dir=str(test_dir)) as tmpf:
        archive = Archive()
        tmpf.write("Hello world!\n".encode("ascii"))
        tmpf.seek(0)
        with pytest.raises(ArchiveCreateError) as err:
            archive.add_metadata(".manifest.yaml", tmpf)
            archive.create(Path(name), "", [p])
        assert "duplicate metadata" in str(err.value)

def test_create_metadata_vs_content(test_dir, testname, monkeypatch):
    """Add additional custom metadata to the archive,
    using a name that conflicts with a content file.
    """
    monkeypatch.chdir(str(test_dir))
    name = archive_name(tags=[testname])
    p = Path("base")
    with TemporaryFile(dir=str(test_dir)) as tmpf:
        archive = Archive()
        tmpf.write("Hello world!\n".encode("ascii"))
        tmpf.seek(0)
        with pytest.raises(ArchiveCreateError) as err:
            archive.add_metadata("msg.txt", tmpf)
            archive.create(Path(name), "", [p])
        assert "filename is reserved" in str(err.value)
