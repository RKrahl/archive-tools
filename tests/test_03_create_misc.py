"""Misc issues around creating an archive.
"""

from pathlib import Path
from tempfile import TemporaryFile
import pytest
from archive import Archive
from conftest import *


# Setup a directory with some test data to be put into an archive.
# Make sure that we have all kind of different things in there.
testdata = [
    DataDir(Path("base", "data"), 0o755),
    DataDir(Path("base", "data", "misc"), 0o755),
    DataDir(Path("base", "data", "other"), 0o755),
    DataFile(Path("base", "data", "misc", "rnd.dat"), 0o644),
    DataSymLink(Path("base", "data", "s.dat"), Path("misc", "rnd.dat")),
]

@pytest.fixture(scope="module")
def test_dir(tmpdir):
    setup_testdata(tmpdir, testdata)
    return tmpdir


def test_create_default_basedir_rel(test_dir, monkeypatch):
    """Check the default basedir with relative paths.  (Issue #8)
    """
    monkeypatch.chdir(str(test_dir))
    archive_path = "archive-rel.tar"
    p = Path("base", "data")
    Archive().create(archive_path, "", [p])
    with Archive().open(archive_path) as archive:
        assert archive.basedir == Path("base")
        check_manifest(archive.manifest, testdata)
        archive.verify()

def test_create_default_basedir_abs(test_dir, monkeypatch):
    """Check the default basedir with absolute paths.  (Issue #8)
    """
    monkeypatch.chdir(str(test_dir))
    archive_path = Path("archive-abs.tar")
    p = test_dir / Path("base", "data")
    Archive().create(archive_path, "", [p])
    with Archive().open(archive_path) as archive:
        assert archive.basedir == Path("archive-abs")
        check_manifest(archive.manifest, testdata, prefix_dir=test_dir)
        archive.verify()

def test_create_sorted(test_dir, monkeypatch):
    """The entries in the manifest should be sorted.  (Issue #11)
    """
    monkeypatch.chdir(str(test_dir))
    archive_path = Path("archive-sort.tar")
    files = [ Path("base", fn) for fn in ("c", "a", "d", "b") ]
    for p in files:
        with p.open("wt") as f:
            print("Some content for file %s" % p, file=f)
    try:
        Archive().create(archive_path, "", files)
        with Archive().open(archive_path) as archive:
            assert [fi.path for fi in archive.manifest] == sorted(files)
            archive.verify()
    finally:
        for p in files:
            p.unlink()

def test_create_custom_metadata(test_dir, monkeypatch):
    """Add additional custom metadata to the archive.
    """
    monkeypatch.chdir(str(test_dir))
    archive_path = Path("archive-custom-md.tar")
    p = Path("base", "data")
    with TemporaryFile(dir=str(test_dir)) as tmpf:
        archive = Archive()
        tmpf.write("Hello world!\n".encode("ascii"))
        tmpf.seek(0)
        archive.add_metadata(".msg.txt", tmpf)
        archive.create(archive_path, "", [p])
    with Archive().open(archive_path) as archive:
        metadata = ( "base/.manifest.yaml", "base/.msg.txt" )
        assert archive.manifest.metadata == metadata
        md = archive.get_metadata(".msg.txt")
        assert md.path == archive.basedir / ".msg.txt"
        assert md.fileobj.read() == "Hello world!\n".encode("ascii")
        check_manifest(archive.manifest, testdata)
        archive.verify()

def test_create_add_symlink(test_dir, monkeypatch):
    """Check adding explicitly adding a symbolic link.  (Issue #37)
    """
    monkeypatch.chdir(str(test_dir))
    archive_path = "archive-symlink.tar"
    paths = [Path("base", "data", "misc"), Path("base", "data", "s.dat")]
    data = [ testdata[i] for i in (1,3,4) ]
    Archive().create(archive_path, "", paths)
    with Archive().open(archive_path) as archive:
        check_manifest(archive.manifest, data)
        archive.verify()

@pytest.mark.parametrize(("tags", "expected"), [
    (None, ()),
    ([], ()),
    (["a"], ("a",)),
    (["a", "b"], ("a", "b")),
])
def test_create_tags(test_dir, monkeypatch, tags, expected):
    """Test setting tags.
    """
    monkeypatch.chdir(str(test_dir))
    archive_path = archive_name(tags=["tags"], counter="create_tags")
    Archive().create(archive_path, "", [Path("base")], tags=tags)
    with Archive().open(archive_path) as archive:
        assert archive.manifest.tags == expected
