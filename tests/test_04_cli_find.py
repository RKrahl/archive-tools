"""Test the find subcommand in the command line tool.
"""

import datetime
import fnmatch
import itertools
from pathlib import Path
import shutil
from tempfile import TemporaryFile
from archive import Archive
from archive.tools import tmp_chdir
import pytest
from conftest import *

now = datetime.datetime.now()
twodays_old = now - datetime.timedelta(days=2)
twohours_old = now - datetime.timedelta(hours=2)

cest = datetime.timezone(datetime.timedelta(hours=2))

testdata = [
    [
        DataDir(Path("base"), 0o755, mtime=1555271302),
        DataDir(Path("base", "data"), 0o750, mtime=1555271302),
        DataDir(Path("base", "empty"), 0o755, mtime=1547911753),
        DataFile(Path("base", "msg.txt"), 0o644, mtime=1547911753),
        DataFile(Path("base", "data", "rnd.dat"), 0o640, mtime=1555271302),
        DataFile(Path("base", "rnd.dat"), 0o600, mtime=1563112510),
        DataSymLink(Path("base", "s.dat"), Path("data", "rnd.dat"),
                    mtime=1555271302),
    ],
    [
        DataDir(Path("base"), 0o755, mtime=1555271302),
        DataDir(Path("base", "data"), 0o750, mtime=1565100853),
        DataFile(Path("base", "msg.txt"), 0o644, mtime=1547911753),
        DataRandomFile(Path("base", "data", "bernd.dat"), 0o640, size=385),
        DataRandomFile(Path("base", "data", "rnd1.dat"), 0o640,
                       size=732, mtime=twodays_old.timestamp()),
        DataRandomFile(Path("base", "data", "rnd2.dat"), 0o640,
                       size=487, mtime=twohours_old.timestamp()),
        DataRandomFile(Path("base", "empty"), 0o644, size=0, mtime=1565100853),
        DataFile(Path("base", "rnd.dat"), 0o600, mtime=1563112510),
        DataSymLink(Path("base", "s.dat"), Path("rnd.dat"), mtime=1565100853),
    ],
]

def archive_paths(root, abspath):
    absflag = "abs" if abspath else "rel"
    return [root / ("archive-%s-%d.tar.bz2" % (absflag, i))
            for i in range(1, len(testdata)+1)]

@pytest.fixture(scope="module")
def test_dir(tmpdir):
    with tmp_chdir(tmpdir):
        rel_paths = archive_paths(Path(""), False)
        abs_paths = archive_paths(Path(""), True)
        for i, data in enumerate(testdata):
            base = next(filter(lambda e: e.type == 'd', data)).path
            setup_testdata(tmpdir, data)
            Archive().create(rel_paths[i], "bz2", [base])
            Archive().create(abs_paths[i], "bz2", [tmpdir / base])
            shutil.rmtree(str(base))
    return tmpdir

@pytest.mark.parametrize("abspath", [False, True])
def test_find_all(test_dir, abspath):
    """Call archive-tool find with no filtering options.
    Expect the call to list all entries from the archives.
    """
    archives = archive_paths(test_dir, abspath)
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["find"] + [str(p) for p in archives]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        expected_out = []
        for arch, data in zip(archives, testdata):
            if abspath:
                paths = sorted(test_dir / e.path for e in data)
            else:
                paths = sorted(e.path for e in data)
            expected_out.extend("%s:%s" % (arch, p) for p in paths)
        for l, ex_l in itertools.zip_longest(get_output(f), expected_out):
            assert l == ex_l

@pytest.mark.parametrize("type", ['f', 'd', 'l'])
@pytest.mark.parametrize("abspath", [False, True])
def test_find_bytype(test_dir, abspath, type):
    """Call archive-tool to find entries by type.
    """
    archives = archive_paths(test_dir, abspath)
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["find", "--type", type] + [str(p) for p in archives]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        expected_out = []
        for arch, data in zip(archives, testdata):
            if abspath:
                paths = sorted(test_dir / e.path
                               for e in data
                               if e.type == type)
            else:
                paths = sorted(e.path
                               for e in data
                               if e.type == type)
            expected_out.extend("%s:%s" % (arch, p) for p in paths)
        for l, ex_l in itertools.zip_longest(get_output(f), expected_out):
            assert l == ex_l

@pytest.mark.parametrize("abspath", [False, True])
def test_find_byname_exact(test_dir, abspath):
    """Call archive-tool to find entries by exact name.
    """
    archives = archive_paths(test_dir, abspath)
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["find", "--name", "rnd.dat"] + [str(p) for p in archives]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        expected_out = []
        for arch, data in zip(archives, testdata):
            if abspath:
                paths = sorted(test_dir / e.path
                               for e in data
                               if e.path.name == "rnd.dat")
            else:
                paths = sorted(e.path
                               for e in data
                               if e.path.name == "rnd.dat")
            expected_out.extend("%s:%s" % (arch, p) for p in paths)
        for l, ex_l in itertools.zip_longest(get_output(f), expected_out):
            assert l == ex_l

@pytest.mark.parametrize("pattern", ["rnd*.dat", "rnd.*", "rnd?.dat"])
@pytest.mark.parametrize("abspath", [False, True])
def test_find_byname_wildcard(test_dir, pattern, abspath):
    """Call archive-tool to find entries with matching name.
    """
    archives = archive_paths(test_dir, abspath)
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["find", "--name", pattern] + [str(p) for p in archives]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        expected_out = []
        for arch, data in zip(archives, testdata):
            if abspath:
                paths = sorted(test_dir / e.path
                               for e in data
                               if fnmatch.fnmatch(e.path.name, pattern))
            else:
                paths = sorted(e.path
                               for e in data
                               if fnmatch.fnmatch(e.path.name, pattern))
            expected_out.extend("%s:%s" % (arch, p) for p in paths)
        for l, ex_l in itertools.zip_longest(get_output(f), expected_out):
            assert l == ex_l

@pytest.mark.parametrize(("mtime", "delta"), [
    ("-1", datetime.timedelta(days=1)),
    ("+1", datetime.timedelta(days=1)),
    ("-3d", datetime.timedelta(days=3)),
    ("+3d", datetime.timedelta(days=3)),
    ("-2.5h", datetime.timedelta(hours=2.5)),
    ("+2.5h", datetime.timedelta(hours=2.5)),
    ("-5m", datetime.timedelta(minutes=5)),
    ("+5m", datetime.timedelta(minutes=5)),
])
def test_find_bymtime_rel(test_dir, mtime, delta):
    """Call archive-tool to find entries by relative modification time,
    e.g. age.
    """
    def matches(direct, timestamp, entry):
        if direct == '+':
            return entry.mtime is not None and entry.mtime < timestamp
        elif direct == '-':
            return entry.mtime is None or entry.mtime > timestamp
    archives = archive_paths(test_dir, False)
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["find", "--mtime=%s" % mtime] + [str(p) for p in archives]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        expected_out = []
        timestamp = (datetime.datetime.now() - delta).timestamp()
        for arch, data in zip(archives, testdata):
            paths = sorted(e.path
                           for e in data
                           if matches(mtime[0], timestamp, e))
            expected_out.extend("%s:%s" % (arch, p) for p in paths)
        for l, ex_l in itertools.zip_longest(get_output(f), expected_out):
            assert l == ex_l

@pytest.mark.parametrize(("mtime", "dt"), [
    ("<2019-04-01", datetime.datetime(2019, 4, 1)),
    (">2019-04-01", datetime.datetime(2019, 4, 1)),
    ("< 2019-04-14 21:45:12", datetime.datetime(2019, 4, 14, 21, 45, 12)),
    ("> 2019-04-14 21:45:12", datetime.datetime(2019, 4, 14, 21, 45, 12)),
    ("< 2019-04-14T21:49:12", datetime.datetime(2019, 4, 14, 21, 49, 12)),
    ("> 2019-04-14T21:49:12", datetime.datetime(2019, 4, 14, 21, 49, 12)),
])
def test_find_bymtime_abs(test_dir, mtime, dt):
    """Call archive-tool to find entries by absolute modification time.
    """
    def matches(direct, timestamp, entry):
        if direct == '<':
            return entry.mtime is not None and entry.mtime < timestamp
        elif direct == '>':
            return entry.mtime is None or entry.mtime > timestamp
    archives = archive_paths(test_dir, False)
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["find", "--mtime=%s" % mtime] + [str(p) for p in archives]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        expected_out = []
        timestamp = dt.timestamp()
        for arch, data in zip(archives, testdata):
            paths = sorted(e.path
                           for e in data
                           if matches(mtime[0], timestamp, e))
            expected_out.extend("%s:%s" % (arch, p) for p in paths)
        for l, ex_l in itertools.zip_longest(get_output(f), expected_out):
            assert l == ex_l

@pytest.mark.parametrize(("mtime", "dt"), [
    ("< 2019-04-14 21:45", datetime.datetime(2019, 4, 14, 21, 45)),
    ("> 2019-04-14 21:45+02:00",
     datetime.datetime(2019, 4, 14, 21, 45, tzinfo=cest)),
    ("< Sun, 14 Apr 2019 21:45:12 +0200",
     datetime.datetime(2019, 4, 14, 21, 45, 12, tzinfo=cest)),
    ("> Sun, 14 Apr 2019 19:45:12 UTC",
     datetime.datetime(2019, 4, 14, 19, 45, 12, tzinfo=datetime.timezone.utc)),
])
def test_find_bymtime_abs_datefmt(test_dir, mtime, dt):
    """Call archive-tool to find entries by absolute modification time,
    using different date formats.  This requires dateutil.parser.
    """
    pytest.importorskip("dateutil.parser")
    def matches(direct, timestamp, entry):
        if direct == '<':
            return entry.mtime is not None and entry.mtime < timestamp
        elif direct == '>':
            return entry.mtime is None or entry.mtime > timestamp
    archives = archive_paths(test_dir, False)
    with TemporaryFile(mode="w+t", dir=str(test_dir)) as f:
        args = ["find", "--mtime=%s" % mtime] + [str(p) for p in archives]
        callscript("archive-tool.py", args, stdout=f)
        f.seek(0)
        expected_out = []
        timestamp = dt.timestamp()
        for arch, data in zip(archives, testdata):
            paths = sorted(e.path
                           for e in data
                           if matches(mtime[0], timestamp, e))
            expected_out.extend("%s:%s" % (arch, p) for p in paths)
        for l, ex_l in itertools.zip_longest(get_output(f), expected_out):
            assert l == ex_l
