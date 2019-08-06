"""Test the '--exclude' command line argument to 'archive-tool create'.
"""

from pathlib import Path
import pytest
from archive import Archive
from conftest import setup_testdata, sub_testdata, check_manifest, callscript


# Setup a directory with some test data to be put into an archive.
# Make sure that we have all kind of different things in there.
testdata = {
    "dirs": [
        (Path("base"), 0o755),
        (Path("base", "data"), 0o750),
        (Path("base", "data", "sub"), 0o750),
        (Path("base", "empty"), 0o755),
    ],
    "files": [
        (Path("base", "msg.txt"), 0o644),
        (Path("base", "rnd.dat"), 0o600),
        (Path("base", "data", "rnd1.dat"), 0o600),
        (Path("base", "data", "rnd2.dat"), 0o600),
        (Path("base", "data", "sub", "rnd3.dat"), 0o600),
    ],
    "symlinks": [
        (Path("base", "s.dat"), Path("data", "rnd1.dat")),
    ]
}

@pytest.fixture(scope="module")
def test_dir(tmpdir):
    setup_testdata(tmpdir, **testdata)
    return tmpdir


def test_cli_create_exclude_dir(test_dir, archive_name, monkeypatch):
    """Exclude a single directory.
    """
    monkeypatch.chdir(str(test_dir))
    paths = "base"
    exclude = Path("base", "data")
    data = sub_testdata(testdata, exclude)
    args = ["create", "--exclude", str(exclude), archive_name, paths]
    callscript("archive-tool.py", args)
    with Archive().open(Path(archive_name)) as archive:
        check_manifest(archive.manifest, **data)


def test_cli_create_exclude_mult(test_dir, archive_name, monkeypatch):
    """Exclude multiple items.
    """
    monkeypatch.chdir(str(test_dir))
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
    args = ["create"] + excl_args + [archive_name, paths]
    callscript("archive-tool.py", args)
    with Archive().open(Path(archive_name)) as archive:
        check_manifest(archive.manifest, **data)


def test_cli_create_exclude_include(test_dir, archive_name, monkeypatch):
    """Exclude a directory, but explicitely include an item in that
    directory.
    """
    monkeypatch.chdir(str(test_dir))
    exclude = Path("base", "data")
    include = Path("base", "data", "rnd1.dat")
    paths = ["base", str(include)]
    data = sub_testdata(testdata, exclude, include)
    args = ["create", "--exclude", str(exclude), archive_name] + paths
    callscript("archive-tool.py", args)
    with Archive().open(Path(archive_name)) as archive:
        check_manifest(archive.manifest, **data)
