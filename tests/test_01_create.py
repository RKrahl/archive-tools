"""Test creating an archive and check its content.
"""

from pathlib import Path
import shutil
import subprocess
import tarfile
import pytest
from pytest_dependency import depends
from archive import Archive
from conftest import gettestdata, testdata_checksums, tmpdir


# Setup a directory with some test data to be put into an archive.
# Make sure that we have all kind if different things in there.
testdirs = [
    (Path("base"), 0o755),
    (Path("base", "data"), 0o750),
    (Path("base", "empty"), 0o755),
]
testfiles = [
    (Path("base", "msg.txt"), 0o644),
    (Path("base", "data", "rnd.dat"), 0o600),
]
testsymlinks = [
    (Path("base", "s.dat"), Path("data", "rnd.dat")),
]
sha256sum = "sha256sum"

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

# Consider compression modes supported by tarfile and relative as well
# as absolute paths in the archive.
compressions = ['', 'gz', 'bz2', 'xz']
abspaths = [ True, False ]
testcases = [ (c,a) for c in compressions for a in abspaths ]

def idfn(case):
    c, a = case
    return "%s-%s" % (c if c else "none", "abs" if a else "rel")

def archive_name(compression, abspath):
    name = "archive-%s.tar" % ("abs" if abspath else "rel")
    if compression:
        name += ".%s" % compression
    return name

@pytest.fixture(scope="module", params=testcases, ids=idfn)
def testcase(request):
    param = request.param
    return param

@pytest.fixture(scope="module")
def dep_testcase(request, testcase):
    depends(request, ["test_create[%s]" % idfn(testcase)])
    return testcase

@pytest.mark.dependency()
def test_create(testdata, monkeypatch, testcase):
    compression, abspath = testcase
    monkeypatch.chdir(str(testdata))
    mode = "x:%s" % compression
    archive_path = archive_name(compression, abspath)
    if abspath:
        paths = [testdata / "base"]
        basedir = "archive"
    else:
        paths = ["base"]
        basedir = "base"
    Archive(archive_path, mode=mode, paths=paths, basedir=basedir)

@pytest.mark.dependency()
def test_check_manifest(testdata, dep_testcase):
    compression, abspath = dep_testcase
    archive_path = testdata / archive_name(compression, abspath)
    archive = Archive(archive_path, mode="r")
    num_testitems = len(testdirs) + len(testfiles) + len(testsymlinks)
    assert len(archive.manifest) == num_testitems
    for d, m in testdirs:
        if abspath:
            d = testdata / d
        fi = archive.manifest.find(d)
        assert fi
        assert fi.type == 'd'
        assert fi.path == d
        assert fi.mode == m
    for f, m in testfiles:
        if abspath:
            f = testdata / f
        fi = archive.manifest.find(f)
        assert fi
        assert fi.type == 'f'
        assert fi.path == f
        assert fi.mode == m
        assert fi.checksum['sha256'] == testdata_checksums[f.name]
    for f, t in testsymlinks:
        if abspath:
            f = testdata / f
        fi = archive.manifest.find(f)
        assert fi
        assert fi.type == 'l'
        assert fi.path == f
        assert fi.target == t

@pytest.mark.dependency()
def test_check_content(testdata, dep_testcase):
    compression, abspath = dep_testcase
    archive_path = testdata / archive_name(compression, abspath)
    outdir = testdata / "out"
    shutil.rmtree(str(outdir), ignore_errors=True)
    outdir.mkdir()
    if abspath:
        cwd = outdir / "archive" / testdata.relative_to(testdata.anchor)
    else:
        cwd = outdir
    with tarfile.open(str(archive_path), "r") as tarf:
        tarf.extractall(path=str(outdir))
    try:
        sha256 = subprocess.Popen([sha256sum, "--check"], 
                                  cwd=str(cwd), stdin=subprocess.PIPE)
    except FileNotFoundError:
        pytest.skip("%s program not found" % sha256sum)
    for f, _ in testfiles:
        l = "%s  %s\n" % (testdata_checksums[f.name], f)
        sha256.stdin.write(l.encode('ascii'))
    sha256.stdin.close()
    sha256.wait()
    assert sha256.returncode == 0

