"""Tests passing the workdir keyword argument to Archive.create().
"""

from pathlib import Path
import pytest
from archive import Archive
from conftest import *


testdata = [
    DataDir(Path("base"), 0o755),
    DataDir(Path("base", "data"), 0o755),
    DataFile(Path("base", "data", "rnd.dat"), 0o644),
]

@pytest.fixture(scope="module")
def test_dir(tmpdir):
    setup_testdata(tmpdir / "work", testdata)
    return tmpdir


@pytest.mark.parametrize("abs_wd", [ True, False ], ids=absflag)
def test_create_workdir(test_dir, monkeypatch, abs_wd):
    """Pass an absolute or relative workdir to Archive.create().
    (Issue #53)
    """
    monkeypatch.chdir(test_dir)
    if abs_wd:
        workdir = test_dir / "work"
    else:
        workdir = Path("work")
    archive_path = Path(archive_name(tags=[absflag(abs_wd)]))
    Archive().create(archive_path, "", [Path("base")], workdir=workdir)
    with Archive().open(workdir / archive_path) as archive:
        assert archive.basedir == Path("base")
        check_manifest(archive.manifest, testdata)
        archive.verify()
