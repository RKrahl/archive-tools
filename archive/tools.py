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


if hasattr(datetime.datetime, 'fromisoformat'):
    # Python 3.7 and newer
    _dt_fromisoformat = datetime.datetime.fromisoformat
else:
    # Python 3.6
    import re
    _dt_isofmt_re = re.compile(r'''^
        (?P<dy>\d{4})-(?P<dm>\d{2})-(?P<dd>\d{2})   # date
        .                                           # separator (any character)
        (?P<th>\d{2}):(?P<tm>\d{2}):(?P<ts>\d{2})   # time
        (?:(?P<zh>[+-]\d{2}):(?P<zm>\d{2}))?        # time zone (optional)
    $''', re.X)
    def _dt_fromisoformat(date_string):
        m = _dt_isofmt_re.match(date_string)
        if m:
            dt = [int(i) for i in m.group('dy', 'dm', 'dd', 'th', 'tm', 'ts')]
            if m.group('zh'):
                zh = int(m.group('zh'))
                zm = int(m.group('zm'))
                offs = datetime.timedelta(hours=zh, minutes=zm)
                tz = datetime.timezone(offs)
            else:
                tz = None
            return datetime.datetime(*dt, tzinfo=tz)
        else:
            raise ValueError("Invalid isoformat string: '%s'" % date_string)


class tmp_chdir():
    """A context manager to temporarily change directory.
    """
    def __init__(self, dir):
        self.save_dir = None
        self.dir = dir
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


def date_str_rfc5322(dt):
    """Return a RFC 5322 string representation of a datetime.
    """
    return dt.strftime("%a, %d %b %Y %H:%M:%S %z").strip()


def now_str():
    """Return the current local date and time as a string.
    """
    if gettz:
        now = datetime.datetime.now(tz=gettz())
    else:
        now = datetime.datetime.now()
    return date_str_rfc5322(now)


def parse_date(date_string):
    """Parse a date string into a datetime object.

    The function accepts strings as returned by datetime.isoformat()
    and date_str_rfc5322().
    """
    if _dateutil_parse:
        return _dateutil_parse(date_string)
    else:
        try:
            return _dt_fromisoformat(date_string)
        except ValueError:
            try:
                date_fmt = "%a, %d %b %Y %H:%M:%S %z"
                return datetime.datetime.strptime(date_string, date_fmt)
            except ValueError:
                try:
                    date_fmt = "%a, %d %b %Y %H:%M:%S"
                    return datetime.datetime.strptime(date_string, date_fmt)
                except ValueError:
                    raise ValueError("Invalid date string: '%s'"
                                     % date_string) from None


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
