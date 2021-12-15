"""Test helper functions dealing with dates in the archive.tools module.
"""

import datetime
import pytest
import archive.tools

tz_utc = datetime.timezone.utc
tz_cest = datetime.timezone(datetime.timedelta(hours=2))
tz_mst = datetime.timezone(datetime.timedelta(hours=-7))
testdates = [
    {
        'dt': datetime.datetime(2021, 5, 1, 15, 21, 5),
        'str_iso': "2021-05-01T15:21:05",
        'str_iso_sp': "2021-05-01 15:21:05",
        'str_rfc5322': "Sat, 01 May 2021 15:21:05",
    },
    {
        'dt': datetime.datetime(1967, 7, 12, 4, 30, 21, tzinfo=tz_utc),
        'str_iso': "1967-07-12T04:30:21+00:00",
        'str_iso_sp': "1967-07-12 04:30:21+00:00",
        'str_rfc5322': "Wed, 12 Jul 1967 04:30:21 +0000",
    },
    {
        'dt': datetime.datetime(2021, 5, 20, 15, 21, 5, tzinfo=tz_cest),
        'str_iso': "2021-05-20T15:21:05+02:00",
        'str_iso_sp': "2021-05-20 15:21:05+02:00",
        'str_rfc5322': "Thu, 20 May 2021 15:21:05 +0200",
    },
    {
        'dt': datetime.datetime(2019, 12, 6, 4, 27, 58, tzinfo=tz_mst),
        'str_iso': "2019-12-06T04:27:58-07:00",
        'str_iso_sp': "2019-12-06 04:27:58-07:00",
        'str_rfc5322': "Fri, 06 Dec 2019 04:27:58 -0700",
    },
]


@pytest.mark.parametrize("date", testdates)
@pytest.mark.skipif(archive.tools._dateutil_parse is None,
                    reason="Need dateutil.parser")
def test_date_str_rfc5322_dateutil(date):
    """Test date_str_rfc5322() and conversion back with parse_date() in
    the case that dateutil.parser is available.
    """
    date_string = archive.tools.date_str_rfc5322(date['dt'])
    assert date_string == date['str_rfc5322']
    dt = archive.tools.parse_date(date_string)
    assert dt == date['dt']

@pytest.mark.parametrize("date", testdates)
def test_date_str_rfc5322_no_dateutil(monkeypatch, date):
    """Test date_str_rfc5322() and conversion back with parse_date() in
    the case that dateutil.parser is not available.
    """
    monkeypatch.setattr(archive.tools, "_dateutil_parse", None)
    date_string = archive.tools.date_str_rfc5322(date['dt'])
    assert date_string == date['str_rfc5322']
    dt = archive.tools.parse_date(date_string)
    assert dt == date['dt']

@pytest.mark.parametrize("date", testdates)
@pytest.mark.skipif(archive.tools._dateutil_parse is None,
                    reason="Need dateutil.parser")
def test_date_str_iso_dateutil(date):
    """Test parse_date() with ISO 8601 dates in
    the case that dateutil.parser is available.
    """
    date_string = date['dt'].isoformat()
    assert date_string == date['str_iso']
    dt = archive.tools.parse_date(date_string)
    assert dt == date['dt']

@pytest.mark.parametrize("date", testdates)
def test_date_str_iso_no_dateutil(monkeypatch, date):
    """Test parse_date() with ISO 8601 dates in
    the case that dateutil.parser is not available.
    """
    monkeypatch.setattr(archive.tools, "_dateutil_parse", None)
    date_string = date['dt'].isoformat()
    assert date_string == date['str_iso']
    dt = archive.tools.parse_date(date_string)
    assert dt == date['dt']

@pytest.mark.parametrize("date", testdates)
@pytest.mark.skipif(archive.tools._dateutil_parse is None,
                    reason="Need dateutil.parser")
def test_date_str_iso_blanksep_dateutil(date):
    """Test parse_date() with ISO 8601 dates using a space as separator in
    the case that dateutil.parser is available.
    """
    date_string = date['dt'].isoformat(sep=' ')
    assert date_string == date['str_iso_sp']
    dt = archive.tools.parse_date(date_string)
    assert dt == date['dt']

@pytest.mark.parametrize("date", testdates)
def test_date_str_iso_no_blanksep_dateutil(monkeypatch, date):
    """Test parse_date() with ISO 8601 dates using a space as separator in
    the case that dateutil.parser is not available.
    """
    monkeypatch.setattr(archive.tools, "_dateutil_parse", None)
    date_string = date['dt'].isoformat(sep=' ')
    assert date_string == date['str_iso_sp']
    dt = archive.tools.parse_date(date_string)
    assert dt == date['dt']

@pytest.mark.skipif(archive.tools.gettz is None, reason="Need dateutil.tz")
def test_now_str_dateutil():
    """Test now_str() in the case that dateutil.tz is available.
    """
    date_string = archive.tools.now_str()
    # It doesn't make much sense to inspect the result as it depends
    # on the current date and time.  Just check that parse_date() can
    # make sense of it and returns a datetime that includes a time
    # zone.
    dt = archive.tools.parse_date(date_string)
    assert dt.tzinfo is not None

def test_now_str_no_dateutil(monkeypatch):
    """Test now_str() in the case that dateutil.tz is not available.
    """
    monkeypatch.setattr(archive.tools, "gettz", None)
    date_string = archive.tools.now_str()
    # It doesn't make much sense to inspect the result as it depends
    # on the current date and time.  Just check that parse_date() can
    # make sense of it and returns a datetime that does not include a
    # time zone.
    dt = archive.tools.parse_date(date_string)
    assert dt.tzinfo is None
