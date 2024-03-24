"""A collection of internal helper routines.

.. note::
   This module is intended for the internal use in archive-tools and
   is not considered to be part of the API.  No effort will be made to
   keep anything in here compatible between different versions.
"""

from contextlib import contextmanager
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
import packaging.version


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


class Version(packaging.version.Version):
    """A variant of packaging.version.Version.

    This version adds comparison with strings.

    >>> version = Version('4.11.1')
    >>> version == '4.11.1'
    True
    >>> version < '4.9.3'
    False
    >>> version = Version('5.0.0a1')
    >>> version > '4.11.1'
    True
    >>> version < '5.0.0'
    True
    >>> version == '5.0.0a1'
    True
    """
    def __lt__(self, other):
        if isinstance(other, str):
            other = type(self)(other)
        return super().__lt__(other)
    def __le__(self, other):
        if isinstance(other, str):
            other = type(self)(other)
        return super().__le__(other)
    def __eq__(self, other):
        if isinstance(other, str):
            other = type(self)(other)
        return super().__eq__(other)
    def __ge__(self, other):
        if isinstance(other, str):
            other = type(self)(other)
        return super().__ge__(other)
    def __gt__(self, other):
        if isinstance(other, str):
            other = type(self)(other)
        return super().__gt__(other)
    def __ne__(self, other):
        if isinstance(other, str):
            other = type(self)(other)
        return super().__ne__(other)


@contextmanager
def tmp_chdir(dir):
    """A context manager to temporarily change directory.
    """
    save_dir = os.getcwd()
    if dir:
        os.chdir(dir)
    try:
        yield dir
    finally:
        os.chdir(save_dir)


@contextmanager
def tmp_umask(mask):
    """A context manager to temporarily set the umask.
    """
    save_mask = os.umask(mask)
    try:
        yield mask
    finally:
        os.umask(save_mask)


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
