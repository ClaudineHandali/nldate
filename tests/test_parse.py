"""Tests for nldate.parse()."""

from datetime import date

import pytest

from nldate import parse

# Reference date: a Wednesday, January 15, 2025
TODAY = date(2025, 1, 15)


# ---------------------------------------------------------------------------
# 1. Simple keywords
# ---------------------------------------------------------------------------


def test_today() -> None:
    assert parse("today", today=TODAY) == TODAY


def test_tomorrow() -> None:
    assert parse("tomorrow", today=TODAY) == date(2025, 1, 16)


def test_yesterday() -> None:
    assert parse("yesterday", today=TODAY) == date(2025, 1, 14)


def test_day_after_tomorrow() -> None:
    assert parse("the day after tomorrow", today=TODAY) == date(2025, 1, 17)


def test_day_before_yesterday() -> None:
    assert parse("the day before yesterday", today=TODAY) == date(2025, 1, 13)


# ---------------------------------------------------------------------------
# 2. next / last / this weekday
# ---------------------------------------------------------------------------


def test_next_tuesday() -> None:
    # TODAY is Wednesday Jan 15; next Tuesday = Jan 21
    assert parse("next Tuesday", today=TODAY) == date(2025, 1, 21)


def test_next_friday() -> None:
    # TODAY is Wednesday; next Friday = Jan 17
    assert parse("next Friday", today=TODAY) == date(2025, 1, 17)


def test_last_monday() -> None:
    # TODAY is Wednesday Jan 15; last Monday = Jan 13
    assert parse("last Monday", today=TODAY) == date(2025, 1, 13)


def test_last_sunday() -> None:
    # TODAY is Wednesday Jan 15; last Sunday = Jan 12
    assert parse("last Sunday", today=TODAY) == date(2025, 1, 12)


def test_this_wednesday() -> None:
    # TODAY is Wednesday; this Wednesday = same day
    assert parse("this Wednesday", today=TODAY) == date(2025, 1, 15)


def test_this_friday() -> None:
    assert parse("this Friday", today=TODAY) == date(2025, 1, 17)


# ---------------------------------------------------------------------------
# 3. Relative offsets from now
# ---------------------------------------------------------------------------


def test_in_3_days() -> None:
    assert parse("in 3 days", today=TODAY) == date(2025, 1, 18)


def test_in_two_weeks() -> None:
    assert parse("in two weeks", today=TODAY) == date(2025, 1, 29)


def test_in_one_month() -> None:
    assert parse("in 1 month", today=TODAY) == date(2025, 2, 15)


def test_in_one_year() -> None:
    assert parse("in 1 year", today=TODAY) == date(2026, 1, 15)


def test_3_days_from_now() -> None:
    assert parse("3 days from now", today=TODAY) == date(2025, 1, 18)


def test_two_weeks_from_today() -> None:
    assert parse("two weeks from today", today=TODAY) == date(2025, 1, 29)


def test_5_days_ago() -> None:
    assert parse("5 days ago", today=TODAY) == date(2025, 1, 10)


def test_one_month_ago() -> None:
    assert parse("1 month ago", today=TODAY) == date(2024, 12, 15)


def test_two_years_ago() -> None:
    assert parse("2 years ago", today=TODAY) == date(2023, 1, 15)


# ---------------------------------------------------------------------------
# 4. Offset before/after an anchor
# ---------------------------------------------------------------------------


def test_5_days_before_absolute() -> None:
    # "5 days before December 1st, 2025"
    assert parse("5 days before December 1st, 2025", today=TODAY) == date(2025, 11, 26)


def test_5_days_after_absolute() -> None:
    assert parse("5 days after December 1st, 2025", today=TODAY) == date(2025, 12, 6)


def test_two_weeks_from_tomorrow() -> None:
    # tomorrow = Jan 16; two weeks later = Jan 30
    assert parse("two weeks from tomorrow", today=TODAY) == date(2025, 1, 30)


def test_one_year_two_months_after_yesterday() -> None:
    # yesterday = Jan 14, 2025 → +1 year +2 months = March 14, 2026
    assert parse("1 year and 2 months after yesterday", today=TODAY) == date(
        2026, 3, 14
    )


def test_3_weeks_before_today() -> None:
    assert parse("3 weeks before today", today=TODAY) == date(2024, 12, 25)


def test_10_days_from_next_monday() -> None:
    # next Monday from Wed Jan 15 = Jan 20; +10 days = Jan 30
    assert parse("10 days from next Monday", today=TODAY) == date(2025, 1, 30)


def test_prior_to() -> None:
    assert parse("5 days prior to December 1st, 2025", today=TODAY) == date(
        2025, 11, 26
    )


# ---------------------------------------------------------------------------
# 5. Absolute dates
# ---------------------------------------------------------------------------


def test_iso_date() -> None:
    assert parse("2025-12-25") == date(2025, 12, 25)


def test_month_day_year() -> None:
    assert parse("December 25, 2025") == date(2025, 12, 25)


def test_ordinal_date() -> None:
    assert parse("December 1st, 2025") == date(2025, 12, 1)


def test_month_name_day_year() -> None:
    assert parse("March 3rd, 2024") == date(2024, 3, 3)


def test_numeric_slash_date() -> None:
    assert parse("01/15/2025") == date(2025, 1, 15)


def test_abbreviated_month() -> None:
    assert parse("Dec 25, 2025") == date(2025, 12, 25)


# ---------------------------------------------------------------------------
# 6. next/last week, month, year
# ---------------------------------------------------------------------------


def test_next_week() -> None:
    assert parse("next week", today=TODAY) == date(2025, 1, 22)


def test_last_week() -> None:
    assert parse("last week", today=TODAY) == date(2025, 1, 8)


def test_next_month() -> None:
    assert parse("next month", today=TODAY) == date(2025, 2, 15)


def test_last_month() -> None:
    assert parse("last month", today=TODAY) == date(2024, 12, 15)


def test_next_year() -> None:
    assert parse("next year", today=TODAY) == date(2026, 1, 15)


def test_last_year() -> None:
    assert parse("last year", today=TODAY) == date(2024, 1, 15)


# ---------------------------------------------------------------------------
# 7. today parameter defaults to real today when omitted
# ---------------------------------------------------------------------------


def test_today_default_is_real_today() -> None:
    result = parse("today")
    assert result == date.today()


def test_tomorrow_default_today() -> None:
    result = parse("tomorrow")
    assert result == date.today() + __import__("datetime").timedelta(days=1)


# ---------------------------------------------------------------------------
# 8. Invalid input raises ValueError
# ---------------------------------------------------------------------------


def test_invalid_input_raises() -> None:
    with pytest.raises(ValueError):
        parse("this is not a date at all blah blah", today=TODAY)


# ---------------------------------------------------------------------------
# 9. Edge cases
# ---------------------------------------------------------------------------


def test_a_week_from_now() -> None:
    assert parse("a week from now", today=TODAY) == date(2025, 1, 22)


def test_an_year_ago() -> None:
    assert parse("a year ago", today=TODAY) == date(2024, 1, 15)
