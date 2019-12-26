"""Misc issues around using the command line tool to create an archive.
"""

from pathlib import Path
import pytest
from archive import Archive
from conftest import *


# Setup a directory with some test data to be put into an archive.
# Make sure that we have all kind of different things in there.
testdata = [
    DataDir(Path("base"), 0o755, mtime=1565100853),
    DataDir(Path("base", "data"), 0o750, mtime=1555271302),
    DataDir(Path("base", "empty"), 0o755, mtime=1547911753),
    DataFile(Path("base", "msg.txt"), 0o644, mtime=1547911753),
    DataFile(Path("base", "data", "rnd.dat"), 0o600, mtime=1563112510),
    DataSymLink(Path("base", "s.dat"), Path("data", "rnd.dat"),
                mtime=1565100853),
]

@pytest.fixture(scope="module")
def test_dir(tmpdir):
    setup_testdata(tmpdir, testdata)
    return tmpdir

@pytest.mark.parametrize(("tags", "expected"), [
    ([], ()),
    (["a"], ("a",)),
    (["a", "b"], ("a", "b")),
])
def test_cli_create_tags(test_dir, monkeypatch, tags, expected):
    """Set tags using the --tags argument.
    """
    monkeypatch.chdir(str(test_dir))
    archive_path = archive_name(tags=["tags"], counter="cli_create_tags")
    args = ["create"]
    for t in tags:
        args += ("--tag", t)
    args += (archive_path, "base")
    callscript("archive-tool.py", args)
    with Archive().open(archive_path) as archive:
        assert archive.manifest.tags == expected
        check_manifest(archive.manifest, testdata)
