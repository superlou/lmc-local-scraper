from datetime import date

from events_ai.humanize import long_date


def test_humanize_long_date():
    assert long_date(date(2026, 1, 1)) == "January 1st, 2026"
    assert long_date(date(1983, 7, 2)) == "July 2nd, 1983"
    assert long_date(date(1983, 12, 12)) == "December 12th, 1983"
    assert long_date(date(2010, 10, 10)) == "October 10th, 2010"
    assert long_date(date(2001, 3, 23)) == "March 23rd, 2001"
