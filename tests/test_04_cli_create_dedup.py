"""Test deduplication modes in the command line tool.
"""

import os
from pathlib import Path
import shutil
import pytest
from pytest_dependency import depends
from archive.archive import Archive, DedupMode
from conftest import *


# Setup a directory with some test data to be put into an archive.
# Make sure that we have all kind of different things in there.
src = Path("base", "data", "rnd.dat")
dest_lnk = src.with_name("rnd_lnk.dat")
dest_cp = src.with_name("rnd_cp.dat")
testdata = [
    DataDir(Path("base"), 0o755),
    DataDir(Path("base", "data"), 0o750),
    DataDir(Path("base", "empty"), 0o755),
    DataFile(Path("base", "msg.txt"), 0o644),
    DataFile(src, 0o600),
    DataSymLink(Path("base", "s.dat"), Path("data", "rnd.dat")),
]
sha256sum = "sha256sum"

@pytest.fixture(scope="module")
def test_dir(tmpdir):
    setup_testdata(tmpdir, testdata)
    sf = next(filter(lambda f: f.path == src, testdata))
    os.link(str(tmpdir / src), str(tmpdir / dest_lnk))
    testdata.append(DataFile(dest_lnk, sf.mode, checksum=sf.checksum))
    shutil.copy(str(tmpdir / src), str(tmpdir / dest_cp))
    testdata.append(DataFile(dest_cp, sf.mode, checksum=sf.checksum))
    return tmpdir

dedupmodes = list(DedupMode)

def idfn(dedup):
    return dedup.value

@pytest.fixture(scope="module", params=dedupmodes, ids=idfn)
def testcase(request):
    param = request.param
    return param

@pytest.fixture(scope="module")
def dep_testcase(request, testcase):
    depends(request, ["test_cli_create[%s]" % idfn(testcase)])
    return testcase

@pytest.mark.dependency()
def test_cli_create(test_dir, monkeypatch, testcase):
    dedup = testcase
    monkeypatch.chdir(str(test_dir))
    archive_path = archive_name(tags=[dedup.value])
    basedir = "base"
    args = ["create", "--deduplicate", dedup.value, archive_path, basedir]
    callscript("archive-tool.py", args)
    with Archive().open(Path(archive_path)) as archive:
        assert str(archive.basedir) == basedir
        check_manifest(archive.manifest, testdata)

@pytest.mark.dependency()
def test_verify(test_dir, dep_testcase):
    dedup = dep_testcase
    archive_path = test_dir / archive_name(tags=[dedup.value])
    with Archive().open(archive_path) as archive:
        ti_lnk = archive._file.getmember(str(dest_lnk))
        ti_cp = archive._file.getmember(str(dest_cp))
        if dedup == DedupMode.NEVER:
            assert ti_lnk.isfile()
            assert ti_cp.isfile()
        elif dedup == DedupMode.LINK:
            assert ti_lnk.islnk()
            assert ti_lnk.linkname == str(src)
            assert ti_cp.isfile()
        elif dedup == DedupMode.CONTENT:
            assert ti_lnk.islnk()
            assert ti_lnk.linkname == str(src)
            assert ti_cp.islnk()
            assert ti_cp.linkname == str(src)
        else:
            assert False, "invalid dedup mode"
