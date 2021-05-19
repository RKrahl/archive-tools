"""Test the excluding items while creating an archive.
"""

from pathlib import Path
import pytest
from archive import Archive
from conftest import *


# Setup a directory with some test data to be put into an archive.
# Make sure that we have all kind of different things in there.
testdata = [
    DataDir(Path("base"), 0o755),
    DataDir(Path("base", "data"), 0o750),
    DataDir(Path("base", "data", "sub"), 0o750),
    DataDir(Path("base", "empty"), 0o755),
    DataFile(Path("base", "msg.txt"), 0o644),
    DataFile(Path("base", "rnd.dat"), 0o600),
    DataRandomFile(Path("base", "data", "rnd1.dat"), 0o600, size=732),
    DataRandomFile(Path("base", "data", "rnd2.dat"), 0o600, size=487),
    DataRandomFile(Path("base", "data", "sub", "rnd3.dat"), 0o600, size=42),
    DataSymLink(Path("base", "s.dat"), Path("data", "rnd1.dat")),
]

@pytest.fixture(scope="module")
def test_dir(tmpdir):
    setup_testdata(tmpdir, testdata)
    return tmpdir


def test_create_exclude_file(test_dir, testname, monkeypatch):
    """Exclude one single file.
    """
    monkeypatch.chdir(test_dir)
    name = archive_name(tags=[testname])
    paths = [Path("base")]
    excludes = [Path("base", "msg.txt")]
    data = sub_testdata(testdata, excludes[0])
    Archive().create(Path(name), "", paths, excludes=excludes)
    with Archive().open(Path(name)) as archive:
        check_manifest(archive.manifest, data)
        archive.verify()


def test_create_exclude_subdir(test_dir, testname, monkeypatch):
    """Exclude a subdirectory.
    """
    monkeypatch.chdir(test_dir)
    name = archive_name(tags=[testname])
    paths = [Path("base")]
    excludes = [Path("base", "data")]
    data = sub_testdata(testdata, excludes[0])
    Archive().create(Path(name), "", paths, excludes=excludes)
    with Archive().open(Path(name)) as archive:
        check_manifest(archive.manifest, data)
        archive.verify()


def test_create_exclude_samelevel(test_dir, testname, monkeypatch):
    """Exclude a directory explictely named in paths.
    """
    monkeypatch.chdir(test_dir)
    name = archive_name(tags=[testname])
    paths = [Path("base", "data"), Path("base", "empty")]
    excludes = [paths[1]]
    data = sub_testdata(testdata, Path("base"), paths[0])
    Archive().create(Path(name), "", paths, excludes=excludes)
    with Archive().open(Path(name)) as archive:
        check_manifest(archive.manifest, data)
        archive.verify()


def test_create_exclude_explicit_include(test_dir, testname, monkeypatch):
    """Exclude a directory, but explicitely include an item in that
    directory.
    """
    monkeypatch.chdir(test_dir)
    name = archive_name(tags=[testname])
    paths = [Path("base"), Path("base", "data", "rnd1.dat")]
    excludes = [Path("base", "data")]
    data = sub_testdata(testdata, excludes[0], paths[1])
    Archive().create(Path(name), "", paths, excludes=excludes)
    with Archive().open(Path(name)) as archive:
        check_manifest(archive.manifest, data)
        archive.verify()
