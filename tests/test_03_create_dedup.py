"""Test deduplication modes while creating an archive.
"""

import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import pytest
from pytest_dependency import depends
from archive.archive import Archive, DedupMode
from archive.manifest import Manifest
from conftest import (checksums, setup_testdata, check_manifest,
                      TestDataDir, TestDataFile, TestDataSymLink)


# Setup a directory with some test data to be put into an archive.
# Make sure that we have all kind of different things in there.
src = Path("base", "data", "rnd.dat")
src_mode = 0o600
dest_lnk = src.with_name("rnd_lnk.dat")
dest_cp = src.with_name("rnd_cp.dat")
testdata = [
    TestDataDir(Path("base"), 0o755),
    TestDataDir(Path("base", "data"), 0o750),
    TestDataDir(Path("base", "empty"), 0o755),
    TestDataFile(Path("base", "msg.txt"), 0o644),
    TestDataFile(src, src_mode),
    TestDataSymLink(Path("base", "s.dat"), Path("data", "rnd.dat")),
]
sha256sum = "sha256sum"

@pytest.fixture(scope="module")
def test_dir(tmpdir):
    setup_testdata(tmpdir, testdata)
    os.link(str(tmpdir / src), str(tmpdir / dest_lnk))
    testdata.append(TestDataFile(dest_lnk, src_mode))
    checksums[dest_lnk.name] = checksums[src.name]
    shutil.copy(str(tmpdir / src), str(tmpdir / dest_cp))
    testdata.append(TestDataFile(dest_cp, src_mode))
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
    depends(request, ["test_create[%s]" % idfn(testcase)])
    return testcase

@pytest.mark.dependency()
def test_create(test_dir, monkeypatch, testcase):
    dedup = testcase
    monkeypatch.chdir(str(test_dir))
    archive_path = Path(archive_name(dedup))
    paths = [Path("base")]
    Archive().create(archive_path, '', paths, dedup=dedup)

@pytest.mark.dependency()
def test_check_manifest(test_dir, dep_testcase):
    dedup = dep_testcase
    archive_path = test_dir / archive_name(dedup)
    with Archive().open(archive_path) as archive:
        check_manifest(archive.manifest, testdata)

@pytest.mark.dependency()
def test_check_content(test_dir, dep_testcase):
    dedup = dep_testcase
    archive_path = test_dir / archive_name(dedup)
    outdir = test_dir / "out"
    shutil.rmtree(str(outdir), ignore_errors=True)
    outdir.mkdir()
    with tarfile.open(str(archive_path), "r") as tarf:
        tarf.extractall(path=str(outdir))
    try:
        sha256 = subprocess.Popen([sha256sum, "--check"], 
                                  cwd=str(outdir), stdin=subprocess.PIPE)
    except FileNotFoundError:
        pytest.skip("%s program not found" % sha256sum)
    for f in testdata:
        if f.type == 'f':
            l = "%s  %s\n" % (checksums[f.path.name], f.path)
            sha256.stdin.write(l.encode('ascii'))
    sha256.stdin.close()
    sha256.wait()
    assert sha256.returncode == 0

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
