"""Provide helper for the backup-tool related to schedules.
"""

import collections
import datetime
from enum import IntEnum
import re
from lark import Lark, Transformer


class NoFullBackupError(Exception):
    pass


class _DTMatcher:
    """datetime component matcher to be used in ScheduleDate.
    This is an abstract base class.
    """
    def matches(self, value):
        raise NotImplementedError

class _DTMatcherAny(_DTMatcher):

    def matches(self, value):
        return True

    def __str__(self):
        return '*'

class _DTMatcherValue(_DTMatcher):

    def __init__(self, value):
        assert isinstance(value, int)
        self.value = value

    def matches(self, value):
        return value == self.value

    def __str__(self):
        return '%d' % self.value

class _DTMatcherInterval(_DTMatcher):

    def __init__(self, i_min, i_max):
        assert isinstance(i_min, int)
        assert isinstance(i_max, int)
        self.i_min = i_min
        self.i_max = i_max

    def matches(self, value):
        return self.i_min <= value <= self.i_max

    def __str__(self):
        return '[%d,%d]' % (self.i_min, self.i_max)

class _DTMatcherList(_DTMatcher):

    def __init__(self, dtms):
        self.dtms = dtms

    def matches(self, value):
        for dtm in self.dtms:
            if dtm.matches(value):
                return True
        else:
            return False

    def __str__(self):
        return '(%s)' % ",".join(str(m) for m in self.dtms)

_wd = dict(Mon=1, Tue=2, Wed=3, Thu=4, Fri=5, Sat=6, Sun=7)

_dt_fields = ('weekday', 'year', 'month', 'day', 'hour', 'minute', 'second')
_dt_tuple = collections.namedtuple('_dt_tuple', _dt_fields)


_sd_grammar = r"""
    sd: [weekday _WS] date [_WS time]

    weekday: wd ("," wd)*   -> vlist

    wd: wdstr               -> value
      | wdstr ".." wdstr    -> intervall

    wdstr: MON | TUE | WED | THU | FRI | SAT | SUN

    date: [[dtc "-"] dtc "-"] dtc

    time: dtc ":" dtc [":" dtc]

    dtc: dtcs ("," dtcs)*   -> vlist

    dtcs: "*"               -> wildcard
        | INT               -> value
        | INT ".." INT      -> intervall

    MON: "Mon"
    TUE: "Tue"
    WED: "Wed"
    THU: "Thu"
    FRI: "Fri"
    SAT: "Sat"
    SUN: "Sun"

    _WS: (" "|/\t/)+

    %import common.INT
"""

class _SDTf(Transformer):

    def wdstr(self, l):
        (s,) = l
        return _wd[s]

    def wildcard(self, l):
        return _DTMatcherAny()

    def value(self, l):
        (v,) = l
        return _DTMatcherValue(int(v))

    def intervall(self, l):
        (a, b) = l
        return _DTMatcherInterval(int(a), int(b))

    def vlist(self, l):
        if len(l) == 1:
            return l[0]
        else:
            return _DTMatcherList(l)

    def date(self, l):
        l = list(l)
        while len(l) < 3:
            l.insert(0, _DTMatcherAny())
        return l

    def time(self, l):
        l = list(l)
        while len(l) < 3:
            l.append(_DTMatcherAny())
        return l

    def sd(self, l):
        l = list(l)
        r = []
        # weekday
        if isinstance(l[0], _DTMatcher):
            r.append(l.pop(0))
        else:
            r.append(_DTMatcherAny())
        # date
        r.extend(l.pop(0))
        # time
        if l:
            r.extend(l.pop(0))
        else:
            r.extend((_DTMatcherAny(), _DTMatcherAny(), _DTMatcherAny()))
        return r

_sd_parser = Lark(_sd_grammar,
                  start='sd', parser='lalr', transformer=_SDTf(),
                  maybe_placeholders=False)

class ScheduleDate(_dt_tuple):

    def __new__(cls, spec):
        l = _sd_parser.parse(spec)
        return super().__new__(cls, *l)

    def __contains__(self, dt):
        if isinstance(dt, datetime.datetime):
            return (self.weekday.matches(dt.isoweekday()) and
                    self.year.matches(dt.year) and
                    self.month.matches(dt.month) and
                    self.day.matches(dt.day) and
                    self.hour.matches(dt.hour) and
                    self.minute.matches(dt.minute) and
                    self.second.matches(dt.second))
        else:
            return False


class BaseSchedule:
    """Abstract base class for schedules.
    """

    SubClasses = dict()
    ClsName = None

    def __init__(self, name, date, parent):
        self.name = name
        self.date = date
        self.parent = parent

    def match_date(self, dt):
        return dt in self.date

    def get_base_archives(self, archives):
        raise NotImplementedError

    def get_child_base_archives(self, archives):
        raise NotImplementedError

    @classmethod
    def register_clsname(cls, subcls):
        """A class decorator to register the name for a subclass.
        """
        assert issubclass(subcls, cls)
        assert subcls.ClsName and subcls.ClsName not in cls.SubClasses
        cls.SubClasses[subcls.ClsName] = subcls
        return subcls

@BaseSchedule.register_clsname
class FullSchedule(BaseSchedule):

    ClsName = "full"

    def get_base_archives(self, archives):
        return []

    def get_child_base_archives(self, archives):
        last_full = None
        for i in archives:
            if i.schedule == self.name:
                last_full = i
        if last_full:
            return [last_full]
        else:
            raise NoFullBackupError

@BaseSchedule.register_clsname
class CumuSchedule(BaseSchedule):

    ClsName = "cumu"

    def get_base_archives(self, archives):
        return self.parent.get_child_base_archives(archives)

    def get_child_base_archives(self, archives):
        base_archives = self.parent.get_child_base_archives(archives)
        p_idx = archives.index(base_archives[-1])
        last_cumu = None
        for i in archives[p_idx+1:]:
            if i.schedule == self.name:
                last_cumu = i
        if last_cumu:
            base_archives.append(last_cumu)
        return base_archives

@BaseSchedule.register_clsname
class IncrSchedule(BaseSchedule):

    ClsName = "incr"

    def get_base_archives(self, archives):
        base_archives = self.parent.get_child_base_archives(archives)
        p_idx = archives.index(base_archives[-1])
        for i in archives[p_idx+1:]:
            if i.schedule == self.name:
                base_archives.append(i)
        return base_archives

    def get_child_base_archives(self, archives):
        return self.get_base_archives(archives)
