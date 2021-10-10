"""Test the backup-tool.
"""

import datetime
import itertools
import os
from pathlib import Path
import pwd
import socket
import string
import sys
from archive import Archive
from archive.bt import backup_tool
import pytest
from _pytest.monkeypatch import MonkeyPatch
from conftest import *


class BTTestEnv:
    """Helper class to manage the environment to test backup-tool.
    """

    def __init__(self, root):
        self.root = root
        self.monkeypatch = MonkeyPatch()
        self._datetime = FrozenDateTime
        self._date = FrozenDate
        self._gethostname = MockFunction()
        pwt = ('jdoe', '*', 1000, 1000, 'John Doe', '/home/jdoe', '/bin/bash')
        self._getpwnam = MockFunction(pwd.struct_passwd(pwt))

    def __enter__(self):
        self.monkeypatch.setattr(datetime, "datetime", self._datetime)
        self.monkeypatch.setattr(datetime, "date", self._date)
        self.monkeypatch.setattr(socket, "gethostname", self._gethostname)
        self.monkeypatch.setattr(pwd, "getpwnam", self._getpwnam)
        return self

    def __exit__(self, type, value, tb):
        self.monkeypatch.undo()

    def set_datetime(self, dt):
        self._datetime.freeze(dt)

    def set_hostname(self, name):
        self._gethostname.set_return_value(name)

    def run_backup_tool(self, argv):
        self.monkeypatch.setattr(sys, "argv", argv.split())
        with pytest.raises(SystemExit) as excinfo:
            backup_tool()
        assert excinfo.value.code == 0

@pytest.fixture(scope="module")
def env(tmpdir):
    with BTTestEnv(tmpdir) as e:
        yield e

cfg = """# Configuration file for backup-tool.
# All paths are within a root directory that need to be substituted.

[DEFAULT]
backupdir = $root/net/backup

[serv]

[desk]
targetdir = $root/var/backup

[sys]
dirs =
    $root/etc
    $root/root
excludes =
    $root/root/.cache
schedules = full/incr

[desk/sys]
schedule.full.date = Sun *-*-1..7
schedule.incr.date = Sun *

[serv/sys]
dirs =
    $root/etc
    $root/root
    $root/usr/local
excludes =
    $root/root/.cache
schedule.full.date = Mon *-*-2..8
schedule.incr.date = Mon *

[user]
name = %(user)s-%(date)s-%(schedule)s.tar.bz2
dirs = $root/%(home)s
excludes =
    $root/%(home)s/.cache
    $root/%(home)s/.thumbnails
    $root/%(home)s/tmp
schedules = full/cumu/incr
schedule.full.date = Mon *-*-2..8
schedule.cumu.date = Mon *
schedule.incr.date = *
"""

sys_data = [
    DataDir(Path("etc"), 0o755, mtime=1633129414),
    DataContentFile(Path("etc", "foo.cfg"),
                    b"[foo]\nbar = baz\n", 0o644, mtime=1632672000),
    DataDir(Path("root"), 0o700, mtime=1633274230),
    DataRandomFile(Path("root", "rnd5.dat"),
                   0o600, size=85, mtime=1633243020),
    DataSymLink(Path("root", "rnd.dat"), Path("rnd5.dat"),
                mtime=1633243020),
]

sys_serv_data = [
    DataDir(Path("usr", "local"), 0o755, mtime=1616490893),
    DataRandomFile(Path("usr", "local", "rnd6.dat"),
                   0o644, size=607, mtime=1633275272),
]

user_data = [
    DataDir(Path("home", "jdoe"), 0o700, mtime=1633263300),
    DataRandomFile(Path("home", "jdoe", "rnd3.dat"),
                   0o600, size=796, mtime=1633243020),
]

excl_data = [
    DataDir(Path("home", "jdoe", ".cache"), 0o700, mtime=1608491257),
    DataRandomFile(Path("home", "jdoe", ".cache", "rnd2.dat"),
                   0o600, size=385, mtime=1633275272),
    DataDir(Path("home", "jdoe", "tmp"), 0o755, mtime=1631130997),
    DataDir(Path("root", ".cache"), 0o700, mtime=1603009887),
    DataRandomFile(Path("root", ".cache", "rnd4.dat"),
                   0o600, size=665, mtime=1633275272),
    DataDir(Path("net", "backup"), 0o755, mtime=1632704400),
    DataDir(Path("var", "backup"), 0o755, mtime=1632704400),
]

def test_backup(env):
    subst = dict(root=env.root)
    cfg_data = string.Template(cfg).substitute(subst).encode('ascii')
    cfg_path = Path("etc", "backup.cfg")
    cfg_file = DataContentFile(cfg_path, cfg_data, 0o644, mtime=1632596683)
    sys_data.append(cfg_file)
    all_data = itertools.chain(sys_data, sys_serv_data, user_data, excl_data)
    setup_testdata(env.root, all_data)

    env.monkeypatch.setenv("BACKUP_CFG", str(env.root / cfg_path))

    sys_desk_full = { d.path:d for d in sys_data }
    sys_serv_full = { d.path:d for d in sys_data + sys_serv_data }
    user_full = { d.path:d for d in user_data }

    env.set_hostname("desk")
    env.set_datetime(datetime.datetime(2021, 10, 3, 19, 30))
    env.run_backup_tool("backup-tool --verbose create --policy sys")
    path = env.root / "var" / "backup" / "desk-211003-full.tar.bz2"
    with Archive().open(path) as archive:
        check_manifest(archive.manifest, sys_desk_full.values(),
                       prefix_dir=env.root)
    path.rename(env.root / "net" / "backup" / "desk-211003-full.tar.bz2")

    env.set_hostname("serv")
    env.set_datetime(datetime.datetime(2021, 10, 4, 3, 0))
    env.run_backup_tool("backup-tool --verbose create --policy sys")
    path = env.root / "net" / "backup" / "serv-211004-full.tar.bz2"
    with Archive().open(path) as archive:
        check_manifest(archive.manifest, sys_serv_full.values(),
                       prefix_dir=env.root)
    env.run_backup_tool("backup-tool --verbose create --user jdoe")
    path = env.root / "net" / "backup" / "jdoe-211004-full.tar.bz2"
    with Archive().open(path) as archive:
        check_manifest(archive.manifest, user_full.values(),
                       prefix_dir=env.root)
    env.run_backup_tool("backup-tool --verbose index")

    sys_desk_cumu = {}
    sys_serv_cumu = {}
    user_cumu = {}
    sys_desk_incr = {}
    sys_serv_incr = {}
    user_incr = {}
