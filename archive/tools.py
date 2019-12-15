"""A collection of internal helper routines.

.. note::
   This module is intended for the internal use in archive-tools and
   is not considered to be part of the API.  No effort will be made to
   keep anything in here compatible between different versions.
"""

import datetime
import hashlib
import os
import stat
try:
    from dateutil.tz import gettz
except ImportError:
    gettz = None
try:
    from dateutil.parser import parse as _dateutil_parse
except ImportError:
    _dateutil_parse = None


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


class tmp_umask():
    """A context manager to temporarily set the umask.
    """
    def __init__(self, mask):
        self.save_mask = None
        self.mask = mask
    def __enter__(self):
        self.save_mask = os.umask(self.mask)
    def _restore_mask(self):
        if self.save_mask:
            os.umask(self.save_mask)
        self.save_mask = None
    def __exit__(self, type, value, tb):
        self._restore_mask()
    def __del__(self):
        self._restore_mask()


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


def parse_date(date_string):
    """Parse a date string as returned from now_str() into a datetime object.
    """
    if _dateutil_parse:
        return _dateutil_parse(date_string)
    else:
        try:
            date_fmt = "%a, %d %b %Y %H:%M:%S %z"
            return datetime.datetime.strptime(date_string, date_fmt)
        except ValueError:
            date_fmt = "%a, %d %b %Y %H:%M:%S"
            return datetime.datetime.strptime(date_string, date_fmt)


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


mode_ft = {
    stat.S_IFLNK: "l",
    stat.S_IFREG: "f",
    stat.S_IFDIR: "d",
}
"""map stat mode value to file type"""

ft_mode = { t:m for m,t in mode_ft.items() }
"""map file type to stat mode value"""
