"""Test the error handling in the command line tool.
"""

import os
from pathlib import Path
import stat
import subprocess
import tarfile
from tempfile import TemporaryFile
from archive.manifest import Manifest
import pytest
from conftest import setup_testdata, callscript

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

@pytest.fixture(scope="module")
def test_dir(tmpdir):
    setup_testdata(tmpdir, **testdata)
    return tmpdir

def test_cli_helpmessage(test_dir, monkeypatch):
    monkeypatch.chdir(str(test_dir))
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["-h"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        line = f.readline()
        assert line.startswith("usage: archive-tool.py ")

def test_cli_missing_command(test_dir, monkeypatch):
    monkeypatch.chdir(str(test_dir))
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = []
        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            callscript("archive-tool.py", args, stderr=f)
        assert exc_info.value.returncode == 2
        f.seek(0)
        line = f.readline()
        assert line.startswith("usage: archive-tool.py ")
        while True:
            line = f.readline()
            if not line.startswith(" "):
                break
        assert "subcommand is required" in line

def test_cli_bogus_command(test_dir, monkeypatch):
    monkeypatch.chdir(str(test_dir))
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["bogus_cmd"]
        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            callscript("archive-tool.py", args, stderr=f)
        assert exc_info.value.returncode == 2
        f.seek(0)
        line = f.readline()
        assert line.startswith("usage: archive-tool.py ")
        while True:
            line = f.readline()
            if not line.startswith(" "):
                break
        assert "invalid choice: 'bogus_cmd'" in line

def test_cli_create_bogus_compression(test_dir, archive_name, monkeypatch):
    monkeypatch.chdir(str(test_dir))
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["create", "--compression=bogus_comp", archive_name, "base"]
        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            callscript("archive-tool.py", args, stderr=f)
        assert exc_info.value.returncode == 2
        f.seek(0)
        line = f.readline()
        assert line.startswith("usage: archive-tool.py ")
        while True:
            line = f.readline()
            if not line.startswith(" "):
                break
        assert "--compression: invalid choice: 'bogus_comp'" in line

def test_cli_ls_bogus_format(test_dir, archive_name, monkeypatch):
    monkeypatch.chdir(str(test_dir))
    args = ["create", archive_name, "base"]
    callscript("archive-tool.py", args)
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["ls", "--format=bogus_fmt", archive_name]
        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            callscript("archive-tool.py", args, stderr=f)
        assert exc_info.value.returncode == 2
        f.seek(0)
        line = f.readline()
        assert line.startswith("usage: archive-tool.py ")
        while True:
            line = f.readline()
            if not line.startswith(" "):
                break
        assert "--format: invalid choice: 'bogus_fmt'" in line

def test_cli_create_normalized_path(test_dir, archive_name, monkeypatch):
    monkeypatch.chdir(str(test_dir))
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["create", archive_name, "base/empty/.."]
        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            callscript("archive-tool.py", args, stderr=f)
        assert exc_info.value.returncode == 1
        f.seek(0)
        line = f.readline()
        assert "invalid path base/empty/..: must be normalized" in line

def test_cli_create_rel_start_basedir(test_dir, archive_name, monkeypatch):
    monkeypatch.chdir(str(test_dir))
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["create", "--basedir=base/data", archive_name, "base/msg.txt"]
        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            callscript("archive-tool.py", args, stderr=f)
        assert exc_info.value.returncode == 1
        f.seek(0)
        line = f.readline()
        assert "'base/msg.txt' does not start with 'base/data'" in line

def test_cli_ls_archive_not_found(test_dir, monkeypatch):
    monkeypatch.chdir(str(test_dir))
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["ls", "bogus.tar"]
        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            callscript("archive-tool.py", args, stderr=f)
        assert exc_info.value.returncode == 1
        f.seek(0)
        line = f.readline()
        assert "No such file or directory: 'bogus.tar'" in line

def test_cli_ls_checksum_invalid_hash(test_dir, archive_name, monkeypatch):
    monkeypatch.chdir(str(test_dir))
    args = ["create", archive_name, "base"]
    callscript("archive-tool.py", args)
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["ls", "--format=checksum", "--checksum=bogus", archive_name]
        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            callscript("archive-tool.py", args, stderr=f)
        assert exc_info.value.returncode == 1
        f.seek(0)
        line = f.readline()
        assert "'bogus' hashes not available" in line

def test_cli_info_missing_entry(test_dir, archive_name, monkeypatch):
    monkeypatch.chdir(str(test_dir))
    args = ["create", archive_name, "base"]
    callscript("archive-tool.py", args)
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["info", archive_name, "base/data/not-present"]
        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            callscript("archive-tool.py", args, stderr=f)
        assert exc_info.value.returncode == 1
        f.seek(0)
        line = f.readline()
        assert "base/data/not-present: not found in archive" in line

def test_cli_integrity_no_manifest(test_dir, archive_name, monkeypatch):
    monkeypatch.chdir(str(test_dir))
    with tarfile.open(archive_name, "w") as tarf:
        tarf.add("base", recursive=True)
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["ls", archive_name]
        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            callscript("archive-tool.py", args, stderr=f)
        assert exc_info.value.returncode == 3
        f.seek(0)
        line = f.readline()
        assert ".manifest.yaml not found" in line

def test_cli_integrity_missing_file(test_dir, archive_name, monkeypatch):
    monkeypatch.chdir(str(test_dir))
    base = Path("base")
    missing = base / "data" / "not-present"
    with missing.open("wt") as f:
        f.write("Hello!")
    manifest = Manifest(paths=[base])
    with open("manifest.yaml", "wb") as f:
        manifest.write(f)
    mtime_parent = os.stat(str(missing.parent)).st_mtime
    missing.unlink()
    os.utime(str(missing.parent), times=(mtime_parent, mtime_parent))
    with tarfile.open(archive_name, "w") as tarf:
        with open("manifest.yaml", "rb") as f:
            manifest_info = tarf.gettarinfo(arcname="base/.manifest.yaml", 
                                            fileobj=f)
            manifest_info.mode = stat.S_IFREG | 0o444
            tarf.addfile(manifest_info, f)
        tarf.add("base")
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["verify", archive_name]
        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            callscript("archive-tool.py", args, stderr=f)
        assert exc_info.value.returncode == 3
        f.seek(0)
        line = f.readline()
        assert "%s:%s: missing" % (archive_name, missing) in line

def test_cli_check_missing_files(test_dir, archive_name, monkeypatch):
    monkeypatch.chdir(str(test_dir))
    args = ["create", archive_name, "base"]
    callscript("archive-tool.py", args)
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", archive_name]
        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            callscript("archive-tool.py", args, stderr=f)
        assert exc_info.value.returncode == 2
        f.seek(0)
        line = f.readline()
        assert line.startswith("usage: archive-tool.py ")
        while True:
            line = f.readline()
            if not line.startswith(" "):
                break
        assert "either --stdin or the files argument is required" in line

def test_cli_check_stdin_and_files(test_dir, archive_name, monkeypatch):
    monkeypatch.chdir(str(test_dir))
    args = ["create", archive_name, "base"]
    callscript("archive-tool.py", args)
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", "--stdin", archive_name, "base"]
        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            callscript("archive-tool.py", args, stderr=f)
        assert exc_info.value.returncode == 2
        f.seek(0)
        line = f.readline()
        assert line.startswith("usage: archive-tool.py ")
        while True:
            line = f.readline()
            if not line.startswith(" "):
                break
        assert "can't accept both, --stdin and the files argument" in line

