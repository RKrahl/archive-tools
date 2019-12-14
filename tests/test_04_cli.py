"""Test the command line tool to create an archive and check its content.
"""

from pathlib import Path
import stat
import subprocess
from tempfile import TemporaryFile
import pytest
from pytest_dependency import depends
from archive import Archive
from conftest import (require_compression, setup_testdata, check_manifest,
                      callscript, TestDataDir, TestDataFile, TestDataSymLink)


# Setup a directory with some test data to be put into an archive.
# Make sure that we have all kind of different things in there.
testdata = [
    TestDataDir(Path("base"), 0o755),
    TestDataDir(Path("base", "data"), 0o750),
    TestDataDir(Path("base", "empty"), 0o755),
    TestDataFile(Path("base", "msg.txt"), 0o644),
    TestDataFile(Path("base", "data", "rnd.dat"), 0o600),
    TestDataSymLink(Path("base", "s.dat"), Path("data", "rnd.dat")),
]
sha256sum = "sha256sum"

@pytest.fixture(scope="module")
def test_dir(tmpdir):
    setup_testdata(tmpdir, testdata)
    return tmpdir

# Consider compression modes supported by tarfile and relative as well
# as absolute paths in the archive.
compressions = ["none", "gz", "bz2", "xz"]
abspaths = [ True, False ]
testcases = [ (c,a) for c in compressions for a in abspaths ]

def idfn(case):
    c, a = case
    return "%s-%s" % (c, "abs" if a else "rel")

def archive_name(compression, abspath):
    name = "archive-%s.tar" % ("abs" if abspath else "rel")
    if compression != "none":
        name += ".%s" % compression
    return name

@pytest.fixture(scope="module", params=testcases, ids=idfn)
def testcase(request):
    param = request.param
    return param

@pytest.fixture(scope="module")
def dep_testcase(request, testcase):
    depends(request, ["test_cli_create[%s]" % idfn(testcase)])
    return testcase

@pytest.mark.dependency()
def test_cli_create(test_dir, monkeypatch, testcase):
    compression, abspath = testcase
    require_compression(compression)
    monkeypatch.chdir(str(test_dir))
    archive_path = archive_name(compression, abspath)
    if abspath:
        paths = str(test_dir / "base")
        basedir = "archive"
    else:
        paths = "base"
        basedir = "base"
    args = ["create", "--compression", compression, "--basedir", basedir,
            archive_path, paths]
    callscript("archive-tool.py", args)
    with Archive().open(archive_path) as archive:
        assert str(archive.basedir) == basedir
        prefix_dir = test_dir if abspath else Path(".")
        check_manifest(archive.manifest, testdata, prefix_dir=prefix_dir)

@pytest.mark.dependency()
def test_cli_verify(test_dir, dep_testcase):
    compression, abspath = dep_testcase
    archive_path = test_dir / archive_name(compression, abspath)
    args = ["verify", str(archive_path)]
    callscript("archive-tool.py", args)

@pytest.mark.dependency()
def test_cli_ls(test_dir, dep_testcase):
    compression, abspath = dep_testcase
    archive_path = test_dir / archive_name(compression, abspath)
    prefix_dir = test_dir if abspath else Path(".")
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["ls", str(archive_path)]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        for entry in sorted(testdata, key=lambda e: e.path):
            line = f.readline()
            fields = line.split()
            assert fields[0] == stat.filemode(entry.st_mode)
            assert fields[5] == str(prefix_dir / entry.path)
            if entry.type == "l":
                assert len(fields) == 8
                assert fields[7] == str(entry.target)
            else:
                assert len(fields) == 6
        assert not f.readline()

@pytest.mark.dependency()
def test_cli_checksums(test_dir, dep_testcase):
    compression, abspath = dep_testcase
    archive_path = test_dir / archive_name(compression, abspath)
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["ls", "--format=checksum", str(archive_path)]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        cwd = None if abspath else str(test_dir)
        try:
            sha256 = subprocess.Popen([sha256sum, "--check"],
                                      cwd=cwd, stdin=subprocess.PIPE)
        except FileNotFoundError:
            pytest.skip("%s program not found" % sha256sum)
        for line in f:
            sha256.stdin.write(line.encode('ascii'))
        sha256.stdin.close()
        sha256.wait()
        assert sha256.returncode == 0

@pytest.mark.dependency()
def test_cli_info(test_dir, dep_testcase):
    compression, abspath = dep_testcase
    archive_path = test_dir / archive_name(compression, abspath)
    prefix_dir = test_dir if abspath else Path(".")
    # Need to test each type only once.
    types_done = set()
    for entry in testdata:
        if entry.type in types_done:
            continue
        with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
            args = ["info", str(archive_path), str(prefix_dir / entry.path)]
            callscript("archive-tool.py", args, stdout=f)
            f.seek(0)
            info = {}
            for line in f:
                k, v = line.split(':', maxsplit=1)
                info[k] = v.strip()
            assert info["Path"] == str(prefix_dir / entry.path)
            assert info["Mode"] == stat.filemode(entry.st_mode)
            if entry.type == "d":
                assert info["Type"] == "directory"
            elif entry.type == "f":
                assert info["Type"] == "file"
            if entry.type == "l":
                assert info["Type"] == "symbolic link"
                assert info["Target"] == str(entry.target)
        types_done.add(entry.type)
