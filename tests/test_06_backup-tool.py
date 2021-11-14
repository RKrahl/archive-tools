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
from archive.index import IndexItem, ArchiveIndex
from archive.bt import backup_tool
import pytest
from _pytest.monkeypatch import MonkeyPatch
from conftest import *


class BTTestEnv:
    """Helper class to manage the environment to test backup-tool.
    """

    def __init__(self, root):
        self.root = root
        self.root.mkdir()
        self.monkeypatch = MonkeyPatch()
        self._datetime = FrozenDateTime
        self._date = FrozenDate
        self._gethostname = MockFunction()
        pwt = ('jdoe', '*', 1000, 1000, 'John Doe', '/home/jdoe', '/bin/bash')
        self._getpwnam = MockFunction(pwd.struct_passwd(pwt))
        self.test_data = dict()
        self.test_data_tags = dict()
        self.index = ArchiveIndex()
        self.backupdir = None
        self.tmptarget = None

    def config(self, backupdir, tmptarget):
        self.backupdir = self.root / backupdir
        self.tmptarget = self.root / tmptarget

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

    def add_test_data(self, tags, items):
        for i in items:
            self.test_data[i.path] = i
            for t in tags:
                for s in ('full', 'cumu', 'incr'):
                    k = (t,s)
                    self.test_data_tags.setdefault(k, set())
                    self.test_data_tags[k].add(i.path)

    def flush_test_data(self, tags, schedule):
        if schedule == 'cumu':
            schedules = ('cumu', 'incr')
        else:
            schedules = ('incr',)
        for t in tags:
            for s in schedules:
                self.test_data_tags[t,s] = set()

    def setup_test_data(self):
        setup_testdata(self.root, self.test_data.values())

    def move_archive(self, name):
        (self.tmptarget / name).rename(self.backupdir / name)

    def check_archive(self, name, tag, schedule):
        path = self.backupdir / name
        items = [ self.test_data[p] for p in self.test_data_tags[tag,schedule] ]
        with Archive().open(path) as archive:
            check_manifest(archive.manifest, items, prefix_dir=self.root)

    def check_index(self):
        idx_file = self.backupdir / ".index.yaml"
        backupdir_content = { idx_file }
        with idx_file.open("rb") as f:
            idx = ArchiveIndex(f)
        assert len(idx) == len(self.index)
        for i1, i0 in zip(idx, self.index):
            assert i1.as_dict() == i0.as_dict()
            backupdir_content.add(i0.path)
        assert set(self.backupdir.iterdir()) == backupdir_content
        assert set(self.tmptarget.iterdir()) == set()

    def add_index(self, name, host, schedule, policy=None, user=None):
        if user:
            policy = 'user'
        idx_data = {
            'date': datetime.datetime.now().isoformat(sep=' '),
            'path': self.backupdir / name,
            'host': host,
            'policy': policy,
            'user': user,
            'schedule': schedule,
        }
        self.index.append(IndexItem(idx_data))

    def run_backup_tool(self, argv):
        self.monkeypatch.setattr(sys, "argv", argv.split())
        with pytest.raises(SystemExit) as excinfo:
            backup_tool()
        assert excinfo.value.code == 0

@pytest.fixture(scope="class")
def env(tmpdir, request):
    with BTTestEnv(tmpdir / request.cls.__name__) as e:
        yield e

class TestBackupTool:
    """Test scenario: consider a directory having the following structure::

      testdir
       +-- etc
       +-- home
       |    +-- jdoe
       +-- net
       |    +-- backup
       +-- root
       +-- usr
       |    +-- local
       +-- var
            +-- backup

    Backups are created at different points in time and different
    policies, see the cfg file for details:

    + host=desk, policy=sys
      schedule: monthly full, weekly incr

    + host=serv, policy=sys
      schedule: monthly full, weekly incr

    + host=serv, policy=user, user=jdoe
      schedule: monthly full, weekly cumu, daily incr

    Tests:

    + test_initial_full_backup: full backup of initial test data.
      2021-10-03: host=desk, policy=sys, schedule=full
      2021-10-04: host=serv, policy=sys, schedule=full
      2021-10-04: host=serv, policy=user, user=jdoe, schedule=full

    + test_simple_incr_backup: add a few files, both in sys and in
      user directories.  According to schedule, only incremental user
      backup will be made.
      2021-10-06: host=serv, policy=user, user=jdoe, schedule=incr

    + test_noop_incr_backup: add only files in directories that being
      excluded.  Since there is nothing to backup, no backup should be
      created at all.
      2021-10-08: -

    + test_simple_cumu_backup: add some more files, both in sys and in
      user directories.  According to schedule, a cumulative backup
      for user and incremental backups for sys are made.
      2021-10-10: host=desk, policy=sys, schedule=incr
      2021-10-11: host=serv, policy=sys, schedule=incr
      2021-10-11: host=serv, policy=user, user=jdoe, schedule=cumu

    + test_incr_backup: add another files in a user directory.
      2021-10-13: host=serv, policy=user, user=jdoe, schedule=incr

    + test_del_incr_backup: delete the file created for the last test
      again.  Only the parent directory will be added to the
      incremental backup for it has a changed file modification time,
      but not its content.
      2021-10-15: host=serv, policy=user, user=jdoe, schedule=incr

    + test_cumu_backup: nothing has changed in sys directories, no
      backups will be created for sys.  The cumulative backup for user
      will essentially have the same content as the last one.
      2021-10-17: -
      2021-10-18: -
      2021-10-18: host=serv, policy=user, user=jdoe, schedule=cumu

    + test_full_backup: the next regular full backup.
      2021-11-07: host=desk, policy=sys, schedule=full
      2021-11-08: host=serv, policy=sys, schedule=full
      2021-11-08: host=serv, policy=user, user=jdoe, schedule=full

    """

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

    def init_data(self, env):
        env.config("net/backup", "var/backup")
        subst = dict(root=env.root)
        cfg_data = string.Template(self.cfg).substitute(subst).encode('ascii')
        cfg_path = Path("etc", "backup.cfg")
        sys_data = [
            DataDir(Path("etc"), 0o755, mtime=1633129414),
            DataContentFile(cfg_path, cfg_data, 0o644, mtime=1632596683),
            DataContentFile(Path("etc", "foo.cfg"),
                            b"[foo]\nbar = baz\n", 0o644, mtime=1632672000),
            DataDir(Path("root"), 0o700, mtime=1633274230),
            DataRandomFile(Path("root", "rnd5.dat"),
                           0o600, size=85, mtime=1633243020),
            DataSymLink(Path("root", "rnd.dat"), Path("rnd5.dat"),
                        mtime=1633243020),
        ]
        env.add_test_data(('desk','serv'), sys_data)
        sys_serv_data = [
            DataDir(Path("usr", "local"), 0o755, mtime=1616490893),
            DataRandomFile(Path("usr", "local", "rnd6.dat"),
                           0o644, size=607, mtime=1633275272),
        ]
        env.add_test_data(('serv',), sys_serv_data)
        user_data = [
            DataDir(Path("home", "jdoe"), 0o700, mtime=1633263300),
            DataRandomFile(Path("home", "jdoe", "rnd3.dat"),
                           0o600, size=796, mtime=1633243020),
        ]
        env.add_test_data(('user',), user_data)
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
        env.add_test_data(('excl',), excl_data)
        env.setup_test_data()
        env.monkeypatch.setenv("BACKUP_CFG", str(env.root / cfg_path))

    def test_initial_full_backup(self, env):
        self.init_data(env)

        env.set_hostname("desk")
        env.set_datetime(datetime.datetime(2021, 10, 3, 19, 30))
        env.run_backup_tool("backup-tool --verbose create --policy sys")
        archive_name = "desk-211003-full.tar.bz2"
        env.move_archive(archive_name)
        env.check_archive(archive_name, 'desk', 'full')
        env.add_index(archive_name, 'desk', 'full', policy='sys')

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 10, 4, 3, 0))
        env.run_backup_tool("backup-tool --verbose create --policy sys")
        archive_name = "serv-211004-full.tar.bz2"
        env.check_archive(archive_name, 'serv', 'full')
        env.add_index(archive_name, 'serv', 'full', policy='sys')
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-211004-full.tar.bz2"
        env.check_archive(archive_name, 'user', 'full')
        env.add_index(archive_name, 'serv', 'full', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('desk', 'serv', 'user'), 'cumu')
