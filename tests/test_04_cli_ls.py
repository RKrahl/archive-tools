"""Test the ls subcommand in the command line tool.

The general functioning is already tested in test_04_cli.py, we only
consider edge cases here.
"""

from pathlib import Path
import stat
from tempfile import TemporaryFile
import pytest
from archive import Archive
from conftest import *


@pytest.mark.xfail(reason="Issue #81")
def test_cli_ls_blank_path(tmpdir):
    """Test case: archive contains a file having blanks in the path.
    Ref. Issue #81.
    """
    testdata = [
        DataDir(Path("base"), 0o755),
        DataFile(Path("base", "msg.txt"), 0o644),
        DataContentFile(Path("base", "path  with  blanks.dat"), b"", 0o600),
    ]
    setup_testdata(tmpdir, testdata)
    archive_path = tmpdir / "archive.tar"
    Archive().create(archive_path, paths=[Path("base")], workdir=tmpdir)
    with TemporaryFile(mode="w+t", dir=tmpdir) as f:
        args = ["ls", str(archive_path)]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        for entry in sorted(testdata, key=lambda e: e.path):
            line = f.readline().strip()
            fields = line.split(maxsplit=5)
            assert fields[0] == stat.filemode(entry.st_mode)
            assert fields[5] == str(entry.path)
            assert len(fields) == 6
        assert not f.readline()
