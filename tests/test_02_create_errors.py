"""Test error conditions during creating an archive.
"""

from pathlib import Path
import shutil
import pytest
from archive import Archive
from conftest import gettestdata, tmpdir


# Setup a directory with some test data to be put into an archive.
# Make sure that we have all kind if different things in there.
testdirs = [
    (Path("base"), 0o755),
    (Path("base", "empty"), 0o755),
    (Path("base", "data"), 0o755),
    (Path("other"), 0o755),
]
testfiles = [
    (Path("base", "msg.txt"), 0o644),
    (Path("other", "rnd.dat"), 0o600),
    (Path("msg.txt"), 0o644),
]
testsymlinks = []

@pytest.fixture(scope="module")
def testdata(tmpdir):
    for d, m in testdirs:
        p = tmpdir / d
        p.mkdir()
        p.chmod(m)
    for f, m in testfiles:
        p = tmpdir / f
        shutil.copy(str(gettestdata(f.name)), str(p))
        p.chmod(m)
    for f, t in testsymlinks:
        p = tmpdir / f
        p.symlink_to(t)
    return tmpdir

def test_create_mixing_abs_rel(testdata, monkeypatch):
    """Mixing absolute and relative paths is not allowed.
    """
    monkeypatch.chdir(str(testdata))
    paths = [ Path("base", "msg.txt"), testdata / "base" / "data" ]
    with pytest.raises(ValueError):
        Archive("archive.tar", mode="x:", paths=paths, basedir="base")

def test_create_rel_not_in_base(testdata, monkeypatch):
    """Relative paths must be in the base directory.
    """
    monkeypatch.chdir(str(testdata))
    paths = [ Path("other", "rnd.dat") ]
    with pytest.raises(ValueError):
        Archive("archive.tar", mode="x:", paths=paths, basedir="base")

def test_create_norm_path(testdata, monkeypatch):
    """Items in paths must be normalized.
    """
    monkeypatch.chdir(str(testdata))
    paths = [ "base", "base/../../../etc/passwd" ]
    with pytest.raises(ValueError):
        Archive("archive.tar", mode="x:", paths=paths, basedir="base")

@pytest.mark.xfail(reason="Issue #9")
def test_create_rel_check_basedir(testdata, monkeypatch):
    """Base directory must be a directory.
    """
    monkeypatch.chdir(str(testdata))
    p = Path("msg.txt")
    with pytest.raises(ValueError):
        Archive("archive.tar", mode="x:", paths=[p], basedir=p)
