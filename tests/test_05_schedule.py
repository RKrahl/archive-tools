"""Test class archive.bt.schedule.ScheduleDate.
"""

import datetime
import pytest
from archive.bt.schedule import ScheduleDate


test_schedules = [
    {
        'schedule' : "Sat,Thu,Mon..Wed,Sat..Sun *",
        'dates': [
            ( datetime.datetime(2021, 7, 1, 5, 13, 21), True ),
            ( datetime.datetime(2021, 7, 2, 6, 24, 36), False ),
            ( datetime.datetime(2021, 7, 3, 3, 57, 42), True ),
            ( datetime.datetime(2021, 7, 4, 8, 8, 48), True ),
            ( datetime.datetime(2021, 7, 5, 19, 50, 14), True ),
            ( datetime.datetime(2021, 7, 6, 22, 48, 56), True ),
            ( datetime.datetime(2021, 7, 7, 1, 11, 49), True ),
        ],
    },
    {
        'schedule' : "Mon,Sun 2012-*-* 2,1:23",
        'dates': [
            ( datetime.datetime(2012, 10, 20, 1, 23, 48), False ),
            ( datetime.datetime(2012, 10, 21, 1, 23, 7), True ),
            ( datetime.datetime(2012, 10, 21, 2, 24, 30), False ),
            ( datetime.datetime(2012, 10, 21, 3, 23, 26), False ),
            ( datetime.datetime(2012, 10, 22, 1, 23, 39), True ),
        ],
    },
    {
        'schedule' : "Wed *-1",
        'dates': [
            ( datetime.datetime(2002, 4, 1, 13, 52, 43), False ),
            ( datetime.datetime(2002, 5, 1, 17, 11, 44), True ),
            ( datetime.datetime(2002, 6, 1, 2, 11, 24), False ),
            ( datetime.datetime(2003, 9, 1, 6, 5, 23), False ),
            ( datetime.datetime(2003, 9, 3, 2, 37, 36), False ),
            ( datetime.datetime(2003, 10, 1, 15, 30, 6), True ),
            ( datetime.datetime(2003, 11, 1, 20, 29, 54), False ),
        ],
    },
    {
        'schedule' : "Wed..Wed,Wed *-1",
        'dates': [
            ( datetime.datetime(2002, 4, 1, 13, 52, 43), False ),
            ( datetime.datetime(2002, 5, 1, 17, 11, 44), True ),
            ( datetime.datetime(2002, 6, 1, 2, 11, 24), False ),
            ( datetime.datetime(2003, 9, 1, 6, 5, 23), False ),
            ( datetime.datetime(2003, 9, 3, 2, 37, 36), False ),
            ( datetime.datetime(2003, 10, 1, 15, 30, 6), True ),
            ( datetime.datetime(2003, 11, 1, 20, 29, 54), False ),
        ],
    },
    {
        'schedule' : "10-15",
        'dates': [
            ( datetime.datetime(2017, 9, 15, 3, 8, 17), False ),
            ( datetime.datetime(2017, 10, 14, 23, 48, 51), False ),
            ( datetime.datetime(2017, 10, 15, 4, 12, 36), True ),
            ( datetime.datetime(2018, 10, 15, 11, 14, 43), True ),
        ],
    },
    {
        'schedule' : "Fri 1..7 4,10,16,22:30",
        'dates': [
            ( datetime.datetime(2021, 7, 1, 4, 30, 45), False ),
            ( datetime.datetime(2021, 7, 2, 4, 30, 45), True ),
            ( datetime.datetime(2021, 7, 2, 5, 30, 45), False ),
            ( datetime.datetime(2021, 7, 2, 16, 30, 45), True ),
            ( datetime.datetime(2021, 7, 9, 16, 30, 45), False ),
        ],
    },
    {
        'schedule' : "Mon *-*-2..8",
        'dates': [
            ( datetime.datetime(2021, 3, 1, 3, 0), False ),
            ( datetime.datetime(2021, 3, 5, 3, 0), False ),
            ( datetime.datetime(2021, 3, 8, 3, 0), True ),
            ( datetime.datetime(2021, 3, 15, 3, 0), False ),
            ( datetime.datetime(2021, 7, 5, 3, 0), True ),
            ( datetime.datetime(2021, 7, 9, 3, 0), False ),
            ( datetime.datetime(2021, 7, 12, 3, 0), False ),
        ],
    },
    {
        'schedule' : "Mon *",
        'dates': [
            ( datetime.datetime(2021, 3, 1, 3, 0), True ),
            ( datetime.datetime(2021, 3, 5, 3, 0), False ),
            ( datetime.datetime(2021, 3, 8, 3, 0), True ),
            ( datetime.datetime(2021, 3, 15, 3, 0), True ),
            ( datetime.datetime(2021, 7, 5, 3, 0), True ),
            ( datetime.datetime(2021, 7, 9, 3, 0), False ),
            ( datetime.datetime(2021, 7, 12, 3, 0), True ),
        ],
    },
    {
        'schedule' : "*",
        'dates': [
            ( datetime.datetime(2021, 3, 1, 3, 0), True ),
            ( datetime.datetime(2021, 3, 5, 3, 0), True ),
            ( datetime.datetime(2021, 3, 8, 3, 0), True ),
            ( datetime.datetime(2021, 3, 15, 3, 0), True ),
            ( datetime.datetime(2021, 7, 5, 3, 0), True ),
            ( datetime.datetime(2021, 7, 9, 3, 0), True ),
            ( datetime.datetime(2021, 7, 12, 3, 0), True ),
        ],
    },
]

@pytest.mark.parametrize("schedule,dates", [
    (s['schedule'], s['dates']) for s in test_schedules
])
def test_schedule_parse(schedule, dates):
    """Various parsing examples for ScheduleDate.
    """
    sd = ScheduleDate(schedule)
    for d in dates:
        assert (d[0] in sd) == d[1]
