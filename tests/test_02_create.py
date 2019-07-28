"""Test creating an archive and check its content.
"""

import datetime
from pathlib import Path
import shutil
import subprocess
import tarfile
import pytest
from pytest_dependency import depends
from archive import Archive
from archive.manifest import FileInfo, Manifest
from conftest import (checksums, require_compression,
                      setup_testdata, check_manifest)


# Setup a directory with some test data to be put into an archive.
# Make sure that we have all kind of different things in there.
testdata = {
    "dirs": [
        (Path("base"), 0o755),
        (Path("base", "data"), 0o750),
        (Path("base", "empty"), 0o755),
    ],
    "files": [
        (Path("base", "msg.txt"), 0o644),
        (Path("base", "data", "rnd.dat"), 0o600),
    ],
    "symlinks": [
        (Path("base", "s.dat"), Path("data", "rnd.dat")),
    ]
}
sha256sum = "sha256sum"

@pytest.fixture(scope="module")
def test_dir(tmpdir):
    setup_testdata(tmpdir, **testdata)
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
def test_create(test_dir, monkeypatch, testcase):
    compression, abspath = testcase
    require_compression(compression)
    monkeypatch.chdir(str(test_dir))
    archive_path = Path(archive_name(compression, abspath))
    if abspath:
        paths = [test_dir / "base"]
        basedir = Path("archive")
    else:
        paths = [Path("base")]
        basedir = Path("base")
    Archive().create(archive_path, compression, paths, basedir=basedir)

@pytest.mark.dependency()
def test_check_manifest(test_dir, dep_testcase):
    compression, abspath = dep_testcase
    archive_path = test_dir / archive_name(compression, abspath)
    with Archive().open(archive_path) as archive:
        head = archive.manifest.head
        assert set(head.keys()) == {
            "Checksums", "Date", "Generator", "Metadata", "Version"
        }
        assert archive.manifest.version == Manifest.Version
        assert isinstance(archive.manifest.date, datetime.datetime)
        assert archive.manifest.checksums == tuple(FileInfo.Checksums)
        manifest_path = archive.basedir / ".manifest.yaml"
        assert archive.manifest.metadata == (str(manifest_path),)
        prefix_dir = test_dir if abspath else None
        check_manifest(archive.manifest, prefix_dir=prefix_dir, **testdata)

@pytest.mark.dependency()
def test_check_content(test_dir, dep_testcase):
    compression, abspath = dep_testcase
    archive_path = test_dir / archive_name(compression, abspath)
    outdir = test_dir / "out"
    shutil.rmtree(str(outdir), ignore_errors=True)
    outdir.mkdir()
    if abspath:
        cwd = outdir / "archive" / test_dir.relative_to(test_dir.anchor)
    else:
        cwd = outdir
    with tarfile.open(str(archive_path), "r") as tarf:
        tarf.extractall(path=str(outdir))
    try:
        sha256 = subprocess.Popen([sha256sum, "--check"], 
                                  cwd=str(cwd), stdin=subprocess.PIPE)
    except FileNotFoundError:
        pytest.skip("%s program not found" % sha256sum)
    for f, _ in testdata["files"]:
        l = "%s  %s\n" % (checksums[f.name], f)
        sha256.stdin.write(l.encode('ascii'))
    sha256.stdin.close()
    sha256.wait()
    assert sha256.returncode == 0

@pytest.mark.dependency()
def test_verify(test_dir, dep_testcase):
    compression, abspath = dep_testcase
    archive_path = test_dir / archive_name(compression, abspath)
    with Archive().open(archive_path) as archive:
        archive.verify()
