"""Test error conditions during verifying an archive.
"""

import os
from pathlib import Path
import shutil
import stat
import tarfile
import tempfile
import time
import pytest
from archive import Archive
from archive.exception import ArchiveIntegrityError
from archive.manifest import Manifest
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

@pytest.fixture(scope="function")
def test_data(tmpdir, monkeypatch):
    monkeypatch.chdir(tmpdir)
    shutil.rmtree("base", ignore_errors=True)
    setup_testdata(tmpdir, testdata)
    manifest = Manifest(paths=[Path("base")])
    manifest.add_metadata(Path("base", ".manifest.yaml"))
    with open("manifest.yaml", "wb") as f:
        manifest.write(f)
    return tmpdir

def create_archive(archive_path):
    with tarfile.open(archive_path, "w") as tarf:
        with open("manifest.yaml", "rb") as f:
            manifest_info = tarf.gettarinfo(arcname="base/.manifest.yaml", 
                                            fileobj=f)
            manifest_info.mode = stat.S_IFREG | 0o444
            tarf.addfile(manifest_info, f)
        tarf.add("base")

def test_verify_missing_manifest(test_data, testname):
    name = archive_name(tags=[testname])
    with tarfile.open(name, "w") as tarf:
        tarf.add("base")
    with pytest.raises(ArchiveIntegrityError) as err:
        with Archive().open(Path(name)) as archive:
            pass
    assert "metadata item '.manifest.yaml' not found" in str(err.value)

def test_verify_missing_metadata_item(test_data, testname):
    name = archive_name(tags=[testname])
    manifest = Manifest(paths=[Path("base")])
    manifest.add_metadata(Path("base", ".manifest.yaml"))
    manifest.add_metadata(Path("base", ".msg.txt"))
    with tarfile.open(name, "w") as tarf:
        with tempfile.TemporaryFile(dir=test_data) as tmpf:
            manifest.write(tmpf)
            tmpf.seek(0)
            ti = tarf.gettarinfo(arcname="base/.manifest.yaml", 
                                 fileobj=tmpf)
            ti.mode = stat.S_IFREG | stat.S_IMODE(0o444)
            tarf.addfile(ti, tmpf)
        tarf.add("base")
    with Archive().open(Path(name)) as archive:
        with pytest.raises(ArchiveIntegrityError) as err:
            archive.verify()
        assert "metadata item 'base/.msg.txt' not found" in str(err.value)

def test_verify_missing_file(test_data, testname):
    name = archive_name(tags=[testname])
    path = Path("base", "msg.txt")
    mtime_parent = os.stat(path.parent).st_mtime
    path.unlink()
    os.utime(path.parent, times=(mtime_parent, mtime_parent))
    create_archive(name)
    with Archive().open(Path(name)) as archive:
        with pytest.raises(ArchiveIntegrityError) as err:
            archive.verify()
        assert "%s: missing" % path in str(err.value)

def test_verify_wrong_mode_file(test_data, testname):
    name = archive_name(tags=[testname])
    path = Path("base", "data", "rnd.dat")
    path.chmod(0o644)
    create_archive(name)
    with Archive().open(Path(name)) as archive:
        with pytest.raises(ArchiveIntegrityError) as err:
            archive.verify()
        assert "%s: wrong mode" % path in str(err.value)

def test_verify_wrong_mode_dir(test_data, testname):
    name = archive_name(tags=[testname])
    path = Path("base", "data")
    path.chmod(0o755)
    create_archive(name)
    with Archive().open(Path(name)) as archive:
        with pytest.raises(ArchiveIntegrityError) as err:
            archive.verify()
        assert "%s: wrong mode" % path in str(err.value)

def test_verify_wrong_mtime(test_data, testname):
    name = archive_name(tags=[testname])
    path = Path("base", "msg.txt")
    hour_ago = time.time() - 3600
    os.utime(path, times=(hour_ago, hour_ago))
    create_archive(name)
    with Archive().open(Path(name)) as archive:
        with pytest.raises(ArchiveIntegrityError) as err:
            archive.verify()
        assert "%s: wrong modification time" % path in str(err.value)

def test_verify_wrong_type(test_data, testname):
    name = archive_name(tags=[testname])
    path = Path("base", "msg.txt")
    mode = os.stat(path).st_mode
    mtime = os.stat(path).st_mtime
    mtime_parent = os.stat(path.parent).st_mtime
    path.unlink()
    path.mkdir()
    path.chmod(mode)
    os.utime(path, times=(mtime, mtime))
    os.utime(path.parent, times=(mtime_parent, mtime_parent))
    create_archive(name)
    with Archive().open(Path(name)) as archive:
        with pytest.raises(ArchiveIntegrityError) as err:
            archive.verify()
        assert "%s: wrong type" % path in str(err.value)

def test_verify_wrong_checksum(test_data, testname):
    name = archive_name(tags=[testname])
    path = Path("base", "data", "rnd.dat")
    stat = os.stat(path)
    mode = stat.st_mode
    mtime = stat.st_mtime
    size = stat.st_size
    with path.open("wb") as f:
        f.write(b'0' * size)
    path.chmod(mode)
    os.utime(path, times=(mtime, mtime))
    create_archive(name)
    with Archive().open(Path(name)) as archive:
        with pytest.raises(ArchiveIntegrityError) as err:
            archive.verify()
        assert "%s: checksum" % path in str(err.value)

def test_verify_ok(test_data, testname):
    name = archive_name(tags=[testname])
    create_archive(name)
    with Archive().open(Path(name)) as archive:
        archive.verify()
