"""Test the find subcommand in the command line tool.
"""

import fnmatch
import itertools
from pathlib import Path
import shutil
from tempfile import TemporaryFile
from archive import Archive
from archive.tools import tmp_chdir
import pytest
from conftest import setup_testdata, callscript

testdata = [
    {
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
    },
    {
        "dirs": [
            (Path("base"), 0o755),
            (Path("base", "data"), 0o750),
        ],
        "files": [
            (Path("base", "msg.txt"), 0o644),
            (Path("base", "data", "bernd.dat"), 0o640),
            (Path("base", "data", "rnd1.dat"), 0o640),
            (Path("base", "data", "rnd2.dat"), 0o640),
            (Path("base", "empty"), 0o644),
            (Path("base", "rnd.dat"), 0o600),
        ],
        "symlinks": [
            (Path("base", "s.dat"), Path("rnd.dat")),
        ]
    },
]

def archive_paths(root, abspath):
    absflag = "abs" if abspath else "rel"
    return [root / ("archive-%s-%d.tar.bz2" % (absflag, i))
            for i in range(1, len(testdata)+1)]

def get_output(fileobj):
    while True:
        line = fileobj.readline()
        if not line:
            break
        line = line.strip()
        print("< %s" % line)
        yield line

@pytest.fixture(scope="module")
def test_dir(tmpdir):
    with tmp_chdir(tmpdir):
        rel_paths = archive_paths(Path(""), False)
        abs_paths = archive_paths(Path(""), True)
        for i, data in enumerate(testdata):
            base = data["dirs"][0][0]
            setup_testdata(tmpdir, **data)
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
            data_entries = itertools.chain.from_iterable(data.values())
            if abspath:
                paths = sorted(test_dir / e[0] for e in data_entries)
            else:
                paths = sorted(e[0] for e in data_entries)
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
            data_entries = itertools.chain.from_iterable(data.values())
            if abspath:
                paths = sorted(test_dir / e[0]
                               for e in data_entries
                               if e[0].name == "rnd.dat")
            else:
                paths = sorted(e[0]
                               for e in data_entries
                               if e[0].name == "rnd.dat")
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
            data_entries = itertools.chain.from_iterable(data.values())
            if abspath:
                paths = sorted(test_dir / e[0]
                               for e in data_entries
                               if fnmatch.fnmatch(e[0].name, pattern))
            else:
                paths = sorted(e[0]
                               for e in data_entries
                               if fnmatch.fnmatch(e[0].name, pattern))
            expected_out.extend("%s:%s" % (arch, p) for p in paths)
        for l, ex_l in itertools.zip_longest(get_output(f), expected_out):
            assert l == ex_l
