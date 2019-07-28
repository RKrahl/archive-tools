"""Test deduplication modes in the command line tool.
"""

import os
from pathlib import Path
import shutil
import pytest
from pytest_dependency import depends
from archive.archive import Archive, DedupMode
from conftest import checksums, setup_testdata, check_manifest, callscript


# Setup a directory with some test data to be put into an archive.
# Make sure that we have all kind of different things in there.
src = Path("base", "data", "rnd.dat")
src_mode = 0o600
dest_lnk = src.with_name("rnd_lnk.dat")
dest_cp = src.with_name("rnd_cp.dat")
testdata = {
    "dirs": [
        (Path("base"), 0o755),
        (Path("base", "data"), 0o750),
        (Path("base", "empty"), 0o755),
    ],
    "files": [
        (Path("base", "msg.txt"), 0o644),
        (src, src_mode),
    ],
    "symlinks": [
        (Path("base", "s.dat"), Path("data", "rnd.dat")),
    ]
}
sha256sum = "sha256sum"

@pytest.fixture(scope="module")
def test_dir(tmpdir):
    setup_testdata(tmpdir, **testdata)
    os.link(str(tmpdir / src), str(tmpdir / dest_lnk))
    testdata["files"].append((dest_lnk, src_mode))
    checksums[dest_lnk.name] = checksums[src.name]
    shutil.copy(str(tmpdir / src), str(tmpdir / dest_cp))
    testdata["files"].append((dest_cp, src_mode))
    checksums[dest_cp.name] = checksums[src.name]
    return tmpdir

dedupmodes = list(DedupMode)

def idfn(dedup):
    return dedup.value

def archive_name(dedup):
    return "archive-%s.tar" % dedup.value

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
    archive_path = archive_name(dedup)
    basedir = "base"
    args = ["create", "--deduplicate", dedup.value, archive_path, basedir]
    callscript("archive-tool.py", args)
    with Archive().open(Path(archive_path)) as archive:
        assert str(archive.basedir) == basedir
        check_manifest(archive.manifest, **testdata)

@pytest.mark.dependency()
def test_verify(test_dir, dep_testcase):
    dedup = dep_testcase
    archive_path = test_dir / archive_name(dedup)
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
