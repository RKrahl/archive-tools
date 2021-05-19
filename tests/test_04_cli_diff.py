"""Test the diff subcommand in the command line tool.
"""

from pathlib import Path
import shutil
from tempfile import TemporaryFile
from archive import Archive
from archive.tools import tmp_chdir
import pytest
from conftest import *


# Setup a directory with some test data to be put into an archive.
# Make sure that we have all kind of different things in there.
testdata = [
    DataDir(Path("base"), 0o755),
    DataDir(Path("base", "data"), 0o750),
    DataDir(Path("base", "data", "aa"), 0o750),
    DataDir(Path("base", "data", "zz"), 0o750),
    DataDir(Path("base", "empty"), 0o755),
    DataFile(Path("base", "msg.txt"), 0o644),
    DataFile(Path("base", "data", "rnd.dat"), 0o600),
    DataFile(Path("base", "data", "rnd2.dat"), 0o600),
    DataRandomFile(Path("base", "data", "aa", "rnd_a.dat"), 0o600),
    DataRandomFile(Path("base", "data", "zz", "rnd_z.dat"), 0o600),
    DataFile(Path("base", "rnd.dat"), 0o600),
    DataSymLink(Path("base", "s.dat"), Path("data", "rnd.dat")),
]

@pytest.fixture(scope="module")
def test_dir(tmpdir):
    setup_testdata(tmpdir, testdata)
    with tmp_chdir(tmpdir):
        Archive().create(Path("archive-rel.tar"), "", [Path("base")])
        Archive().create(Path("archive-abs.tar"), "", [tmpdir / "base"])
    return tmpdir

@pytest.fixture(scope="function")
def test_data(request, test_dir):
    shutil.rmtree(test_dir / "base", ignore_errors=True)
    with Archive().open(test_dir / "archive-rel.tar") as archive:
        archive.extract(test_dir)
    return test_dir

@pytest.mark.parametrize("abspath", [False, True])
def test_diff_equal(test_data, testname, monkeypatch, abspath):
    """Diff two archives having equal content.
    """
    monkeypatch.chdir(test_data)
    if abspath:
        archive_ref_path = Path("archive-abs.tar")
        base_dir = test_data / "base"
    else:
        archive_ref_path = Path("archive-rel.tar")
        base_dir = Path("base")
    flag = absflag(abspath)
    archive_path = Path(archive_name(ext="bz2", tags=[testname, flag]))
    Archive().create(archive_path, "bz2", [base_dir])
    with TemporaryFile(mode="w+t", dir=test_data) as f:
        args = ["diff", str(archive_ref_path), str(archive_path)]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert list(get_output(f)) == []

@pytest.mark.parametrize("abspath", [False, True])
def test_diff_modified_file(test_data, testname, monkeypatch, abspath):
    """Diff two archives having one file's content modified.
    """
    monkeypatch.chdir(test_data)
    if abspath:
        archive_ref_path = Path("archive-abs.tar")
        base_dir = test_data / "base"
    else:
        archive_ref_path = Path("archive-rel.tar")
        base_dir = Path("base")
    p = base_dir / "rnd.dat"
    shutil.copy(gettestdata("rnd2.dat"), p)
    flag = absflag(abspath)
    archive_path = Path(archive_name(ext="bz2", tags=[testname, flag]))
    Archive().create(archive_path, "bz2", [base_dir])
    with TemporaryFile(mode="w+t", dir=test_data) as f:
        args = ["diff", str(archive_ref_path), str(archive_path)]
        callscript("archive-tool.py", args, returncode=101, stdout=f)
        f.seek(0)
        out = list(get_output(f))
        assert len(out) == 1
        assert out[0] == ("Files %s:%s and %s:%s differ"
                          % (archive_ref_path, p, archive_path, p))

@pytest.mark.parametrize("abspath", [False, True])
def test_diff_symlink_target(test_data, testname, monkeypatch, abspath):
    """Diff two archives having one symlink's target modified.
    """
    monkeypatch.chdir(test_data)
    if abspath:
        archive_ref_path = Path("archive-abs.tar")
        base_dir = test_data / "base"
    else:
        archive_ref_path = Path("archive-rel.tar")
        base_dir = Path("base")
    p = base_dir / "s.dat"
    p.unlink()
    p.symlink_to(Path("msg.txt"))
    flag = absflag(abspath)
    archive_path = Path(archive_name(ext="bz2", tags=[testname, flag]))
    Archive().create(archive_path, "bz2", [base_dir])
    with TemporaryFile(mode="w+t", dir=test_data) as f:
        args = ["diff", str(archive_ref_path), str(archive_path)]
        callscript("archive-tool.py", args, returncode=101, stdout=f)
        f.seek(0)
        out = list(get_output(f))
        assert len(out) == 1
        assert out[0] == ("Symbol links %s:%s and %s:%s have different target"
                          % (archive_ref_path, p, archive_path, p))

@pytest.mark.parametrize("abspath", [False, True])
def test_diff_wrong_type(test_data, testname, monkeypatch, abspath):
    """Diff two archives with one entry having a wrong type.
    """
    monkeypatch.chdir(test_data)
    if abspath:
        archive_ref_path = Path("archive-abs.tar")
        base_dir = test_data / "base"
    else:
        archive_ref_path = Path("archive-rel.tar")
        base_dir = Path("base")
    p = base_dir / "rnd.dat"
    p.unlink()
    p.symlink_to(Path("data", "rnd.dat"))
    flag = absflag(abspath)
    archive_path = Path(archive_name(ext="bz2", tags=[testname, flag]))
    Archive().create(archive_path, "bz2", [base_dir])
    with TemporaryFile(mode="w+t", dir=test_data) as f:
        args = ["diff", str(archive_ref_path), str(archive_path)]
        callscript("archive-tool.py", args, returncode=102, stdout=f)
        f.seek(0)
        out = list(get_output(f))
        assert len(out) == 1
        assert out[0] == ("Entries %s:%s and %s:%s have different type"
                          % (archive_ref_path, p, archive_path, p))

@pytest.mark.parametrize("abspath", [False, True])
def test_diff_missing_files(test_data, testname, monkeypatch, abspath):
    """Diff two archives having one file's name changed.
    """
    monkeypatch.chdir(test_data)
    if abspath:
        archive_ref_path = Path("archive-abs.tar")
        base_dir = test_data / "base"
    else:
        archive_ref_path = Path("archive-rel.tar")
        base_dir = Path("base")
    p1 = base_dir / "rnd.dat"
    p2 = base_dir / "a.dat"
    p1.rename(p2)
    flag = absflag(abspath)
    archive_path = Path(archive_name(ext="bz2", tags=[testname, flag]))
    Archive().create(archive_path, "bz2", [base_dir])
    with TemporaryFile(mode="w+t", dir=test_data) as f:
        args = ["diff", str(archive_ref_path), str(archive_path)]
        callscript("archive-tool.py", args, returncode=102, stdout=f)
        f.seek(0)
        out = list(get_output(f))
        assert len(out) == 2
        assert out[0] == "Only in %s: %s" % (archive_path, p2)
        assert out[1] == "Only in %s: %s" % (archive_ref_path, p1)

@pytest.mark.parametrize("abspath", [False, True])
def test_diff_mult(test_data, testname, monkeypatch, abspath):
    """Diff two archives having multiple differences.
    """
    monkeypatch.chdir(test_data)
    if abspath:
        archive_ref_path = Path("archive-abs.tar")
        base_dir = test_data / "base"
    else:
        archive_ref_path = Path("archive-rel.tar")
        base_dir = Path("base")
    pm = base_dir / "data" / "rnd.dat"
    shutil.copy(gettestdata("rnd2.dat"), pm)
    p1 = base_dir / "msg.txt"
    p2 = base_dir / "o.txt"
    p1.rename(p2)
    flag = absflag(abspath)
    archive_path = Path(archive_name(ext="bz2", tags=[testname, flag]))
    Archive().create(archive_path, "bz2", [base_dir])
    with TemporaryFile(mode="w+t", dir=test_data) as f:
        args = ["diff", str(archive_ref_path), str(archive_path)]
        callscript("archive-tool.py", args, returncode=102, stdout=f)
        f.seek(0)
        out = list(get_output(f))
        assert len(out) == 3
        assert out[0] == ("Files %s:%s and %s:%s differ"
                          % (archive_ref_path, pm, archive_path, pm))
        assert out[1] == "Only in %s: %s" % (archive_ref_path, p1)
        assert out[2] == "Only in %s: %s" % (archive_path, p2)

@pytest.mark.parametrize("abspath", [False, True])
def test_diff_metadata(test_data, testname, monkeypatch, abspath):
    """Diff two archives having one file's file system metadata modified.
    This difference should be ignored by default.
    """
    monkeypatch.chdir(test_data)
    if abspath:
        archive_ref_path = Path("archive-abs.tar")
        base_dir = test_data / "base"
    else:
        archive_ref_path = Path("archive-rel.tar")
        base_dir = Path("base")
    p = base_dir / "rnd.dat"
    p.chmod(0o0444)
    flag = absflag(abspath)
    archive_path = Path(archive_name(ext="bz2", tags=[testname, flag]))
    Archive().create(archive_path, "bz2", [base_dir])
    with TemporaryFile(mode="w+t", dir=test_data) as f:
        args = ["diff", str(archive_ref_path), str(archive_path)]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        assert list(get_output(f)) == []
    with TemporaryFile(mode="w+t", dir=test_data) as f:
        args = ["diff", "--report-meta",
                str(archive_ref_path), str(archive_path)]
        callscript("archive-tool.py", args, returncode=100, stdout=f)
        f.seek(0)
        out = list(get_output(f))
        assert len(out) == 1
        assert out[0] == ("File system metadata for %s:%s and %s:%s differ"
                          % (archive_ref_path, p, archive_path, p))

@pytest.mark.parametrize("abspath", [False, True])
def test_diff_missing_dir(test_data, testname, monkeypatch, abspath):
    """Diff two archives with one subdirectory missing.
    """
    monkeypatch.chdir(test_data)
    if abspath:
        archive_ref_path = Path("archive-abs.tar")
        base_dir = test_data / "base"
    else:
        archive_ref_path = Path("archive-rel.tar")
        base_dir = Path("base")
    pd = base_dir / "data" / "zz"
    shutil.rmtree(pd)
    flag = absflag(abspath)
    archive_path = Path(archive_name(ext="bz2", tags=[testname, flag]))
    Archive().create(archive_path, "bz2", [base_dir])
    with TemporaryFile(mode="w+t", dir=test_data) as f:
        args = ["diff", str(archive_ref_path), str(archive_path)]
        callscript("archive-tool.py", args, returncode=102, stdout=f)
        f.seek(0)
        out = list(get_output(f))
        assert len(out) == 2
        assert out[0] == "Only in %s: %s" % (archive_ref_path, pd)
        assert out[1] == "Only in %s: %s" % (archive_ref_path, pd / "rnd_z.dat")
    with TemporaryFile(mode="w+t", dir=test_data) as f:
        args = ["diff", "--skip-dir-content",
                str(archive_ref_path), str(archive_path)]
        callscript("archive-tool.py", args, returncode=102, stdout=f)
        f.seek(0)
        out = list(get_output(f))
        assert len(out) == 1
        assert out[0] == "Only in %s: %s" % (archive_ref_path, pd)

@pytest.mark.parametrize("abspath", [False, True])
def test_diff_orphan_dir_content(test_data, testname, monkeypatch, abspath):
    """Diff archives having content in a missing directory.  Ref. #56
    """
    monkeypatch.chdir(test_data)
    if abspath:
        base_dir = test_data / "base"
    else:
        base_dir = Path("base")
    pd = base_dir / "data"
    excl_a = [ pd / "zz" ]
    flag = absflag(abspath)
    archive_a = Path(archive_name(ext="bz2", tags=[testname, "a", flag]))
    Archive().create(archive_a, "bz2", [base_dir], excludes=excl_a)
    pm = pd / "rnd2.dat"
    shutil.copy(gettestdata("rnd.dat"), pm)
    incl_b = [ base_dir, pd / "aa", pd / "rnd2.dat", pd / "zz" ]
    excl_b = [ pd, pd / "rnd.dat" ]
    flag = absflag(abspath)
    archive_b = Path(archive_name(ext="bz2", tags=[testname, "b", flag]))
    Archive().create(archive_b, "bz2", incl_b, excludes=excl_b)
    with TemporaryFile(mode="w+t", dir=test_data) as f:
        args = ["diff", str(archive_a), str(archive_b)]
        callscript("archive-tool.py", args, returncode=102, stdout=f)
        f.seek(0)
        out = list(get_output(f))
        assert len(out) == 5
        assert out[0] == "Only in %s: %s" % (archive_a, pd)
        assert out[1] == "Only in %s: %s" % (archive_a, pd / "rnd.dat")
        assert out[2] == ("Files %s:%s and %s:%s differ"
                          % (archive_a, pm, archive_b, pm))
        assert out[3] == "Only in %s: %s" % (archive_b, pd / "zz")
        assert out[4] == "Only in %s: %s" % (archive_b, pd / "zz" / "rnd_z.dat")
    with TemporaryFile(mode="w+t", dir=test_data) as f:
        args = ["diff", "--skip-dir-content", str(archive_a), str(archive_b)]
        callscript("archive-tool.py", args, returncode=102, stdout=f)
        f.seek(0)
        out = list(get_output(f))
        assert len(out) == 1
        assert out[0] == "Only in %s: %s" % (archive_a, pd)

@pytest.mark.parametrize("abspath", [False, True])
def test_diff_extrafile_end(test_data, testname, monkeypatch, abspath):
    """The first archives has an extra entry as last item.  Ref. #55
    """
    monkeypatch.chdir(test_data)
    if abspath:
        archive_ref_path = Path("archive-abs.tar")
        base_dir = test_data / "base"
    else:
        archive_ref_path = Path("archive-rel.tar")
        base_dir = Path("base")
    p = base_dir / "zzz.dat"
    shutil.copy(gettestdata("rnd2.dat"), p)
    flag = absflag(abspath)
    archive_path = Path(archive_name(ext="bz2", tags=[testname, flag]))
    Archive().create(archive_path, "bz2", [base_dir])
    with TemporaryFile(mode="w+t", dir=test_data) as f:
        args = ["diff", str(archive_path), str(archive_ref_path)]
        callscript("archive-tool.py", args, returncode=102, stdout=f)
        f.seek(0)
        out = list(get_output(f))
        assert len(out) == 1
        assert out[0] == "Only in %s: %s" % (archive_path, p)
