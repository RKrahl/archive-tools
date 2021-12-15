"""Test the backup-tool.
"""

import datetime
import itertools
import os
from pathlib import Path
import pwd
import shutil
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
        self.schedules = None

    def config(self, backupdir, tmptarget, schedules=('full', 'cumu', 'incr')):
        self.backupdir = self.root / backupdir
        self.tmptarget = self.root / tmptarget
        self.schedules = schedules

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
                for s in self.schedules:
                    k = (t,s)
                    self.test_data_tags.setdefault(k, set())
                    self.test_data_tags[k].add(i.path)

    def remove_test_data(self, tags, items):
        for i in items:
            del self.test_data[i.path]
            for t in tags:
                for s in self.schedules:
                    k = (t,s)
                    self.test_data_tags.setdefault(k, set())
                    self.test_data_tags[k].discard(i.path)

    def flush_test_data(self, tags, schedule):
        idx = self.schedules.index(schedule)
        for t in tags:
            for s in self.schedules[idx:]:
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

    def add_index(self, name, host, schedule,
                  type=None, policy=None, user=None):
        if user:
            policy = 'user'
        idx_data = {
            'date': datetime.datetime.now().isoformat(sep=' '),
            'path': self.backupdir / name,
            'host': host,
            'policy': policy,
            'user': user,
            'schedule': schedule,
            'type': type or schedule,
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

    + test_initial_full: full backup of initial test data.
      2021-10-03: host=desk, policy=sys, schedule=full
      2021-10-04: host=serv, policy=sys, schedule=full
      2021-10-04: host=serv, policy=user, user=jdoe, schedule=full

    + test_simple_incr: add a few files, both in sys and in
      user directories.  According to schedule, only incremental user
      backup will be made.
      2021-10-06: host=serv, policy=user, user=jdoe, schedule=incr

    + test_noop_incr: add only files in directories that being
      excluded.  Since there is nothing to backup, no backup should be
      created at all.
      2021-10-07: -

    + test_content_incr: modify a file's content, but make sure
      all filesystem metadata remain unchanged.
      2021-10-08: host=serv, policy=user, user=jdoe, schedule=incr

    + test_meta_incr: modify a file's metadata, but keep the
      content unchanged.
      2021-10-09: host=serv, policy=user, user=jdoe, schedule=incr

    + test_simple_cumu: add some more files, both in sys and in
      user directories.  According to schedule, a cumulative backup
      for user and incremental backups for sys are made.
      2021-10-10: host=desk, policy=sys, schedule=incr
      2021-10-11: host=serv, policy=sys, schedule=incr
      2021-10-11: host=serv, policy=user, user=jdoe, schedule=cumu

    + test_incr: add another files in a user directory.
      2021-10-13: host=serv, policy=user, user=jdoe, schedule=incr

    + test_del_incr: delete the file created for the last test
      again.  Only the parent directory will be added to the
      incremental backup for it has a changed file modification time,
      but not its content.
      2021-10-15: host=serv, policy=user, user=jdoe, schedule=incr

    + test_cumu: nothing has changed in sys directories, no
      backups will be created for sys.  The cumulative backup for user
      will essentially have the same content as the last one.
      2021-10-17: -
      2021-10-18: -
      2021-10-18: host=serv, policy=user, user=jdoe, schedule=cumu

    + test_full: the next regular full backup.
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
            DataRandomFile(Path("home", "jdoe", "rnd.dat"),
                           0o600, size=7964, mtime=1626052455),
            DataFile(Path("home", "jdoe", "rnd2.dat"), 0o640, mtime=1633050855),
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

    @pytest.mark.dependency()
    def test_initial_full(self, env):
        """Full backup of initial test data.
        """
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
        env.set_datetime(datetime.datetime(2021, 10, 4, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-211004-full.tar.bz2"
        env.check_archive(archive_name, 'user', 'full')
        env.add_index(archive_name, 'serv', 'full', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('desk', 'serv', 'user'), 'cumu')

    @pytest.mark.dependency(depends=["test_initial_full"], scope='class')
    def test_simple_incr(self, env):
        """Add a few files, both in sys and in user directories.
        According to schedule, only incremental user backup will be
        made.
        """
        mtime = 1633451717
        u_path = Path("home", "jdoe", "misc")
        u_dir = DataDir(u_path, 0o755, mtime=mtime)
        u_file = DataRandomFile(u_path / "rnd7.dat",
                                0o644, size=473, mtime=mtime)
        u_parent = env.test_data[u_path.parent]
        u_parent.mtime = mtime
        mtime = 1633464305
        s_path = Path("root", "rnd8.dat")
        s_file = DataRandomFile(s_path, 0o600, size=42, mtime=mtime)
        s_parent = env.test_data[s_path.parent]
        s_parent.mtime = mtime
        env.add_test_data(('user',), [u_parent, u_dir, u_file])
        env.add_test_data(('desk','serv'), [s_parent, s_file])
        setup_testdata(env.root, [u_dir, u_file, s_file])

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 10, 6, 3, 0))
        env.run_backup_tool("backup-tool --verbose create --policy sys")
        env.set_datetime(datetime.datetime(2021, 10, 6, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-211006-incr.tar.bz2"
        env.check_archive(archive_name, 'user', 'incr')
        env.add_index(archive_name, 'serv', 'incr', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('user',), 'incr')

    @pytest.mark.dependency(depends=["test_simple_incr"], scope='class')
    def test_noop_incr(self, env):
        """Add only files in directories that being excluded.
        Since there is nothing to backup, no backup should be created at all.
        """
        mtime = 1633487220
        s_path = Path("root", ".cache", "rnd10.dat")
        s_file = DataRandomFile(s_path, 0o600, size=27, mtime=mtime)
        s_parent = env.test_data[s_path.parent]
        s_parent.mtime = mtime
        mtime = 1633500600
        u_path = Path("home", "jdoe", "tmp", "rnd9.dat")
        u_file = DataRandomFile(u_path, 0o640, size=582, mtime=mtime)
        u_parent = env.test_data[u_path.parent]
        u_parent.mtime = mtime
        env.add_test_data(('excl',), [s_parent, s_file, u_parent, u_file])
        setup_testdata(env.root, [s_file, u_file])

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 10, 7, 3, 0))
        env.run_backup_tool("backup-tool --verbose create --policy sys")
        env.set_datetime(datetime.datetime(2021, 10, 7, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('user',), 'incr')

    @pytest.mark.dependency(depends=["test_noop_incr"], scope='class')
    def test_content_incr(self, env):
        """Modify a file's content, but make sure all filesystem metadata
        remain unchanged.
        """
        u_path = Path("home", "jdoe", "rnd2.dat")
        u_orig_file = env.test_data[u_path]
        with gettestdata("rnd2bis.dat").open("rb") as f:
            u_file = DataContentFile(u_path, f.read(),
                                     mode=u_orig_file.mode,
                                     mtime=u_orig_file.mtime)
        u_parent = env.test_data[u_path.parent]
        env.add_test_data(('user',), [u_file])
        setup_testdata(env.root, [u_parent, u_file])

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 10, 8, 3, 0))
        env.run_backup_tool("backup-tool --verbose create --policy sys")
        env.set_datetime(datetime.datetime(2021, 10, 8, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-211008-incr.tar.bz2"
        env.check_archive(archive_name, 'user', 'incr')
        env.add_index(archive_name, 'serv', 'incr', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('user',), 'incr')

    @pytest.mark.dependency(depends=["test_content_incr"], scope='class')
    def test_meta_incr(self, env):
        """Modify a file's metadata, but keep the content unchanged.
        """
        u_path = Path("home", "jdoe", "rnd3.dat")
        u_file = env.test_data[u_path]
        u_parent = env.test_data[u_path.parent]
        u_file.mode = 0o644
        env.add_test_data(('user',), [u_file])
        (env.root / u_path).chmod(u_file.mode)

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 10, 9, 3, 0))
        env.run_backup_tool("backup-tool --verbose create --policy sys")
        env.set_datetime(datetime.datetime(2021, 10, 9, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-211009-incr.tar.bz2"
        env.check_archive(archive_name, 'user', 'incr')
        env.add_index(archive_name, 'serv', 'incr', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('user',), 'incr')

    @pytest.mark.dependency(depends=["test_meta_incr"], scope='class')
    def test_simple_cumu(self, env):
        """Add some more files, both in sys and in user directories.
        According to schedule, a cumulative backup for user and
        incremental backups for sys are made.
        """
        mtime = 1633837020
        s0_path = Path("usr", "local", "rnd11.dat")
        s0_file = DataRandomFile(s0_path, 0o644, size=528, mtime=mtime)
        s0_parent = env.test_data[s0_path.parent]
        s0_parent.mtime = mtime
        mtime = 1633843260
        s1_path = Path("root", "rnd12.dat")
        s1_file = DataRandomFile(s1_path, 0o600, size=17, mtime=mtime)
        s1_parent = env.test_data[s1_path.parent]
        s1_parent.mtime = mtime
        mtime = 1633876920
        u_path = Path("home", "jdoe", "misc", "rnd13.dat")
        u_file = DataRandomFile(u_path, 0o644, size=378, mtime=mtime)
        u_parent = env.test_data[u_path.parent]
        u_parent.mtime = mtime
        env.add_test_data(('serv',), [s0_parent, s0_file])
        env.add_test_data(('desk','serv'), [s1_parent, s1_file])
        env.add_test_data(('user',), [u_parent, u_file])
        setup_testdata(env.root, [s0_file, s1_file, u_file])

        env.set_hostname("desk")
        env.set_datetime(datetime.datetime(2021, 10, 10, 19, 30))
        env.run_backup_tool("backup-tool --verbose create --policy sys")
        archive_name = "desk-211010-incr.tar.bz2"
        env.move_archive(archive_name)
        env.check_archive(archive_name, 'desk', 'incr')
        env.add_index(archive_name, 'desk', 'incr', policy='sys')

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 10, 11, 3, 0))
        env.run_backup_tool("backup-tool --verbose create --policy sys")
        archive_name = "serv-211011-incr.tar.bz2"
        env.check_archive(archive_name, 'serv', 'incr')
        env.add_index(archive_name, 'serv', 'incr', policy='sys')
        env.set_datetime(datetime.datetime(2021, 10, 11, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-211011-cumu.tar.bz2"
        env.check_archive(archive_name, 'user', 'cumu')
        env.add_index(archive_name, 'serv', 'cumu', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('desk', 'serv', 'user'), 'incr')

    @pytest.mark.dependency(depends=["test_simple_cumu"], scope='class')
    def test_incr(self, env):
        """Add another files in a user directory.
        """
        mtime = 1634067525
        u_path = Path("home", "jdoe", "misc", "rnd14.dat")
        u_file = DataRandomFile(u_path, 0o644, size=146, mtime=mtime)
        u_parent = env.test_data[u_path.parent]
        u_parent.mtime = mtime
        env.add_test_data(('user',), [u_parent, u_file])
        setup_testdata(env.root, [u_file])

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 10, 13, 3, 0))
        env.run_backup_tool("backup-tool --verbose create --policy sys")
        env.set_datetime(datetime.datetime(2021, 10, 13, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-211013-incr.tar.bz2"
        env.check_archive(archive_name, 'user', 'incr')
        env.add_index(archive_name, 'serv', 'incr', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('user',), 'incr')

    @pytest.mark.dependency(depends=["test_incr"], scope='class')
    def test_del_incr(self, env):
        """Delete the file created for the last test again.
        Only the parent directory will be added to the incremental
        backup for it has a changed file modification time, but not
        its content.
        """
        mtime = 1634240325
        u_path = Path("home", "jdoe", "misc", "rnd14.dat")
        u_file = env.test_data[u_path]
        u_parent = env.test_data[u_path.parent]
        u_parent.mtime = mtime
        env.remove_test_data(('user',), [u_file])
        env.add_test_data(('user',), [u_parent])
        u_file.unlink(env.root, mtime)

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 10, 15, 3, 0))
        env.run_backup_tool("backup-tool --verbose create --policy sys")
        env.set_datetime(datetime.datetime(2021, 10, 15, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-211015-incr.tar.bz2"
        env.check_archive(archive_name, 'user', 'incr')
        env.add_index(archive_name, 'serv', 'incr', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('user',), 'incr')

    @pytest.mark.dependency(depends=["test_del_incr"], scope='class')
    def test_cumu(self, env):
        """Do the next weekly backup.
        Nothing has changed in sys directories, no backups will be
        created for sys.  The cumulative backup for user will
        essentially have the same content as the last one.
        """
        env.set_hostname("desk")
        env.set_datetime(datetime.datetime(2021, 10, 17, 19, 30))
        env.run_backup_tool("backup-tool --verbose create --policy sys")

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 10, 18, 3, 0))
        env.run_backup_tool("backup-tool --verbose create --policy sys")
        env.set_datetime(datetime.datetime(2021, 10, 18, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-211018-cumu.tar.bz2"
        env.check_archive(archive_name, 'user', 'cumu')
        env.add_index(archive_name, 'serv', 'cumu', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('desk', 'serv', 'user'), 'incr')

    @pytest.mark.dependency(depends=["test_cumu"], scope='class')
    def test_full(self, env):
        """Do the next monthly backup.
        """
        env.set_hostname("desk")
        env.set_datetime(datetime.datetime(2021, 11, 7, 19, 30))
        env.run_backup_tool("backup-tool --verbose create --policy sys")
        archive_name = "desk-211107-full.tar.bz2"
        env.move_archive(archive_name)
        env.check_archive(archive_name, 'desk', 'full')
        env.add_index(archive_name, 'desk', 'full', policy='sys')

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 11, 8, 3, 0))
        env.run_backup_tool("backup-tool --verbose create --policy sys")
        archive_name = "serv-211108-full.tar.bz2"
        env.check_archive(archive_name, 'serv', 'full')
        env.add_index(archive_name, 'serv', 'full', policy='sys')
        env.set_datetime(datetime.datetime(2021, 11, 8, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-211108-full.tar.bz2"
        env.check_archive(archive_name, 'user', 'full')
        env.add_index(archive_name, 'serv', 'full', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('desk', 'serv', 'user'), 'cumu')


class TestBackupToolNamedSchedule:
    """Use named schedules in the config file.

    Otherwise this is mostly a simplified version of class
    TestBackupTool.  The focus of the tests is on proper functioning
    of the schedule, full vs. cumulative vs. incremental.
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
schedules = monthly:full/weekly:incr

[desk/sys]
schedule.monthly.date = Sun *-*-1..7
schedule.weekly.date = Sun *

[serv/sys]
dirs =
    $root/etc
    $root/root
    $root/usr/local
excludes =
    $root/root/.cache
schedule.monthly.date = Mon *-*-2..8
schedule.weekly.date = Mon *

[user]
name = %(user)s-%(date)s-%(schedule)s.tar.bz2
dirs = $root/%(home)s
excludes =
    $root/%(home)s/.cache
    $root/%(home)s/.thumbnails
    $root/%(home)s/tmp
schedules = monthly:full/weekly:cumu/daily:incr
schedule.monthly.date = Mon *-*-2..8
schedule.weekly.date = Mon *
schedule.daily.date = *
"""

    def init_data(self, env):
        env.config("net/backup", "var/backup",
                   schedules=('monthly', 'weekly', 'daily'))
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
            DataDir(Path("usr", "local"), 0o755, mtime=1616490893),
            DataRandomFile(Path("usr", "local", "rnd6.dat"),
                           0o644, size=607, mtime=1633275272),
        ]
        env.add_test_data(('sys',), sys_data)
        user_data = [
            DataDir(Path("home", "jdoe"), 0o700, mtime=1633263300),
            DataRandomFile(Path("home", "jdoe", "rnd.dat"),
                           0o600, size=7964, mtime=1626052455),
            DataFile(Path("home", "jdoe", "rnd2.dat"), 0o640, mtime=1633050855),
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

    @pytest.mark.dependency()
    def test_initial_monthly(self, env):
        """Full backup of initial test data.
        """
        self.init_data(env)

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 10, 4, 3, 0))
        env.run_backup_tool("backup-tool --verbose create --policy sys")
        archive_name = "serv-211004-monthly.tar.bz2"
        env.check_archive(archive_name, 'sys', 'monthly')
        env.add_index(archive_name, 'serv', 'monthly',
                      type='full', policy='sys')
        env.set_datetime(datetime.datetime(2021, 10, 4, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-211004-monthly.tar.bz2"
        env.check_archive(archive_name, 'user', 'monthly')
        env.add_index(archive_name, 'serv', 'monthly',
                      type='full', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('sys', 'user'), 'weekly')

    @pytest.mark.dependency(depends=["test_initial_monthly"], scope='class')
    def test_first_daily(self, env):
        """First incremental backup in the first week.
        """
        mtime = 1633451717
        u_path = Path("home", "jdoe", "misc")
        u_dir = DataDir(u_path, 0o755, mtime=mtime)
        u_file = DataRandomFile(u_path / "rnd7.dat",
                                0o644, size=473, mtime=mtime)
        u_parent = env.test_data[u_path.parent]
        u_parent.mtime = mtime
        mtime = 1633464305
        s_path = Path("root", "rnd8.dat")
        s_file = DataRandomFile(s_path, 0o600, size=42, mtime=mtime)
        s_parent = env.test_data[s_path.parent]
        s_parent.mtime = mtime
        env.add_test_data(('user',), [u_parent, u_dir, u_file])
        env.add_test_data(('sys',), [s_parent, s_file])
        setup_testdata(env.root, [u_dir, u_file, s_file])

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 10, 6, 3, 0))
        env.run_backup_tool("backup-tool --verbose create --policy sys")
        env.set_datetime(datetime.datetime(2021, 10, 6, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-211006-daily.tar.bz2"
        env.check_archive(archive_name, 'user', 'daily')
        env.add_index(archive_name, 'serv', 'daily',
                      type='incr', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('user',), 'daily')

    @pytest.mark.dependency(depends=["test_first_daily"], scope='class')
    def test_second_daily(self, env):
        """Second incremental backup in the first week.
        """
        mtime = 1633500600
        u_path = Path("home", "jdoe", "misc", "rnd9.dat")
        u_file = DataRandomFile(u_path, 0o640, size=582, mtime=mtime)
        u_parent = env.test_data[u_path.parent]
        u_parent.mtime = mtime
        env.add_test_data(('user',), [u_parent, u_file])
        setup_testdata(env.root, [u_file])

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 10, 7, 3, 0))
        env.run_backup_tool("backup-tool --verbose create --policy sys")
        env.set_datetime(datetime.datetime(2021, 10, 7, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-211007-daily.tar.bz2"
        env.check_archive(archive_name, 'user', 'daily')
        env.add_index(archive_name, 'serv', 'daily',
                      type='incr', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('user',), 'daily')

    @pytest.mark.dependency(depends=["test_second_daily"], scope='class')
    def test_first_weekly(self, env):
        """First cumulative backup.
        """
        mtime = 1633837020
        s0_path = Path("usr", "local", "rnd11.dat")
        s0_file = DataRandomFile(s0_path, 0o644, size=528, mtime=mtime)
        s0_parent = env.test_data[s0_path.parent]
        s0_parent.mtime = mtime
        mtime = 1633843260
        s1_path = Path("root", "rnd12.dat")
        s1_file = DataRandomFile(s1_path, 0o600, size=17, mtime=mtime)
        s1_parent = env.test_data[s1_path.parent]
        s1_parent.mtime = mtime
        mtime = 1633876920
        u_path = Path("home", "jdoe", "misc", "rnd13.dat")
        u_file = DataRandomFile(u_path, 0o644, size=378, mtime=mtime)
        u_parent = env.test_data[u_path.parent]
        u_parent.mtime = mtime
        env.add_test_data(('sys',), [s0_parent, s0_file, s1_parent, s1_file])
        env.add_test_data(('user',), [u_parent, u_file])
        setup_testdata(env.root, [s0_file, s1_file, u_file])

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 10, 11, 3, 0))
        env.run_backup_tool("backup-tool --verbose create --policy sys")
        archive_name = "serv-211011-weekly.tar.bz2"
        env.check_archive(archive_name, 'sys', 'weekly')
        env.add_index(archive_name, 'serv', 'weekly',
                      type='incr', policy='sys')
        env.set_datetime(datetime.datetime(2021, 10, 11, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-211011-weekly.tar.bz2"
        env.check_archive(archive_name, 'user', 'weekly')
        env.add_index(archive_name, 'serv', 'weekly',
                      type='cumu', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('sys',), 'weekly')
        env.flush_test_data(('user',), 'daily')

    @pytest.mark.dependency(depends=["test_first_weekly"], scope='class')
    def test_third_daily(self, env):
        """First incremental backup in the second week.
        """
        mtime = 1634053507
        u_path = Path("home", "jdoe", "misc", "rnd14.dat")
        u_file = DataRandomFile(u_path, 0o644, size=763, mtime=mtime)
        u_parent = env.test_data[u_path.parent]
        u_parent.mtime = mtime
        mtime = 1634083500
        s_path = Path("root", "rnd15.dat")
        s_file = DataRandomFile(s_path, 0o600, size=165, mtime=mtime)
        s_parent = env.test_data[s_path.parent]
        s_parent.mtime = mtime
        env.add_test_data(('user',), [u_parent, u_file])
        env.add_test_data(('sys',), [s_parent, s_file])
        setup_testdata(env.root, [u_file, s_file])

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 10, 13, 3, 0))
        env.run_backup_tool("backup-tool --verbose create --policy sys")
        env.set_datetime(datetime.datetime(2021, 10, 13, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-211013-daily.tar.bz2"
        env.check_archive(archive_name, 'user', 'daily')
        env.add_index(archive_name, 'serv', 'daily',
                      type='incr', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('user',), 'daily')

    @pytest.mark.dependency(depends=["test_third_daily"], scope='class')
    def test_second_weekly(self, env):
        """Second cumulative backup.
        """
        mtime = 1634509129
        u_path = Path("home", "jdoe", "misc", "rnd16.dat")
        u_file = DataRandomFile(u_path, 0o644, size=834, mtime=mtime)
        u_parent = env.test_data[u_path.parent]
        u_parent.mtime = mtime
        env.add_test_data(('user',), [u_parent, u_file])
        setup_testdata(env.root, [u_file])

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 10, 18, 3, 0))
        env.run_backup_tool("backup-tool --verbose create --policy sys")
        archive_name = "serv-211018-weekly.tar.bz2"
        env.check_archive(archive_name, 'sys', 'weekly')
        env.add_index(archive_name, 'serv', 'weekly',
                      type='incr', policy='sys')
        env.set_datetime(datetime.datetime(2021, 10, 18, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-211018-weekly.tar.bz2"
        env.check_archive(archive_name, 'user', 'weekly')
        env.add_index(archive_name, 'serv', 'weekly',
                      type='cumu', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('sys',), 'weekly')
        env.flush_test_data(('user',), 'daily')

    @pytest.mark.dependency(depends=["test_second_weekly"], scope='class')
    def test_fourth_daily(self, env):
        """First incremental backup in the third week.
        """
        mtime = 1634605839
        s_path = Path("root", "rnd18.dat")
        s_file = DataRandomFile(s_path, 0o600, size=589, mtime=mtime)
        s_parent = env.test_data[s_path.parent]
        s_parent.mtime = mtime
        mtime = 1634631969
        u_path = Path("home", "jdoe", "misc", "rnd17.dat")
        u_file = DataRandomFile(u_path, 0o644, size=568, mtime=mtime)
        u_parent = env.test_data[u_path.parent]
        u_parent.mtime = mtime
        env.add_test_data(('user',), [u_parent, u_file])
        env.add_test_data(('sys',), [s_parent, s_file])
        setup_testdata(env.root, [u_file, s_file])

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 10, 20, 3, 0))
        env.run_backup_tool("backup-tool --verbose create --policy sys")
        env.set_datetime(datetime.datetime(2021, 10, 20, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-211020-daily.tar.bz2"
        env.check_archive(archive_name, 'user', 'daily')
        env.add_index(archive_name, 'serv', 'daily',
                      type='incr', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('user',), 'daily')

    @pytest.mark.dependency(depends=["test_fourth_daily"], scope='class')
    def test_second_monthly(self, env):
        """Do the next monthly backup.
        """
        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 11, 8, 3, 0))
        env.run_backup_tool("backup-tool --verbose create --policy sys")
        archive_name = "serv-211108-monthly.tar.bz2"
        env.check_archive(archive_name, 'sys', 'monthly')
        env.add_index(archive_name, 'serv', 'monthly',
                      type='full', policy='sys')
        env.set_datetime(datetime.datetime(2021, 11, 8, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-211108-monthly.tar.bz2"
        env.check_archive(archive_name, 'user', 'monthly')
        env.add_index(archive_name, 'serv', 'monthly',
                      type='full', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('sys', 'user'), 'weekly')


class TestBackupToolMixedScheduleTypes:
    """The schedule types may be freely mixed.

    The backup-tool supports a hierarchy of the schedule types 'full',
    'cumu', and 'incr'.  It is not required to use them in that order.
    Only the root of the hierarchy must have the type 'full',
    otherwise the types may be freely mixed.

    The scenario considered in this test:
    - quarterly: full,
    - monthly: incr,
    - weekly: cumu,
    - daily: incr.
    """

    cfg = """# Configuration file for backup-tool.
# All paths are within a root directory that need to be substituted.

[serv]
backupdir = $root/net/backup

[user]
name = %(user)s-%(date)s-%(schedule)s.tar.bz2
dirs = $root/%(home)s
excludes =
    $root/%(home)s/.cache
    $root/%(home)s/.thumbnails
    $root/%(home)s/tmp
schedules = quarterly:full/monthly:incr/weekly:cumu/daily:incr
schedule.quarterly.date = Mon *-1,4,7,10-2..8
schedule.monthly.date = Mon *-*-2..8
schedule.weekly.date = Mon *
schedule.daily.date = *
"""

    def init_data(self, env):
        env.config("net/backup", "var",
                   schedules=('quarterly', 'monthly', 'weekly', 'daily'))
        subst = dict(root=env.root)
        cfg_data = string.Template(self.cfg).substitute(subst).encode('ascii')
        cfg_path = Path("etc", "backup.cfg")
        sys_data = [
            DataDir(Path("etc"), 0o755, mtime=1625363657),
            DataContentFile(cfg_path, cfg_data, 0o644, mtime=1625243298),
        ]
        env.add_test_data(('sys',), sys_data)
        user_data = [
            DataDir(Path("home", "jdoe"), 0o700, mtime=1633263300),
            DataRandomFile(Path("home", "jdoe", "rnd00.dat"),
                           0o600, size=7964, mtime=1612908655),
            DataRandomFile(Path("home", "jdoe", "rnd01.dat"),
                           0o600, size=39, mtime=1614947739),
        ]
        env.add_test_data(('user',), user_data)
        excl_data = [
            DataDir(Path("net", "backup"), 0o755, mtime=1625360400),
            DataDir(Path("var"), 0o755, mtime=1625360400),
        ]
        env.add_test_data(('excl',), excl_data)
        env.setup_test_data()
        env.monkeypatch.setenv("BACKUP_CFG", str(env.root / cfg_path))

    @pytest.mark.dependency()
    def test_20210705(self, env):
        """Full backup of initial test data.
        """
        self.init_data(env)

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 7, 5, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-210705-quarterly.tar.bz2"
        env.check_archive(archive_name, 'user', 'quarterly')
        env.add_index(archive_name, 'serv', 'quarterly',
                      type='full', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('user',), 'monthly')

    @pytest.mark.dependency(depends=["test_20210705"], scope='class')
    def test_20210707(self, env):
        """Daily incremental backup in the first week.
        """
        mtime = 1625562697
        u_path = Path("home", "jdoe", "rnd02.dat")
        u_file = DataRandomFile(u_path, 0o600, size=446, mtime=mtime)
        u_parent = env.test_data[u_path.parent]
        u_parent.mtime = mtime
        env.add_test_data(('user',), [u_parent, u_file])
        setup_testdata(env.root, [u_file])

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 7, 7, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-210707-daily.tar.bz2"
        env.check_archive(archive_name, 'user', 'daily')
        env.add_index(archive_name, 'serv', 'daily',
                      type='incr', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('user',), 'daily')

    @pytest.mark.dependency(depends=["test_20210707"], scope='class')
    def test_20210709(self, env):
        """Second daily incremental backup in the first week.
        """
        mtime = 1625743947
        u_path = Path("home", "jdoe", "rnd03.dat")
        u_file = DataRandomFile(u_path, 0o600, size=55, mtime=mtime)
        u_parent = env.test_data[u_path.parent]
        u_parent.mtime = mtime
        env.add_test_data(('user',), [u_parent, u_file])
        setup_testdata(env.root, [u_file])

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 7, 9, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-210709-daily.tar.bz2"
        env.check_archive(archive_name, 'user', 'daily')
        env.add_index(archive_name, 'serv', 'daily',
                      type='incr', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('user',), 'daily')

    @pytest.mark.dependency(depends=["test_20210709"], scope='class')
    def test_20210712(self, env):
        """Weekly cumulative backup.
        """
        mtime = 1626043402
        u_path = Path("home", "jdoe", "rnd04.dat")
        u_file = DataRandomFile(u_path, 0o600, size=228, mtime=mtime)
        u_parent = env.test_data[u_path.parent]
        u_parent.mtime = mtime
        env.add_test_data(('user',), [u_parent, u_file])
        setup_testdata(env.root, [u_file])

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 7, 12, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-210712-weekly.tar.bz2"
        env.check_archive(archive_name, 'user', 'weekly')
        env.add_index(archive_name, 'serv', 'weekly',
                      type='cumu', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('user',), 'daily')

    @pytest.mark.dependency(depends=["test_20210712"], scope='class')
    def test_20210714(self, env):
        """Daily incremental backup in the second week.
        """
        mtime = 1626167376
        u_path = Path("home", "jdoe", "rnd05.dat")
        u_file = DataRandomFile(u_path, 0o600, size=263, mtime=mtime)
        u_parent = env.test_data[u_path.parent]
        u_parent.mtime = mtime
        env.add_test_data(('user',), [u_parent, u_file])
        setup_testdata(env.root, [u_file])

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 7, 14, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-210714-daily.tar.bz2"
        env.check_archive(archive_name, 'user', 'daily')
        env.add_index(archive_name, 'serv', 'daily',
                      type='incr', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('user',), 'daily')

    @pytest.mark.dependency(depends=["test_20210714"], scope='class')
    def test_20210719(self, env):
        """Weekly cumulative backup.
        """
        mtime = 1626575481
        u_path = Path("home", "jdoe", "rnd06.dat")
        u_file = DataRandomFile(u_path, 0o600, size=287, mtime=mtime)
        u_parent = env.test_data[u_path.parent]
        u_parent.mtime = mtime
        env.add_test_data(('user',), [u_parent, u_file])
        setup_testdata(env.root, [u_file])

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 7, 19, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-210719-weekly.tar.bz2"
        env.check_archive(archive_name, 'user', 'weekly')
        env.add_index(archive_name, 'serv', 'weekly',
                      type='cumu', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('user',), 'daily')

    @pytest.mark.dependency(depends=["test_20210719"], scope='class')
    def test_20210721(self, env):
        """Daily incremental backup in the third week.
        """
        mtime = 1626826403
        u_path = Path("home", "jdoe", "rnd07.dat")
        u_file = DataRandomFile(u_path, 0o600, size=318, mtime=mtime)
        u_parent = env.test_data[u_path.parent]
        u_parent.mtime = mtime
        env.add_test_data(('user',), [u_parent, u_file])
        setup_testdata(env.root, [u_file])

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 7, 21, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-210721-daily.tar.bz2"
        env.check_archive(archive_name, 'user', 'daily')
        env.add_index(archive_name, 'serv', 'daily',
                      type='incr', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('user',), 'daily')

    @pytest.mark.dependency(depends=["test_20210721"], scope='class')
    def test_20210802(self, env):
        """Monthly backup.
        """
        mtime = 1627806186
        u_path = Path("home", "jdoe", "rnd08.dat")
        u_file = DataRandomFile(u_path, 0o600, size=334, mtime=mtime)
        u_parent = env.test_data[u_path.parent]
        u_parent.mtime = mtime
        env.add_test_data(('user',), [u_parent, u_file])
        setup_testdata(env.root, [u_file])

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 8, 2, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-210802-monthly.tar.bz2"
        env.check_archive(archive_name, 'user', 'monthly')
        env.add_index(archive_name, 'serv', 'monthly',
                      type='incr', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('user',), 'monthly')

    @pytest.mark.dependency(depends=["test_20210802"], scope='class')
    def test_20210804(self, env):
        """Daily incremental backup.
        """
        mtime = 1628026098
        u_path = Path("home", "jdoe", "rnd09.dat")
        u_file = DataRandomFile(u_path, 0o600, size=404, mtime=mtime)
        u_parent = env.test_data[u_path.parent]
        u_parent.mtime = mtime
        env.add_test_data(('user',), [u_parent, u_file])
        setup_testdata(env.root, [u_file])

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 8, 4, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-210804-daily.tar.bz2"
        env.check_archive(archive_name, 'user', 'daily')
        env.add_index(archive_name, 'serv', 'daily',
                      type='incr', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('user',), 'daily')

    @pytest.mark.dependency(depends=["test_20210804"], scope='class')
    def test_20210809(self, env):
        """Weekly cumulative backup.
        """
        mtime = 1628460869
        u_path = Path("home", "jdoe", "rnd10.dat")
        u_file = DataRandomFile(u_path, 0o600, size=453, mtime=mtime)
        u_parent = env.test_data[u_path.parent]
        u_parent.mtime = mtime
        env.add_test_data(('user',), [u_parent, u_file])
        setup_testdata(env.root, [u_file])

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 8, 9, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-210809-weekly.tar.bz2"
        env.check_archive(archive_name, 'user', 'weekly')
        env.add_index(archive_name, 'serv', 'weekly',
                      type='cumu', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('user',), 'daily')

    @pytest.mark.dependency(depends=["test_20210809"], scope='class')
    def test_20210811(self, env):
        """Daily incremental backup.
        """
        mtime = 1628563138
        u_path = Path("home", "jdoe", "rnd11.dat")
        u_file = DataRandomFile(u_path, 0o600, size=174, mtime=mtime)
        u_parent = env.test_data[u_path.parent]
        u_parent.mtime = mtime
        env.add_test_data(('user',), [u_parent, u_file])
        setup_testdata(env.root, [u_file])

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 8, 11, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-210811-daily.tar.bz2"
        env.check_archive(archive_name, 'user', 'daily')
        env.add_index(archive_name, 'serv', 'daily',
                      type='incr', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('user',), 'daily')

    @pytest.mark.dependency(depends=["test_20210811"], scope='class')
    def test_20210906(self, env):
        """Monthly backup.
        """
        mtime = 1630827561
        u_path = Path("home", "jdoe", "rnd12.dat")
        u_file = DataRandomFile(u_path, 0o600, size=225, mtime=mtime)
        u_parent = env.test_data[u_path.parent]
        u_parent.mtime = mtime
        env.add_test_data(('user',), [u_parent, u_file])
        setup_testdata(env.root, [u_file])

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 9, 6, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-210906-monthly.tar.bz2"
        env.check_archive(archive_name, 'user', 'monthly')
        env.add_index(archive_name, 'serv', 'monthly',
                      type='incr', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('user',), 'monthly')

    @pytest.mark.dependency(depends=["test_20210906"], scope='class')
    def test_20210908(self, env):
        """Daily incremental backup.
        """
        mtime = 1630986960
        u_path = Path("home", "jdoe", "rnd13.dat")
        u_file = DataRandomFile(u_path, 0o600, size=317, mtime=mtime)
        u_parent = env.test_data[u_path.parent]
        u_parent.mtime = mtime
        env.add_test_data(('user',), [u_parent, u_file])
        setup_testdata(env.root, [u_file])

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 9, 8, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-210908-daily.tar.bz2"
        env.check_archive(archive_name, 'user', 'daily')
        env.add_index(archive_name, 'serv', 'daily',
                      type='incr', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('user',), 'daily')

    @pytest.mark.dependency(depends=["test_20210908"], scope='class')
    def test_20210913(self, env):
        """Weekly cumulative backup.
        """
        mtime = 1631419436
        u_path = Path("home", "jdoe", "rnd14.dat")
        u_file = DataRandomFile(u_path, 0o600, size=159, mtime=mtime)
        u_parent = env.test_data[u_path.parent]
        u_parent.mtime = mtime
        env.add_test_data(('user',), [u_parent, u_file])
        setup_testdata(env.root, [u_file])

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 9, 13, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-210913-weekly.tar.bz2"
        env.check_archive(archive_name, 'user', 'weekly')
        env.add_index(archive_name, 'serv', 'weekly',
                      type='cumu', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('user',), 'daily')

    @pytest.mark.dependency(depends=["test_20210913"], scope='class')
    def test_20210915(self, env):
        """Daily incremental backup.
        """
        mtime = 1631652957
        u_path = Path("home", "jdoe", "rnd15.dat")
        u_file = DataRandomFile(u_path, 0o600, size=199, mtime=mtime)
        u_parent = env.test_data[u_path.parent]
        u_parent.mtime = mtime
        env.add_test_data(('user',), [u_parent, u_file])
        setup_testdata(env.root, [u_file])

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 9, 15, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-210915-daily.tar.bz2"
        env.check_archive(archive_name, 'user', 'daily')
        env.add_index(archive_name, 'serv', 'daily',
                      type='incr', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('user',), 'daily')

    @pytest.mark.dependency(depends=["test_20210915"], scope='class')
    def test_20210917(self, env):
        """Daily incremental backup.
        """
        mtime = 1631781786
        u_path = Path("home", "jdoe", "rnd16.dat")
        u_file = DataRandomFile(u_path, 0o600, size=24, mtime=mtime)
        u_parent = env.test_data[u_path.parent]
        u_parent.mtime = mtime
        env.add_test_data(('user',), [u_parent, u_file])
        setup_testdata(env.root, [u_file])

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 9, 17, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-210917-daily.tar.bz2"
        env.check_archive(archive_name, 'user', 'daily')
        env.add_index(archive_name, 'serv', 'daily',
                      type='incr', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('user',), 'daily')

    @pytest.mark.dependency(depends=["test_20210917"], scope='class')
    def test_20211004(self, env):
        """Quarterly full backup.
        """
        mtime = 1633264335
        u_path = Path("home", "jdoe", "rnd17.dat")
        u_file = DataRandomFile(u_path, 0o600, size=467, mtime=mtime)
        u_parent = env.test_data[u_path.parent]
        u_parent.mtime = mtime
        env.add_test_data(('user',), [u_parent, u_file])
        setup_testdata(env.root, [u_file])

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 10, 4, 3, 10))
        env.run_backup_tool("backup-tool --verbose create --user jdoe")
        archive_name = "jdoe-211004-quarterly.tar.bz2"
        env.check_archive(archive_name, 'user', 'quarterly')
        env.add_index(archive_name, 'serv', 'quarterly',
                      type='full', user='jdoe')

        env.run_backup_tool("backup-tool --verbose index")
        env.check_index()
        env.flush_test_data(('user',), 'monthly')


class TestBackupToolDedup:
    """Test the dedup configration option.
    """

    src_dir = Path("root")
    src_path = Path("root", "rnd.dat")
    lnk_path = Path("root", "rnd_lnk.dat")
    cp_path = Path("root", "rnd_cp.dat")

    cfg = """# Configuration file for backup-tool.
# All paths are within a root directory that need to be substituted.

[sys]
name = %(host)s-%(date)s-%(schedule)s-$suffix.tar.bz2
dirs =
    $root/root
backupdir = $root/net/backup
schedules = full/incr
schedule.full.date = Mon *-*-2..8
schedule.incr.date = Mon *
"""

    def init_data(self, env, dedup):
        env.config("net/backup", "var/backup")
        subst = dict(root=env.root, suffix=str(dedup))
        cfg = string.Template(self.cfg).substitute(subst)
        if dedup:
            cfg_path = env.root / "etc" / ("backup-%s.cfg" % dedup)
            cfg += "dedup = %s\n" % dedup
        else:
            cfg_path = env.root / "etc" / "backup.cfg"
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        with cfg_path.open("wt") as f:
            f.write(cfg)
        if not (env.root / self.src_dir).is_dir():
            sys_data = [
                DataDir(self.src_dir, 0o700, mtime=1633274230),
                DataFile(self.src_path, 0o600, mtime=1633243020),
            ]
            env.add_test_data(('sys',), sys_data)
            excl_data = [
                DataDir(Path("net", "backup"), 0o755, mtime=1632704400),
            ]
            env.add_test_data(('excl',), excl_data)
            env.setup_test_data()
            src_file = env.test_data[self.src_path]
            os.link(env.root / self.src_path, env.root / self.lnk_path)
            shutil.copy2(env.root / self.src_path, env.root / self.cp_path)
            extra_data = [
                DataFile(self.lnk_path, src_file.mode,
                         mtime=src_file.mtime, checksum=src_file.checksum),
                DataFile(self.cp_path, src_file.mode,
                         mtime=src_file.mtime, checksum=src_file.checksum),
            ]
            env.add_test_data(('sys',), extra_data)
            env.test_data[self.src_dir].create(env.root)
        env.monkeypatch.setenv("BACKUP_CFG", str(env.root / cfg_path))

    @pytest.mark.parametrize("dedup", [None, 'never', 'link', 'content'])
    def test_full(self, env, dedup):
        """Full backup of initial test data.
        """
        self.init_data(env, dedup)

        env.set_hostname("serv")
        env.set_datetime(datetime.datetime(2021, 10, 4, 3, 0))
        env.run_backup_tool("backup-tool --verbose create --policy sys")
        archive_name = "serv-211004-full-%s.tar.bz2" % str(dedup)
        env.check_archive(archive_name, 'sys', 'full')
        with Archive().open(env.backupdir / archive_name) as archive:
            src_path = archive._arcname(env.root / self.src_path)
            lnk_path = archive._arcname(env.root / self.lnk_path)
            cp_path = archive._arcname(env.root / self.cp_path)
            ti_lnk = archive._file.getmember(lnk_path)
            ti_cp = archive._file.getmember(cp_path)
            if dedup == 'never':
                assert ti_lnk.isfile()
                assert ti_cp.isfile()
            elif dedup is None or dedup == 'link':
                assert ti_lnk.islnk()
                assert ti_lnk.linkname == src_path
                assert ti_cp.isfile()
            elif dedup == 'content':
                assert ti_lnk.islnk()
                assert ti_lnk.linkname == src_path
                assert ti_cp.islnk()
                assert ti_cp.linkname == src_path
