"""Test the '--exclude' command line argument to 'archive-tool create'.
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


def test_cli_create_exclude_dir(test_dir, testname, monkeypatch):
    """Exclude a single directory.
    """
    monkeypatch.chdir(test_dir)
    name = archive_name(tags=[testname])
    paths = "base"
    exclude = Path("base", "data")
    data = sub_testdata(testdata, exclude)
    args = ["create", "--exclude", str(exclude), name, paths]
    callscript("archive-tool.py", args)
    with Archive().open(Path(name)) as archive:
        check_manifest(archive.manifest, data)


def test_cli_create_exclude_mult(test_dir, testname, monkeypatch):
    """Exclude multiple items.
    """
    monkeypatch.chdir(test_dir)
    name = archive_name(tags=[testname])
    paths = "base"
    excludes = [
        Path("base", "data", "sub"),
        Path("base", "rnd.dat"),
        Path("base", "s.dat"),
    ]
    data = testdata
    excl_args = []
    for excl in excludes:
        data = sub_testdata(data, excl)
        excl_args += ("--exclude", str(excl))
    args = ["create"] + excl_args + [name, paths]
    callscript("archive-tool.py", args)
    with Archive().open(Path(name)) as archive:
        check_manifest(archive.manifest, data)


def test_cli_create_exclude_include(test_dir, testname, monkeypatch):
    """Exclude a directory, but explicitely include an item in that
    directory.
    """
    monkeypatch.chdir(test_dir)
    name = archive_name(tags=[testname])
    exclude = Path("base", "data")
    include = Path("base", "data", "rnd1.dat")
    paths = ["base", str(include)]
    data = sub_testdata(testdata, exclude, include)
    args = ["create", "--exclude", str(exclude), name] + paths
    callscript("archive-tool.py", args)
    with Archive().open(Path(name)) as archive:
        check_manifest(archive.manifest, data)
