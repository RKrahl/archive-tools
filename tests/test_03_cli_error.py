"""Test the error handling in the command line tool.
"""

from pathlib import Path
import subprocess
from tempfile import TemporaryFile
import pytest
from conftest import archive_name, setup_testdata, callscript

# Setup a directory with some test data to be put into an archive.
# Make sure that we have all kind if different things in there.
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
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["create", archive_name, "base"]
        callscript("archive-tool.py", args)
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
