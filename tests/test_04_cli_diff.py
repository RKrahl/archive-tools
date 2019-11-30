"""Test the diff subcommand in the command line tool.
"""

from pathlib import Path
import shutil
from tempfile import TemporaryFile
from archive import Archive
from archive.tools import tmp_chdir
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
    with tmp_chdir(tmpdir):
        Archive().create(Path("archive-rel.tar"), "", [Path("base")])
        Archive().create(Path("archive-abs.tar"), "", [tmpdir / "base"])
    return tmpdir

@pytest.fixture(scope="function")
def test_data(request, test_dir):
    shutil.rmtree(str(test_dir / "base"), ignore_errors=True)
    with Archive().open(test_dir / "archive-rel.tar") as archive:
        archive.extract(test_dir)
    return test_dir

def archive_name(request, abspath):
    fname = request.function.__name__
    absflag = "abs" if abspath else "rel"
    return Path("archive-%s-%s.tar.bz2" % (fname, absflag))

def get_output(fileobj):
    out = []
    while True:
        line = fileobj.readline()
        if not line:
            break
        out.append(line.strip())
    return out

@pytest.mark.parametrize("abspath", [False, True])
def test_diff_equal(test_data, request, monkeypatch, abspath):
    """Diff two archives having equal content.
    """
    monkeypatch.chdir(str(test_data))
    if abspath:
        archive_ref_path = Path("archive-abs.tar")
        base_dir = test_data / "base"
    else:
        archive_ref_path = Path("archive-rel.tar")
        base_dir = Path("base")
    archive_path = archive_name(request, abspath)
    Archive().create(archive_path, "bz2", [base_dir])
    with TemporaryFile(mode="w+t", dir=str(test_data)) as f:
        args = ["diff", str(archive_ref_path), str(archive_path)]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert get_output(f) == []

@pytest.mark.parametrize("abspath", [False, True])
def test_diff_modified_file(test_data, request, monkeypatch, abspath):
    """Diff two archives having one file's content modified.
    """
    monkeypatch.chdir(str(test_data))
    if abspath:
        archive_ref_path = Path("archive-abs.tar")
        base_dir = test_data / "base"
    else:
        archive_ref_path = Path("archive-rel.tar")
        base_dir = Path("base")
    p = base_dir / "rnd.dat"
    shutil.copy(str(gettestdata("rnd2.dat")), str(p))
    archive_path = archive_name(request, abspath)
    Archive().create(archive_path, "bz2", [base_dir])
    with TemporaryFile(mode="w+t", dir=str(test_data)) as f:
        args = ["diff", str(archive_ref_path), str(archive_path)]
        callscript("archive-tool.py", args, returncode=101, stdout=f)
        f.seek(0)
        out = get_output(f)
        assert len(out) == 1
        assert out[0] == ("Files %s:%s and %s:%s differ"
                          % (archive_ref_path, p, archive_path, p))

@pytest.mark.parametrize("abspath", [False, True])
def test_diff_symlink_target(test_data, request, monkeypatch, abspath):
    """Diff two archives having one symlink's target modified.
    """
    monkeypatch.chdir(str(test_data))
    if abspath:
        archive_ref_path = Path("archive-abs.tar")
        base_dir = test_data / "base"
    else:
        archive_ref_path = Path("archive-rel.tar")
        base_dir = Path("base")
    p = base_dir / "s.dat"
    p.unlink()
    p.symlink_to(Path("msg.txt"))
    archive_path = archive_name(request, abspath)
    Archive().create(archive_path, "bz2", [base_dir])
    with TemporaryFile(mode="w+t", dir=str(test_data)) as f:
        args = ["diff", str(archive_ref_path), str(archive_path)]
        callscript("archive-tool.py", args, returncode=101, stdout=f)
        f.seek(0)
        out = get_output(f)
        assert len(out) == 1
        assert out[0] == ("Symbol links %s:%s and %s:%s have different target"
                          % (archive_ref_path, p, archive_path, p))

@pytest.mark.parametrize("abspath", [False, True])
def test_diff_wrong_type(test_data, request, monkeypatch, abspath):
    """Diff two archives with one entry having a wrong type.
    """
    monkeypatch.chdir(str(test_data))
    if abspath:
        archive_ref_path = Path("archive-abs.tar")
        base_dir = test_data / "base"
    else:
        archive_ref_path = Path("archive-rel.tar")
        base_dir = Path("base")
    p = base_dir / "rnd.dat"
    p.unlink()
    p.symlink_to(Path("data", "rnd.dat"))
    archive_path = archive_name(request, abspath)
    Archive().create(archive_path, "bz2", [base_dir])
    with TemporaryFile(mode="w+t", dir=str(test_data)) as f:
        args = ["diff", str(archive_ref_path), str(archive_path)]
        callscript("archive-tool.py", args, returncode=102, stdout=f)
        f.seek(0)
        out = get_output(f)
        assert len(out) == 1
        assert out[0] == ("Entries %s:%s and %s:%s have different type"
                          % (archive_ref_path, p, archive_path, p))

@pytest.mark.parametrize("abspath", [False, True])
def test_diff_missing_files(test_data, request, monkeypatch, abspath):
    """Diff two archives having one file's name changed.
    """
    monkeypatch.chdir(str(test_data))
    if abspath:
        archive_ref_path = Path("archive-abs.tar")
        base_dir = test_data / "base"
    else:
        archive_ref_path = Path("archive-rel.tar")
        base_dir = Path("base")
    p1 = base_dir / "rnd.dat"
    p2 = base_dir / "a.dat"
    p1.rename(p2)
    archive_path = archive_name(request, abspath)
    Archive().create(archive_path, "bz2", [base_dir])
    with TemporaryFile(mode="w+t", dir=str(test_data)) as f:
        args = ["diff", str(archive_ref_path), str(archive_path)]
        callscript("archive-tool.py", args, returncode=102, stdout=f)
        f.seek(0)
        out = get_output(f)
        assert len(out) == 2
        assert out[0] == "Only in %s: %s" % (archive_path, p2)
        assert out[1] == "Only in %s: %s" % (archive_ref_path, p1)

@pytest.mark.parametrize("abspath", [False, True])
def test_diff_mult(test_data, request, monkeypatch, abspath):
    """Diff two archives having multiple differences.
    """
    monkeypatch.chdir(str(test_data))
    if abspath:
        archive_ref_path = Path("archive-abs.tar")
        base_dir = test_data / "base"
    else:
        archive_ref_path = Path("archive-rel.tar")
        base_dir = Path("base")
    pm = base_dir / "data" / "rnd.dat"
    shutil.copy(str(gettestdata("rnd2.dat")), str(pm))
    p1 = base_dir / "msg.txt"
    p2 = base_dir / "o.txt"
    p1.rename(p2)
    archive_path = archive_name(request, abspath)
    Archive().create(archive_path, "bz2", [base_dir])
    with TemporaryFile(mode="w+t", dir=str(test_data)) as f:
        args = ["diff", str(archive_ref_path), str(archive_path)]
        callscript("archive-tool.py", args, returncode=102, stdout=f)
        f.seek(0)
        out = get_output(f)
        assert len(out) == 3
        assert out[0] == ("Files %s:%s and %s:%s differ"
                          % (archive_ref_path, pm, archive_path, pm))
        assert out[1] == "Only in %s: %s" % (archive_ref_path, p1)
        assert out[2] == "Only in %s: %s" % (archive_path, p2)

@pytest.mark.parametrize("abspath", [False, True])
def test_diff_metadata(test_data, request, monkeypatch, abspath):
    """Diff two archives having one file's file system metadata modified.
    This difference should be ignored by default.
    """
    monkeypatch.chdir(str(test_data))
    if abspath:
        archive_ref_path = Path("archive-abs.tar")
        base_dir = test_data / "base"
    else:
        archive_ref_path = Path("archive-rel.tar")
        base_dir = Path("base")
    p = base_dir / "rnd.dat"
    p.chmod(0o0444)
    archive_path = archive_name(request, abspath)
    Archive().create(archive_path, "bz2", [base_dir])
    with TemporaryFile(mode="w+t", dir=str(test_data)) as f:
        args = ["diff", str(archive_ref_path), str(archive_path)]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert get_output(f) == []
    with TemporaryFile(mode="w+t", dir=str(test_data)) as f:
        args = ["diff", "--report-meta",
                str(archive_ref_path), str(archive_path)]
        callscript("archive-tool.py", args, returncode=100, stdout=f)
        f.seek(0)
        out = get_output(f)
        assert len(out) == 1
        assert out[0] == ("File system metadata for %s:%s and %s:%s differ"
                          % (archive_ref_path, p, archive_path, p))

def test_diff_basedir_equal(test_data, request, monkeypatch):
    """Diff two archives with different base directories having equal
    content.

    This test makes only sense for archives with relative path names.
    """
    monkeypatch.chdir(str(test_data))
    newbase = Path("newbase")
    shutil.rmtree(str(newbase), ignore_errors=True)
    Path("base").rename(newbase)
    archive_ref_path = Path("archive-rel.tar")
    archive_path = archive_name(request, False)
    Archive().create(archive_path, "bz2", [newbase])
    with TemporaryFile(mode="w+t", dir=str(test_data)) as f:
        args = ["diff", str(archive_ref_path), str(archive_path)]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert get_output(f) == []

def test_diff_basedir_mod_file(test_data, request, monkeypatch):
    """Diff two archives with different base directories having one file's
    content modified.

    This test makes only sense for archives with relative path names.
    """
    monkeypatch.chdir(str(test_data))
    base = Path("base")
    newbase = Path("newbase")
    shutil.rmtree(str(newbase), ignore_errors=True)
    base.rename(newbase)
    archive_ref_path = Path("archive-rel.tar")
    p = base / "rnd.dat"
    pn = newbase / "rnd.dat"
    shutil.copy(str(gettestdata("rnd2.dat")), str(pn))
    archive_path = archive_name(request, False)
    Archive().create(archive_path, "bz2", [newbase])
    with TemporaryFile(mode="w+t", dir=str(test_data)) as f:
        args = ["diff", str(archive_ref_path), str(archive_path)]
        callscript("archive-tool.py", args, returncode=101, stdout=f)
        f.seek(0)
        out = get_output(f)
        assert len(out) == 1
        assert out[0] == ("Files %s:%s and %s:%s differ"
                          % (archive_ref_path, p, archive_path, pn))

@pytest.mark.parametrize("abspath", [False, True])
def test_diff_dircontent(test_data, request, monkeypatch, abspath):
    """Diff two archives with one subdirectory missing.
    """
    monkeypatch.chdir(str(test_data))
    if abspath:
        archive_ref_path = Path("archive-abs.tar")
        base_dir = test_data / "base"
    else:
        archive_ref_path = Path("archive-rel.tar")
        base_dir = Path("base")
    pd = base_dir / "data"
    shutil.rmtree(str(pd))
    archive_path = archive_name(request, abspath)
    Archive().create(archive_path, "bz2", [base_dir])
    with TemporaryFile(mode="w+t", dir=str(test_data)) as f:
        args = ["diff", str(archive_ref_path), str(archive_path)]
        callscript("archive-tool.py", args, returncode=102, stdout=f)
        f.seek(0)
        out = get_output(f)
        assert len(out) == 2
        assert out[0] == "Only in %s: %s" % (archive_ref_path, pd)
        assert out[1] == "Only in %s: %s" % (archive_ref_path, pd / "rnd.dat")
    with TemporaryFile(mode="w+t", dir=str(test_data)) as f:
        args = ["diff", "--skip-dir-content",
                str(archive_ref_path), str(archive_path)]
        callscript("archive-tool.py", args, returncode=102, stdout=f)
        f.seek(0)
        out = get_output(f)
        assert len(out) == 1
        assert out[0] == "Only in %s: %s" % (archive_ref_path, pd)
