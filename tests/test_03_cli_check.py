"""Test the check subcommand in the command line tool.
"""

import os
from pathlib import Path
import shutil
import tarfile
from tempfile import TemporaryFile
from archive import Archive
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
all_test_files = {
    str(f[0]) for f in testdata["files"] + testdata["symlinks"]
} 

@pytest.fixture(scope="module")
def test_dir(tmpdir):
    setup_testdata(tmpdir, **testdata)
    Archive().create("archive.tar", "", ["base"], workdir=tmpdir)
    return tmpdir

@pytest.fixture(scope="function")
def copy_data(request, test_dir):
    copy_dir = test_dir / request.function.__name__
    shutil.copytree(str(test_dir / "base"), str(copy_dir / "base"), 
                    symlinks=True)
    return copy_dir

def get_results(fileobj):
    results = set()
    while True:
        line = fileobj.readline()
        if not line:
            break
        results.add(line.strip())
    return results

def test_check_allmatch(test_dir, copy_data, monkeypatch):
    monkeypatch.chdir(str(copy_data))
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", "../archive.tar", "base"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert get_results(f) == set()

def test_check_add_file(test_dir, copy_data, monkeypatch):
    monkeypatch.chdir(str(copy_data))
    fp = Path("base", "new_msg.txt")
    with fp.open("wt") as f:
        print("Greeting!", file=f)
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", "../archive.tar", "base"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert get_results(f) == {str(fp)}

def test_check_change_type(test_dir, copy_data, monkeypatch):
    monkeypatch.chdir(str(copy_data))
    fp = Path("base", "s.dat")
    fp.unlink()
    shutil.copy2(str(Path("base", "data", "rnd.dat")), str(fp))
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", "../archive.tar", "base"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert get_results(f) == {str(fp)}

def test_check_touch_file(test_dir, copy_data, monkeypatch):
    monkeypatch.chdir(str(copy_data))
    fp = Path("base", "data", "rnd.dat")
    fp.touch()
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", "../archive.tar", "base"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert get_results(f) == {str(fp)}

def test_check_modify_file(test_dir, copy_data, monkeypatch):
    monkeypatch.chdir(str(copy_data))
    fp = Path("base", "data", "rnd.dat")
    st = fp.stat()
    with fp.open("wb") as f:
        f.write(b" " * st.st_size)
    os.utime(str(fp), (st.st_mtime, st.st_mtime))
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", "../archive.tar", "base"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert get_results(f) == {str(fp)}

def test_check_symlink_target(test_dir, copy_data, monkeypatch):
    monkeypatch.chdir(str(copy_data))
    fp = Path("base", "s.dat")
    fp.unlink()
    fp.symlink_to(Path("msg.txt"))
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", "../archive.tar", "base"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert get_results(f) == {str(fp)}

def test_check_present_allmatch(test_dir, copy_data, monkeypatch):
    monkeypatch.chdir(str(copy_data))
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", "--present", "../archive.tar", "base"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert get_results(f) == all_test_files

def test_check_present_add_file(test_dir, copy_data, monkeypatch):
    monkeypatch.chdir(str(copy_data))
    fp = Path("base", "new_msg.txt")
    with fp.open("wt") as f:
        print("Greeting!", file=f)
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", "--present", "../archive.tar", "base"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert get_results(f) == all_test_files - {str(fp)}

def test_check_present_change_type(test_dir, copy_data, monkeypatch):
    monkeypatch.chdir(str(copy_data))
    fp = Path("base", "s.dat")
    fp.unlink()
    shutil.copy2(str(Path("base", "data", "rnd.dat")), str(fp))
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", "--present", "../archive.tar", "base"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert get_results(f) == all_test_files - {str(fp)}

def test_check_present_touch_file(test_dir, copy_data, monkeypatch):
    monkeypatch.chdir(str(copy_data))
    fp = Path("base", "data", "rnd.dat")
    fp.touch()
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", "--present", "../archive.tar", "base"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert get_results(f) == all_test_files - {str(fp)}

def test_check_present_modify_file(test_dir, copy_data, monkeypatch):
    monkeypatch.chdir(str(copy_data))
    fp = Path("base", "data", "rnd.dat")
    st = fp.stat()
    with fp.open("wb") as f:
        f.write(b" " * st.st_size)
    os.utime(str(fp), (st.st_mtime, st.st_mtime))
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", "--present", "../archive.tar", "base"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert get_results(f) == all_test_files - {str(fp)}

def test_check_present_symlink_target(test_dir, copy_data, monkeypatch):
    monkeypatch.chdir(str(copy_data))
    fp = Path("base", "s.dat")
    fp.unlink()
    fp.symlink_to(Path("msg.txt"))
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", "--present", "../archive.tar", "base"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert get_results(f) == all_test_files - {str(fp)}

def test_check_extract_archive(test_dir, request, monkeypatch):
    """When extracting an archive and checking the result, 
    check should not report any file to be missing in the archive.

    In particular, it should not report metadata such as the manifest
    file to be missing in the archive, even though these metadata are
    not listed in the manifest.  Issue #25.
    """
    check_dir = test_dir / request.function.__name__
    check_dir.mkdir()
    monkeypatch.chdir(str(check_dir))
    with tarfile.open("../archive.tar", "r") as tarf:
        tarf.extractall()
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", "../archive.tar", "base"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert get_results(f) == set()

def test_check_extract_archive_custom_metadata(test_dir, request, monkeypatch):
    """When extracting an archive and checking the result, 
    check should not report any file to be missing in the archive.

    Same as test_check_extract_archive(), but now using an archive
    having custom metadata.  Issue #25.
    """
    archive_path = test_dir / "archive-custom-md.tar"
    with TemporaryFile(dir=str(test_dir)) as tmpf:
        archive = Archive()
        tmpf.write("Hello world!\n".encode("ascii"))
        tmpf.seek(0)
        archive.add_metadata(".msg.txt", tmpf)
        archive.create(archive_path, "", ["base"], workdir=test_dir)
    check_dir = test_dir / request.function.__name__
    check_dir.mkdir()
    monkeypatch.chdir(str(check_dir))
    with tarfile.open(str(archive_path), "r") as tarf:
        tarf.extractall()
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", str(archive_path), "base"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert get_results(f) == set()

def test_check_present_extract_archive(test_dir, request, monkeypatch):
    """When extracting an archive and checking the result, 
    check should report all file to be present in the archive.

    If called with the "--present" flag, it should list the full
    content of the directory extracted from the archive, including
    metadata such as the manifest file, even though these metadata are
    not listed in the manifest.  Issue #25.
    """
    check_dir = test_dir / request.function.__name__
    check_dir.mkdir()
    monkeypatch.chdir(str(check_dir))
    with tarfile.open("../archive.tar", "r") as tarf:
        tarf.extractall()
    all_files = all_test_files | { 'base/.manifest.yaml' }
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", "--present", "../archive.tar", "base"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert get_results(f) == all_files
