"""Test the diff subcommand in the command line tool.
"""

from pathlib import Path
import shutil
from tempfile import TemporaryFile
from archive import Archive
import pytest
from conftest import gettestdata, setup_testdata, callscript

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
        (Path("base", "data", "rnd.dat"), 0o640),
        (Path("base", "rnd.dat"), 0o600),
    ],
    "symlinks": [
        (Path("base", "s.dat"), Path("data", "rnd.dat")),
    ]
}

@pytest.fixture(scope="module")
def test_dir(tmpdir):
    setup_testdata(tmpdir, **testdata)
    Archive().create(Path("archive.tar"), "", [Path("base")], workdir=tmpdir)
    return tmpdir

@pytest.fixture(scope="function")
def copy_data(request, test_dir):
    copy_dir = test_dir / request.function.__name__
    shutil.copytree(str(test_dir / "base"), str(copy_dir / "base"), 
                    symlinks=True)
    return copy_dir

def get_output(fileobj):
    out = []
    while True:
        line = fileobj.readline()
        if not line:
            break
        out.append(line.strip())
    return out

def test_diff_equal(test_dir, copy_data, archive_name, monkeypatch):
    """Diff two archives having equal content.
    """
    monkeypatch.chdir(str(copy_data))
    archive_ref_path = test_dir / "archive.tar"
    archive_path = test_dir / (archive_name + ".bz2")
    Archive().create(archive_path, "bz2", [Path("base")])
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["diff", str(archive_ref_path), str(archive_path)]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert get_output(f) == []

def test_diff_modified_file(test_dir, copy_data, archive_name, monkeypatch):
    """Diff two archives having one file's content modified.
    """
    monkeypatch.chdir(str(copy_data))
    p = Path("base", "rnd.dat")
    shutil.copy(str(gettestdata("rnd2.dat")), str(p))
    archive_ref_path = test_dir / "archive.tar"
    archive_path = test_dir / (archive_name + ".bz2")
    Archive().create(archive_path, "bz2", [Path("base")])
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["diff", str(archive_ref_path), str(archive_path)]
        callscript("archive-tool.py", args, returncode=101, stdout=f)
        f.seek(0)
        out = get_output(f)
        assert len(out) == 1
        assert out[0] == ("Files %s:%s and %s:%s differ"
                          % (archive_ref_path, p, archive_path, p))

def test_diff_symlink_target(test_dir, copy_data, archive_name, monkeypatch):
    """Diff two archives having one symlink's target modified.
    """
    monkeypatch.chdir(str(copy_data))
    p = Path("base", "s.dat")
    p.unlink()
    p.symlink_to(Path("msg.txt"))
    archive_ref_path = test_dir / "archive.tar"
    archive_path = test_dir / (archive_name + ".bz2")
    Archive().create(archive_path, "bz2", [Path("base")])
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["diff", str(archive_ref_path), str(archive_path)]
        callscript("archive-tool.py", args, returncode=101, stdout=f)
        f.seek(0)
        out = get_output(f)
        assert len(out) == 1
        assert out[0] == ("Symbol links %s:%s and %s:%s have different target"
                          % (archive_ref_path, p, archive_path, p))

def test_diff_wrong_type(test_dir, copy_data, archive_name, monkeypatch):
    """Diff two archives with one entry having a wrong type.
    """
    monkeypatch.chdir(str(copy_data))
    p = Path("base", "rnd.dat")
    p.unlink()
    p.symlink_to(Path("data", "rnd.dat"))
    archive_ref_path = test_dir / "archive.tar"
    archive_path = test_dir / (archive_name + ".bz2")
    Archive().create(archive_path, "bz2", [Path("base")])
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["diff", str(archive_ref_path), str(archive_path)]
        callscript("archive-tool.py", args, returncode=102, stdout=f)
        f.seek(0)
        out = get_output(f)
        assert len(out) == 1
        assert out[0] == ("Entries %s:%s and %s:%s have different type"
                          % (archive_ref_path, p, archive_path, p))

def test_diff_missing_files(test_dir, copy_data, archive_name, monkeypatch):
    """Diff two archives having one file's name changed.
    """
    monkeypatch.chdir(str(copy_data))
    p1 = Path("base", "rnd.dat")
    p2 = Path("base", "a.dat")
    p1.rename(p2)
    archive_ref_path = test_dir / "archive.tar"
    archive_path = test_dir / (archive_name + ".bz2")
    Archive().create(archive_path, "bz2", [Path("base")])
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["diff", str(archive_ref_path), str(archive_path)]
        callscript("archive-tool.py", args, returncode=102, stdout=f)
        f.seek(0)
        out = get_output(f)
        assert len(out) == 2
        assert out[0] == "Only in %s: %s" % (archive_path, p2)
        assert out[1] == "Only in %s: %s" % (archive_ref_path, p1)

def test_diff_metadata(test_dir, copy_data, archive_name, monkeypatch):
    """Diff two archives having one file's file system metadata modified.
    This difference should be ignored by default.
    """
    monkeypatch.chdir(str(copy_data))
    p = Path("base", "rnd.dat")
    p.chmod(0o0444)
    archive_ref_path = test_dir / "archive.tar"
    archive_path = test_dir / (archive_name + ".bz2")
    Archive().create(archive_path, "bz2", [Path("base")])
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["diff", str(archive_ref_path), str(archive_path)]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert get_output(f) == []
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["diff", "--report-meta",
                str(archive_ref_path), str(archive_path)]
        callscript("archive-tool.py", args, returncode=100, stdout=f)
        f.seek(0)
        out = get_output(f)
        assert len(out) == 1
        assert out[0] == ("File system metadata for %s:%s and %s:%s differ"
                          % (archive_ref_path, p, archive_path, p))
