import datetime
import hashlib
import os
import stat
try:
    from dateutil.tz import gettz
except ImportError:
    gettz = None


class tmp_chdir():
    """A context manager to temporarily change directory.
    """
    def __init__(self, dir):
        self.save_dir = None
        self.dir = str(dir)
    def __enter__(self):
        self.save_dir = os.getcwd()
        os.chdir(self.dir)
    def _restore_dir(self):
        if self.save_dir:
            os.chdir(self.save_dir)
        self.save_dir = None
    def __exit__(self, type, value, tb):
        self._restore_dir()
    def __del__(self):
        self._restore_dir()


def now_str():
    """Return the current local date and time as a string.
    """
    if gettz:
        now = datetime.datetime.now(tz=gettz())
        date_fmt = "%a, %d %b %Y %H:%M:%S %z"
    else:
        now = datetime.datetime.now()
        date_fmt = "%a, %d %b %Y %H:%M:%S"
    return now.strftime(date_fmt)


def checksum(fileobj, hashalg):
    """Calculate hashes for a file.
    """
    if not hashalg:
        return {}
    m = { h:hashlib.new(h) for h in hashalg }
    chunksize = 8192
    while True:
        chunk = fileobj.read(chunksize)
        if not chunk:
            break
        for h in hashalg:
            m[h].update(chunk)
    return { h: m[h].hexdigest() for h in hashalg }


def modstr(t, m):
    ftch = '-' if t == 'f' else t
    urch = 'r' if m & stat.S_IRUSR else '-'
    uwch = 'w' if m & stat.S_IWUSR else '-'
    if m & stat.S_ISUID:
        uxch = 's' if m & stat.S_IXUSR else 'S'
    else:
        uxch = 'x' if m & stat.S_IXUSR else '-'
    grch = 'r' if m & stat.S_IRGRP else '-'
    gwch = 'w' if m & stat.S_IWGRP else '-'
    if m & stat.S_ISGID:
        gxch = 's' if m & stat.S_IXGRP else 'S'
    else:
        gxch = 'x' if m & stat.S_IXGRP else '-'
    orch = 'r' if m & stat.S_IROTH else '-'
    owch = 'w' if m & stat.S_IWOTH else '-'
    if m & stat.S_ISVTX:
        oxch = 't' if m & stat.S_IXOTH else 'T'
    else:
        oxch = 'x' if m & stat.S_IXOTH else '-'
    chars = (ftch, urch, uwch, uxch, grch, gwch, gxch, orch, owch, oxch)
    return ''.join(chars)
