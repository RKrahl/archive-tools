"""Test the check subcommand in the command line tool.
"""

import os
from pathlib import Path
import shutil
import tarfile
from tempfile import TemporaryFile
from archive import Archive
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
all_test_files = { str(f.path) for f in testdata if f.type in {'f', 'l'} }

@pytest.fixture(scope="module")
def test_dir(tmpdir):
    setup_testdata(tmpdir, testdata)
    Archive().create(Path("archive.tar"), "", [Path("base")], workdir=tmpdir)
    return tmpdir

@pytest.fixture(scope="function")
def copy_data(testname, test_dir):
    copy_dir = test_dir / testname
    shutil.copytree(str(test_dir / "base"), str(copy_dir / "base"), 
                    symlinks=True)
    return copy_dir

@pytest.fixture(scope="function")
def extract_archive(testname, test_dir):
    archive_path = test_dir / "archive.tar"
    check_dir = test_dir / testname
    check_dir.mkdir()
    with tarfile.open(str(archive_path), "r") as tarf:
        tarf.extractall(path=str(check_dir))
    return check_dir

def test_check_allmatch(test_dir, copy_data, monkeypatch):
    monkeypatch.chdir(str(copy_data))
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", str(test_dir / "archive.tar"), "base"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert set(get_output(f)) == set()

def test_check_add_file(test_dir, copy_data, monkeypatch):
    monkeypatch.chdir(str(copy_data))
    fp = Path("base", "new_msg.txt")
    with fp.open("wt") as f:
        print("Greeting!", file=f)
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", str(test_dir / "archive.tar"), "base"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert set(get_output(f)) == {str(fp)}

def test_check_change_type(test_dir, copy_data, monkeypatch):
    monkeypatch.chdir(str(copy_data))
    fp = Path("base", "s.dat")
    fp.unlink()
    shutil.copy2(str(Path("base", "data", "rnd.dat")), str(fp))
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", str(test_dir / "archive.tar"), "base"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert set(get_output(f)) == {str(fp)}

def test_check_touch_file(test_dir, copy_data, monkeypatch):
    monkeypatch.chdir(str(copy_data))
    fp = Path("base", "data", "rnd.dat")
    fp.touch()
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", str(test_dir / "archive.tar"), "base"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert set(get_output(f)) == {str(fp)}

def test_check_modify_file(test_dir, copy_data, monkeypatch):
    monkeypatch.chdir(str(copy_data))
    fp = Path("base", "data", "rnd.dat")
    st = fp.stat()
    with fp.open("wb") as f:
        f.write(b" " * st.st_size)
    os.utime(str(fp), (st.st_mtime, st.st_mtime))
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", str(test_dir / "archive.tar"), "base"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert set(get_output(f)) == {str(fp)}

def test_check_symlink_target(test_dir, copy_data, monkeypatch):
    monkeypatch.chdir(str(copy_data))
    fp = Path("base", "s.dat")
    fp.unlink()
    fp.symlink_to(Path("msg.txt"))
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", str(test_dir / "archive.tar"), "base"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert set(get_output(f)) == {str(fp)}

def test_check_present_allmatch(test_dir, copy_data, monkeypatch):
    monkeypatch.chdir(str(copy_data))
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", "--present", str(test_dir / "archive.tar"), "base"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert set(get_output(f)) == all_test_files

def test_check_present_add_file(test_dir, copy_data, monkeypatch):
    monkeypatch.chdir(str(copy_data))
    fp = Path("base", "new_msg.txt")
    with fp.open("wt") as f:
        print("Greeting!", file=f)
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", "--present", str(test_dir / "archive.tar"), "base"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert set(get_output(f)) == all_test_files - {str(fp)}

def test_check_present_change_type(test_dir, copy_data, monkeypatch):
    monkeypatch.chdir(str(copy_data))
    fp = Path("base", "s.dat")
    fp.unlink()
    shutil.copy2(str(Path("base", "data", "rnd.dat")), str(fp))
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", "--present", str(test_dir / "archive.tar"), "base"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert set(get_output(f)) == all_test_files - {str(fp)}

def test_check_present_touch_file(test_dir, copy_data, monkeypatch):
    monkeypatch.chdir(str(copy_data))
    fp = Path("base", "data", "rnd.dat")
    fp.touch()
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", "--present", str(test_dir / "archive.tar"), "base"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert set(get_output(f)) == all_test_files - {str(fp)}

def test_check_present_modify_file(test_dir, copy_data, monkeypatch):
    monkeypatch.chdir(str(copy_data))
    fp = Path("base", "data", "rnd.dat")
    st = fp.stat()
    with fp.open("wb") as f:
        f.write(b" " * st.st_size)
    os.utime(str(fp), (st.st_mtime, st.st_mtime))
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", "--present", str(test_dir / "archive.tar"), "base"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert set(get_output(f)) == all_test_files - {str(fp)}

def test_check_present_symlink_target(test_dir, copy_data, monkeypatch):
    monkeypatch.chdir(str(copy_data))
    fp = Path("base", "s.dat")
    fp.unlink()
    fp.symlink_to(Path("msg.txt"))
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", "--present", str(test_dir / "archive.tar"), "base"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert set(get_output(f)) == all_test_files - {str(fp)}

def test_check_extract_archive(test_dir, extract_archive, monkeypatch):
    """When extracting an archive and checking the result, 
    check should not report any file to be missing in the archive.

    In particular, it should not report metadata such as the manifest
    file to be missing in the archive, even though these metadata are
    not listed in the manifest.  Issue #25.
    """
    monkeypatch.chdir(str(extract_archive))
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", str(test_dir / "archive.tar"), "base"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert set(get_output(f)) == set()

def test_check_extract_archive_custom_metadata(test_dir, testname, monkeypatch):
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
        archive.create(archive_path, "", [Path("base")], workdir=test_dir)
    check_dir = test_dir / testname
    check_dir.mkdir()
    monkeypatch.chdir(str(check_dir))
    with tarfile.open(str(archive_path), "r") as tarf:
        tarf.extractall()
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", str(archive_path), "base"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert set(get_output(f)) == set()

def test_check_present_extract_archive(test_dir, extract_archive, monkeypatch):
    """When extracting an archive and checking the result, 
    check should report all file to be present in the archive.

    If called with the "--present" flag, it should list the full
    content of the directory extracted from the archive, including
    metadata such as the manifest file, even though these metadata are
    not listed in the manifest.  Issue #25.
    """
    monkeypatch.chdir(str(extract_archive))
    all_files = all_test_files | { 'base/.manifest.yaml' }
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", "--present", str(test_dir / "archive.tar"), "base"]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert set(get_output(f)) == all_files

def test_check_prefix_allmatch(test_dir, copy_data, monkeypatch):
    """Test the --prefix argument to archive-tool check.

    The test situation is that all files to be checked are in some
    subdirectory in the archive.  All files (actually, it's only one)
    match.
    """
    archive_path = test_dir / "archive.tar"
    prefix = Path("base", "data")
    monkeypatch.chdir(str(copy_data / prefix))
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", "--prefix", str(prefix), str(archive_path), "."]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert set(get_output(f)) == set()

def test_check_prefix_present_allmatch(test_dir, copy_data, monkeypatch):
    """Test the --prefix argument to archive-tool check.

    Same test situation as above, but now use the --present flag to
    show all matching files.
    """
    archive_path = test_dir / "archive.tar"
    prefix = Path("base", "data")
    monkeypatch.chdir(str(copy_data / prefix))
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", "--prefix", str(prefix), "--present", 
                str(archive_path), "."]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert set(get_output(f)) == {"rnd.dat"}

def test_check_prefix_extract(test_dir, extract_archive, monkeypatch):
    """Test the --prefix argument to archive-tool check.

    Call check from within the basedir of an extracted archive.  This
    test essentially checks that the --prefix argument also works for
    metadata files.
    """
    archive_path = test_dir / "archive.tar"
    prefix = Path("base")
    monkeypatch.chdir(str(extract_archive / prefix))
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", "--prefix", str(prefix), str(archive_path), "."]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert set(get_output(f)) == set()

def test_check_prefix_present_extract(test_dir, extract_archive, monkeypatch):
    """Test the --prefix argument to archive-tool check.

    Same test situation as above, but now use the --present flag to
    show all matching files.
    """
    archive_path = test_dir / "archive.tar"
    prefix = Path("base")
    monkeypatch.chdir(str(extract_archive / prefix))
    all_files = {
        str(f.path.relative_to(prefix))
        for f in testdata if f.type in {'f', 'l'}
    } | { '.manifest.yaml' }
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["check", "--prefix", str(prefix), "--present", 
                str(archive_path), "."]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert set(get_output(f)) == all_files

def test_check_stdin(test_dir, copy_data, monkeypatch):
    monkeypatch.chdir(str(copy_data))
    old_file = Path("base", "data", "rnd.dat")
    new_file = Path("base", "new_msg.txt")
    with new_file.open("wt") as f:
        print("Greeting!", file=f)
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f_out:
        args = ["check", "--stdin", str(test_dir / "archive.tar")]
        with TemporaryFile(mode="w+t", dir=str(test_dir)) as f_in:
            print(str(old_file), file=f_in)
            print(str(new_file), file=f_in)
            f_in.seek(0)
            callscript("archive-tool.py", args, stdin=f_in, stdout=f_out)
        f_out.seek(0)
        assert set(get_output(f_out)) == {str(new_file)}

def test_check_stdin_present(test_dir, copy_data, monkeypatch):
    monkeypatch.chdir(str(copy_data))
    old_file = Path("base", "data", "rnd.dat")
    new_file = Path("base", "new_msg.txt")
    with new_file.open("wt") as f:
        print("Greeting!", file=f)
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f_out:
        args = ["check", "--present", "--stdin", str(test_dir / "archive.tar")]
        with TemporaryFile(mode="w+t", dir=str(test_dir)) as f_in:
            print(str(old_file), file=f_in)
            print(str(new_file), file=f_in)
            f_in.seek(0)
            callscript("archive-tool.py", args, stdin=f_in, stdout=f_out)
        f_out.seek(0)
        assert set(get_output(f_out)) == {str(old_file)}
