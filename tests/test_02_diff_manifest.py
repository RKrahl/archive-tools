"""Test diff_manifest() function in archive.manifest.
"""

import os
from pathlib import Path
import shutil
from tempfile import TemporaryFile
from archive.archive import Archive
from archive.manifest import DiffStatus, FileInfo, diff_manifest
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
    DataFile(Path("base", "rnd.dat"), 0o600),
    DataSymLink(Path("base", "s.dat"), Path("data", "rnd.dat")),
]

def get_fileinfos(base):
    fileinfos = FileInfo.iterpaths([base], set())
    return sorted(fileinfos, key = lambda fi: fi.path)

def non_match(t):
    return t[0] != DiffStatus.MATCH

@pytest.fixture(scope="module")
def test_dir(tmpdir):
    setup_testdata(tmpdir, testdata)
    Archive().create(Path("archive.tar"), "", [Path("base")], workdir=tmpdir)
    return tmpdir

@pytest.fixture(scope="function")
def test_data(request, test_dir):
    shutil.rmtree(test_dir / "base", ignore_errors=True)
    with Archive().open(test_dir / "archive.tar") as archive:
        archive.extract(test_dir)
    return test_dir

def test_diff_manifest_equal(test_data, testname, monkeypatch):
    """Diff two fileinfo lists having equal content.
    """
    monkeypatch.chdir(test_data)
    with Archive().open(Path("archive.tar")) as archive:
        manifest_ref = archive.manifest
    base_dir = Path("base")
    fileinfos = get_fileinfos(base_dir)
    diff = list(filter(non_match, diff_manifest(fileinfos, manifest_ref)))
    assert diff == []

def test_diff_manifest_metadata(test_data, testname, monkeypatch):
    """Diff two fileinfo lists having one file's metadata modified.
    """
    monkeypatch.chdir(test_data)
    with Archive().open(Path("archive.tar")) as archive:
        manifest_ref = archive.manifest
    base_dir = Path("base")
    p = base_dir / "rnd.dat"
    p.chmod(0o0444)
    fileinfos = get_fileinfos(base_dir)
    diff = list(filter(non_match, diff_manifest(fileinfos, manifest_ref)))
    assert len(diff) == 1
    status, fi_a, fi_b = diff[0]
    assert status == DiffStatus.META
    assert fi_a.type == fi_b.type == 'f'
    assert fi_a.path == fi_b.path == p

def test_diff_manifest_modified_file(test_data, testname, monkeypatch):
    """Diff two fileinfo lists having one file's content modified.
    """
    monkeypatch.chdir(test_data)
    with Archive().open(Path("archive.tar")) as archive:
        manifest_ref = archive.manifest
    base_dir = Path("base")
    mtime_base = os.stat(base_dir).st_mtime
    p = base_dir / "rnd.dat"
    shutil.copy(gettestdata("rnd2.dat"), p)
    os.utime(base_dir, times=(mtime_base, mtime_base))
    fileinfos = get_fileinfos(base_dir)
    diff = list(filter(non_match, diff_manifest(fileinfos, manifest_ref)))
    assert len(diff) == 1
    status, fi_a, fi_b = diff[0]
    assert status == DiffStatus.CONTENT
    assert fi_a.type == fi_b.type == 'f'
    assert fi_a.path == fi_b.path == p

def test_diff_manifest_symlink_target(test_data, testname, monkeypatch):
    """Diff two fileinfo lists having one symlink's target modified.
    """
    monkeypatch.chdir(test_data)
    with Archive().open(Path("archive.tar")) as archive:
        manifest_ref = archive.manifest
    base_dir = Path("base")
    mtime_base = os.stat(base_dir).st_mtime
    p = base_dir / "s.dat"
    p.unlink()
    p.symlink_to(Path("msg.txt"))
    os.utime(base_dir, times=(mtime_base, mtime_base))
    fileinfos = get_fileinfos(base_dir)
    diff = list(filter(non_match, diff_manifest(fileinfos, manifest_ref)))
    assert len(diff) == 1
    status, fi_a, fi_b = diff[0]
    assert status == DiffStatus.SYMLNK_TARGET
    assert fi_a.type == fi_b.type == 'l'
    assert fi_a.path == fi_b.path == p

def test_diff_manifest_wrong_type(test_data, testname, monkeypatch):
    """Diff two fileinfo lists with one entry having a wrong type.
    """
    monkeypatch.chdir(test_data)
    with Archive().open(Path("archive.tar")) as archive:
        manifest_ref = archive.manifest
    base_dir = Path("base")
    mtime_base = os.stat(base_dir).st_mtime
    p = base_dir / "rnd.dat"
    p.unlink()
    p.symlink_to(Path("data", "rnd.dat"))
    os.utime(base_dir, times=(mtime_base, mtime_base))
    fileinfos = get_fileinfos(base_dir)
    diff = list(filter(non_match, diff_manifest(fileinfos, manifest_ref)))
    assert len(diff) == 1
    status, fi_a, fi_b = diff[0]
    assert status == DiffStatus.TYPE
    assert fi_a.type == 'l'
    assert fi_b.type == 'f'
    assert fi_a.path == fi_b.path == p

def test_diff_manifest_missing_files(test_data, testname, monkeypatch):
    """Diff two fileinfo lists having one file's name changed.
    """
    monkeypatch.chdir(test_data)
    with Archive().open(Path("archive.tar")) as archive:
        manifest_ref = archive.manifest
    base_dir = Path("base")
    mtime_base = os.stat(base_dir).st_mtime
    p1 = base_dir / "rnd.dat"
    p2 = base_dir / "a.dat"
    p1.rename(p2)
    os.utime(base_dir, times=(mtime_base, mtime_base))
    fileinfos = get_fileinfos(base_dir)
    diff = list(filter(non_match, diff_manifest(fileinfos, manifest_ref)))
    assert len(diff) == 2
    status, fi_a, fi_b = diff[0]
    assert status == DiffStatus.MISSING_B
    assert fi_a.type == 'f'
    assert fi_a.path == p2
    assert fi_b is None
    status, fi_a, fi_b = diff[1]
    assert status == DiffStatus.MISSING_A
    assert fi_b.type == 'f'
    assert fi_b.path == p1
    assert fi_a is None

def test_diff_manifest_mult(test_data, testname, monkeypatch):
    """Diff two fileinfo lists having multiple differences.
    """
    monkeypatch.chdir(test_data)
    with Archive().open(Path("archive.tar")) as archive:
        manifest_ref = archive.manifest
    base_dir = Path("base")
    mtime_base = os.stat(base_dir).st_mtime
    mtime_data = os.stat(base_dir / "data").st_mtime
    pm = base_dir / "data" / "rnd.dat"
    shutil.copy(gettestdata("rnd2.dat"), pm)
    p1 = base_dir / "msg.txt"
    p2 = base_dir / "o.txt"
    p1.rename(p2)
    os.utime(base_dir, times=(mtime_base, mtime_base))
    os.utime(base_dir / "data", times=(mtime_data, mtime_data))
    fileinfos = get_fileinfos(base_dir)
    diff = list(filter(non_match, diff_manifest(fileinfos, manifest_ref)))
    assert len(diff) == 3
    status, fi_a, fi_b = diff[0]
    assert status == DiffStatus.CONTENT
    assert fi_a.type == fi_b.type == 'f'
    assert fi_a.path == fi_b.path == pm
    status, fi_a, fi_b = diff[1]
    assert status == DiffStatus.MISSING_A
    assert fi_b.type == 'f'
    assert fi_b.path == p1
    assert fi_a is None
    status, fi_a, fi_b = diff[2]
    assert status == DiffStatus.MISSING_B
    assert fi_a.type == 'f'
    assert fi_a.path == p2
    assert fi_b is None

def test_diff_manifest_dircontent(test_data, testname, monkeypatch):
    """Diff two fileinfo lists with one subdirectory missing.
    """
    monkeypatch.chdir(test_data)
    with Archive().open(Path("archive.tar")) as archive:
        manifest_ref = archive.manifest
    base_dir = Path("base")
    mtime_base = os.stat(base_dir).st_mtime
    pd = base_dir / "data"
    shutil.rmtree(pd)
    os.utime(base_dir, times=(mtime_base, mtime_base))
    fileinfos = get_fileinfos(base_dir)
    diff = list(filter(non_match, diff_manifest(fileinfos, manifest_ref)))
    assert len(diff) == 2
    status, fi_a, fi_b = diff[0]
    assert status == DiffStatus.MISSING_A
    assert fi_b.type == 'd'
    assert fi_b.path == pd
    assert fi_a is None
    status, fi_a, fi_b = diff[1]
    assert status == DiffStatus.MISSING_A
    assert fi_b.type == 'f'
    assert fi_b.path == pd / "rnd.dat"
    assert fi_a is None

def test_diff_manifest_add_file_last(test_data, testname, monkeypatch):
    """Diff two fileinfo lists, one having an additional file as last item.

    The implementation of the corresponding command line tool used to
    have a flaw in this particular case, ref. #55.
    """
    monkeypatch.chdir(test_data)
    with Archive().open(Path("archive.tar")) as archive:
        manifest_ref = archive.manifest
    base_dir = Path("base")
    mtime_base = os.stat(base_dir).st_mtime
    p = base_dir / "zzz.dat"
    shutil.copy(gettestdata("rnd2.dat"), p)
    os.utime(base_dir, times=(mtime_base, mtime_base))
    fileinfos = get_fileinfos(base_dir)
    diff = list(filter(non_match, diff_manifest(fileinfos, manifest_ref)))
    assert len(diff) == 1
    status, fi_a, fi_b = diff[0]
    assert status == DiffStatus.MISSING_B
    assert fi_a.type == 'f'
    assert fi_a.path == p
    assert fi_b is None
    diff = list(filter(non_match, diff_manifest(manifest_ref, fileinfos)))
    assert len(diff) == 1
    status, fi_a, fi_b = diff[0]
    assert status == DiffStatus.MISSING_A
    assert fi_b.type == 'f'
    assert fi_b.path == p
    assert fi_a is None
