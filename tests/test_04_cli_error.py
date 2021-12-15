"""Test the error handling in the command line tool.
"""

import os
from pathlib import Path
import stat
import tarfile
from tempfile import TemporaryFile
from archive.manifest import Manifest
import pytest
from conftest import *

# Setup a directory with some test data to be put into an archive.
# Make sure that we have all kind of different things in there.
testdata = [
    DataDir(Path("base"), 0o755),
    DataDir(Path("base", "data"), 0o750),
    DataDir(Path("base", "empty"), 0o755),
    DataFile(Path("base", "msg.txt"), 0o644),
    DataFile(Path("base", "data", "rnd.dat"), 0o600),
    DataSymLink(Path("base", "s.dat"), Path("data", "rnd.dat")),
]

@pytest.fixture(scope="module")
def test_dir(tmpdir):
    setup_testdata(tmpdir, testdata)
    return tmpdir

def test_cli_helpmessage(test_dir, monkeypatch):
    monkeypatch.chdir(test_dir)
    with TemporaryFile(mode="w+t", dir=test_dir) as f:
        args = ["-h"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        line = f.readline()
        assert line.startswith("usage: archive-tool.py ")

def test_cli_missing_command(test_dir, monkeypatch):
    monkeypatch.chdir(test_dir)
    with TemporaryFile(mode="w+t", dir=test_dir) as f:
        args = []
        callscript("archive-tool.py", args, returncode=2, stderr=f)
        f.seek(0)
        line = f.readline()
        assert line.startswith("usage: archive-tool.py ")
        while True:
            line = f.readline()
            if not line.startswith(" "):
                break
        assert "subcommand is required" in line

def test_cli_bogus_command(test_dir, monkeypatch):
    monkeypatch.chdir(test_dir)
    with TemporaryFile(mode="w+t", dir=test_dir) as f:
        args = ["bogus_cmd"]
        callscript("archive-tool.py", args, returncode=2, stderr=f)
        f.seek(0)
        line = f.readline()
        assert line.startswith("usage: archive-tool.py ")
        while True:
            line = f.readline()
            if not line.startswith(" "):
                break
        assert "invalid choice: 'bogus_cmd'" in line

def test_cli_create_bogus_compression(test_dir, testname, monkeypatch):
    monkeypatch.chdir(test_dir)
    name = archive_name(tags=[testname])
    with TemporaryFile(mode="w+t", dir=test_dir) as f:
        args = ["create", "--compression=bogus_comp", name, "base"]
        callscript("archive-tool.py", args, returncode=2, stderr=f)
        f.seek(0)
        line = f.readline()
        assert line.startswith("usage: archive-tool.py ")
        while True:
            line = f.readline()
            if not line.startswith(" "):
                break
        assert "--compression: invalid choice: 'bogus_comp'" in line

def test_cli_ls_bogus_format(test_dir, testname, monkeypatch):
    monkeypatch.chdir(test_dir)
    name = archive_name(tags=[testname])
    args = ["create", name, "base"]
    callscript("archive-tool.py", args)
    with TemporaryFile(mode="w+t", dir=test_dir) as f:
        args = ["ls", "--format=bogus_fmt", name]
        callscript("archive-tool.py", args, returncode=2, stderr=f)
        f.seek(0)
        line = f.readline()
        assert line.startswith("usage: archive-tool.py ")
        while True:
            line = f.readline()
            if not line.startswith(" "):
                break
        assert "--format: invalid choice: 'bogus_fmt'" in line

def test_cli_create_normalized_path(test_dir, testname, monkeypatch):
    monkeypatch.chdir(test_dir)
    name = archive_name(tags=[testname])
    with TemporaryFile(mode="w+t", dir=test_dir) as f:
        args = ["create", name, "base/empty/.."]
        callscript("archive-tool.py", args, returncode=1, stderr=f)
        f.seek(0)
        line = f.readline()
        assert "invalid path 'base/empty/..': must be normalized" in line

def test_cli_create_rel_start_basedir(test_dir, testname, monkeypatch):
    monkeypatch.chdir(test_dir)
    name = archive_name(tags=[testname])
    with TemporaryFile(mode="w+t", dir=test_dir) as f:
        args = ["create", "--basedir=base/data", name, "base/msg.txt"]
        callscript("archive-tool.py", args, returncode=1, stderr=f)
        f.seek(0)
        line = f.readline()
        assert ("invalid path 'base/msg.txt': must be a subpath of "
                "base directory base/data") in line

def test_cli_ls_archive_not_found(test_dir, monkeypatch):
    monkeypatch.chdir(test_dir)
    with TemporaryFile(mode="w+t", dir=test_dir) as f:
        args = ["ls", "bogus.tar"]
        callscript("archive-tool.py", args, returncode=1, stderr=f)
        f.seek(0)
        line = f.readline()
        assert "No such file or directory: 'bogus.tar'" in line

def test_cli_ls_checksum_invalid_hash(test_dir, testname, monkeypatch):
    monkeypatch.chdir(test_dir)
    name = archive_name(tags=[testname])
    args = ["create", name, "base"]
    callscript("archive-tool.py", args)
    with TemporaryFile(mode="w+t", dir=test_dir) as f:
        args = ["ls", "--format=checksum", "--checksum=bogus", name]
        callscript("archive-tool.py", args, returncode=1, stderr=f)
        f.seek(0)
        line = f.readline()
        assert "'bogus' hashes not available" in line

def test_cli_info_missing_entry(test_dir, testname, monkeypatch):
    monkeypatch.chdir(test_dir)
    name = archive_name(tags=[testname])
    args = ["create", name, "base"]
    callscript("archive-tool.py", args)
    with TemporaryFile(mode="w+t", dir=test_dir) as f:
        args = ["info", name, "base/data/not-present"]
        callscript("archive-tool.py", args, returncode=1, stderr=f)
        f.seek(0)
        line = f.readline()
        assert "base/data/not-present: not found in archive" in line

def test_cli_integrity_no_manifest(test_dir, testname, monkeypatch):
    monkeypatch.chdir(test_dir)
    name = archive_name(tags=[testname])
    with tarfile.open(name, "w") as tarf:
        tarf.add("base", recursive=True)
    with TemporaryFile(mode="w+t", dir=test_dir) as f:
        args = ["ls", name]
        callscript("archive-tool.py", args, returncode=3, stderr=f)
        f.seek(0)
        line = f.readline()
        assert "metadata item '.manifest.yaml' not found" in line

def test_cli_integrity_missing_file(test_dir, testname, monkeypatch):
    monkeypatch.chdir(test_dir)
    name = archive_name(tags=[testname])
    base = Path("base")
    missing = base / "data" / "not-present"
    with missing.open("wt") as f:
        f.write("Hello!")
    manifest = Manifest(paths=[base])
    with open("manifest.yaml", "wb") as f:
        manifest.write(f)
    mtime_parent = os.stat(missing.parent).st_mtime
    missing.unlink()
    os.utime(missing.parent, times=(mtime_parent, mtime_parent))
    with tarfile.open(name, "w") as tarf:
        with open("manifest.yaml", "rb") as f:
            manifest_info = tarf.gettarinfo(arcname="base/.manifest.yaml", 
                                            fileobj=f)
            manifest_info.mode = stat.S_IFREG | 0o444
            tarf.addfile(manifest_info, f)
        tarf.add("base")
    with TemporaryFile(mode="w+t", dir=test_dir) as f:
        args = ["verify", name]
        callscript("archive-tool.py", args, returncode=3, stderr=f)
        f.seek(0)
        line = f.readline()
        assert "%s:%s: missing" % (name, missing) in line

def test_cli_check_stdin_and_files(test_dir, testname, monkeypatch):
    monkeypatch.chdir(test_dir)
    name = archive_name(tags=[testname])
    args = ["create", name, "base"]
    callscript("archive-tool.py", args)
    with TemporaryFile(mode="w+t", dir=test_dir) as f:
        args = ["check", "--stdin", name, "base"]
        callscript("archive-tool.py", args, returncode=2, stderr=f)
        f.seek(0)
        line = f.readline()
        assert line.startswith("usage: archive-tool.py ")
        while True:
            line = f.readline()
            if not line.startswith(" "):
                break
        assert "can't accept both, --stdin and the files argument" in line

