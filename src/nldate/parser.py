"""Natural-language date parser."""

from __future__ import annotations

import re
from datetime import date, timedelta

from dateutil import parser as dateutil_parser
from dateutil.relativedelta import relativedelta

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WEEKDAY_NAMES: dict[str, int] = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
    "mon": 0,
    "tue": 1,
    "tues": 1,
    "wed": 2,
    "thu": 3,
    "thur": 3,
    "thurs": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}

MONTH_NAMES: dict[str, int] = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

WORD_TO_NUM: dict[str, int] = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "a": 1,
    "an": 1,
}

UNIT_ALIASES: dict[str, str] = {
    "day": "days",
    "days": "days",
    "week": "weeks",
    "weeks": "weeks",
    "month": "months",
    "months": "months",
    "year": "years",
    "years": "years",
    "yr": "years",
    "yrs": "years",
    "wk": "weeks",
    "wks": "weeks",
    "mo": "months",
    "mos": "months",
    "d": "days",
    "w": "weeks",
    "m": "months",
    "y": "years",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_today(today: date | None) -> date:
    return today if today is not None else date.today()


def _word_to_int(word: str) -> int | None:
    """Convert a word or digit string to an integer, or None if not recognized."""
    word = word.lower().strip()
    if word.isdigit():
        return int(word)
    return WORD_TO_NUM.get(word)


def _parse_number(s: str) -> int | None:
    """Parse a potentially compound number like 'twenty one' or '21'."""
    s = s.strip().lower()
    if s.isdigit():
        return int(s)
    # Try compound: e.g. "twenty one", "twenty-one"
    parts = re.split(r"[\s\-]+", s)
    if len(parts) == 2:
        a = _word_to_int(parts[0])
        b = _word_to_int(parts[1])
        if a is not None and b is not None and b < 10:
            return a + b
    return _word_to_int(s)


def _apply_delta(
    base: date,
    amount: int,
    unit: str,
    direction: int,  # +1 or -1
) -> date:
    """Apply a time delta to a base date."""
    n = amount * direction
    if unit == "days":
        return base + timedelta(days=n)
    if unit == "weeks":
        return base + timedelta(weeks=n)
    if unit == "months":
        return base + relativedelta(months=n)
    if unit == "years":
        return base + relativedelta(years=n)
    return base


def _next_weekday(ref: date, weekday: int) -> date:
    """Return the next occurrence of `weekday` strictly after `ref`."""
    days_ahead = weekday - ref.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return ref + timedelta(days=days_ahead)


def _last_weekday(ref: date, weekday: int) -> date:
    """Return the most recent occurrence of `weekday` strictly before `ref`."""
    days_behind = ref.weekday() - weekday
    if days_behind <= 0:
        days_behind += 7
    return ref - timedelta(days=days_behind)


def _this_weekday(ref: date, weekday: int) -> date:
    """Return this week's occurrence of weekday (could be past or future within the same week)."""
    days_ahead = weekday - ref.weekday()
    return ref + timedelta(days=days_ahead)


# ---------------------------------------------------------------------------
# Segment parsing helpers
# ---------------------------------------------------------------------------

_UNIT_RE = r"(?:years?|yrs?|months?|mos?|weeks?|wks?|days?)"
_NUM_WORD = r"(?:a|an|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty(?:[\s\-]?one)?|thirty(?:[\s\-]?one)?|\d+)"
_SEGMENT_RE = re.compile(
    rf"({_NUM_WORD})\s+({_UNIT_RE})",
    re.IGNORECASE,
)


def _parse_offset_segments(s: str) -> relativedelta | None:
    """
    Parse one or more offset segments like '1 year and 2 months', '3 weeks 4 days', etc.
    Returns a relativedelta if found, else None.
    """
    matches = list(_SEGMENT_RE.finditer(s))
    if not matches:
        return None

    rd = relativedelta()
    for m in matches:
        num = _parse_number(m.group(1))
        # removed unused unit assignment
        # Normalise unit
        raw_unit = m.group(2).lower()
        # Map to canonical
        canonical = None
        for alias, canon in UNIT_ALIASES.items():
            if (
                raw_unit == alias
                or raw_unit == alias.rstrip("s")
                or raw_unit.rstrip("s") == alias.rstrip("s")
            ):
                canonical = canon
                break
        if num is None or canonical is None:
            continue
        if canonical == "days":
            rd += relativedelta(days=num)
        elif canonical == "weeks":
            rd += relativedelta(weeks=num)
        elif canonical == "months":
            rd += relativedelta(months=num)
        elif canonical == "years":
            rd += relativedelta(years=num)

    return rd


def _try_parse_absolute(s: str) -> date | None:
    """
    Try to parse an absolute date string using dateutil.
    Returns None if parsing fails.
    """
    # Normalise ordinal suffixes: 1st -> 1, 2nd -> 2, etc.
    s = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", s, flags=re.IGNORECASE)
    try:
        return dateutil_parser.parse(s, dayfirst=False).date()
    except (ValueError, OverflowError):
        return None


# ---------------------------------------------------------------------------
# Main parse logic
# ---------------------------------------------------------------------------


def parse(s: str, today: date | None = None) -> date:
    """
    Parse a natural-language date string and return a datetime.date.

    Parameters
    ----------
    s:
        A natural-language description of a date, such as:
        - "today", "tomorrow", "yesterday"
        - "next Tuesday", "last Friday", "this Wednesday"
        - "in 3 days", "3 days from now"
        - "5 days before December 1st, 2025"
        - "1 year and 2 months after yesterday"
        - "two weeks from tomorrow"
        - "December 25, 2025"
        - "2025-12-25"
    today:
        Reference date used for relative expressions. Defaults to date.today().

    Returns
    -------
    datetime.date
    """
    ref = _resolve_today(today)
    text = s.strip().lower()

    # ------------------------------------------------------------------
    # 1. Simple keywords
    # ------------------------------------------------------------------
    if text in ("today",):
        return ref
    if text in ("tomorrow",):
        return ref + timedelta(days=1)
    if text in ("yesterday",):
        return ref + timedelta(days=-1)
    if text in ("the day after tomorrow", "day after tomorrow"):
        return ref + timedelta(days=2)
    if text in ("the day before yesterday", "day before yesterday"):
        return ref + timedelta(days=-2)

    # ------------------------------------------------------------------
    # 2. "next/last/this <weekday>"
    # ------------------------------------------------------------------
    m = re.fullmatch(
        r"(next|last|this)\s+(" + "|".join(WEEKDAY_NAMES.keys()) + r")",
        text,
        re.IGNORECASE,
    )
    if m:
        modifier = m.group(1).lower()
        weekday = WEEKDAY_NAMES[m.group(2).lower()]
        if modifier == "next":
            return _next_weekday(ref, weekday)
        if modifier == "last":
            return _last_weekday(ref, weekday)
        # "this"
        return _this_weekday(ref, weekday)

    # ------------------------------------------------------------------
    # 3. Just a weekday name (treat as next occurrence)
    # ------------------------------------------------------------------
    if text in WEEKDAY_NAMES:
        weekday = WEEKDAY_NAMES[text]
        # If today is that weekday, return next week's
        return _next_weekday(ref, weekday)

    # ------------------------------------------------------------------
    # 4. "in <N> <unit>" / "<N> <unit> from now" / "<N> <unit> later"
    # ------------------------------------------------------------------
    m = re.fullmatch(
        rf"in\s+({_NUM_WORD})\s+({_UNIT_RE})",
        text,
        re.IGNORECASE,
    )
    if m:
        num = _parse_number(m.group(1))
        unit = _normalise_unit(m.group(2))
        if num is not None and unit:
            return _apply_delta(ref, num, unit, +1)

    m = re.fullmatch(
        rf"({_NUM_WORD})\s+({_UNIT_RE})\s+(?:from now|from today|later|hence)",
        text,
        re.IGNORECASE,
    )
    if m:
        num = _parse_number(m.group(1))
        unit = _normalise_unit(m.group(2))
        if num is not None and unit:
            return _apply_delta(ref, num, unit, +1)

    # ------------------------------------------------------------------
    # 5. "<N> <unit> ago"
    # ------------------------------------------------------------------
    m = re.fullmatch(
        rf"({_NUM_WORD})\s+({_UNIT_RE})\s+ago",
        text,
        re.IGNORECASE,
    )
    if m:
        num = _parse_number(m.group(1))
        unit = _normalise_unit(m.group(2))
        if num is not None and unit:
            return _apply_delta(ref, num, unit, -1)

    # ------------------------------------------------------------------
    # 6. "<N> <unit> before/after <anchor>"
    #    "<N> <unit> from <anchor>"
    #    "<N> <unit> before/after <anchor>" with compound amounts
    # ------------------------------------------------------------------
    # Pattern: offset BEFORE/AFTER anchor
    before_after = re.compile(
        r"^(.+?)\s+(before|after|from|prior to|following)\s+(.+)$",
        re.IGNORECASE,
    )
    m = before_after.match(text)
    if m:
        offset_str = m.group(1).strip()
        direction_word = m.group(2).strip().lower()
        anchor_str = m.group(3).strip()

        direction = -1 if direction_word in ("before", "prior to") else +1

        rd = _parse_offset_segments(offset_str)
        anchor = _resolve_anchor(anchor_str, ref)

        if rd is not None and anchor is not None:
            return anchor + direction * rd

    # ------------------------------------------------------------------
    # 7. "next/last <month>" or "next/last <month> <day>"
    # ------------------------------------------------------------------
    m = re.fullmatch(
        r"(next|last)\s+(" + "|".join(MONTH_NAMES.keys()) + r")(?:\s+(\d+))?",
        text,
        re.IGNORECASE,
    )
    if m:
        modifier = m.group(1).lower()
        month = MONTH_NAMES[m.group(2).lower()]
        day = int(m.group(3)) if m.group(3) else 1
        year = ref.year
        candidate = date(year, month, day)
        if modifier == "next":
            if candidate <= ref:
                candidate = date(year + 1, month, day)
        else:  # last
            if candidate >= ref:
                candidate = date(year - 1, month, day)
        return candidate

    # ------------------------------------------------------------------
    # 8. "next/last week/month/year"
    # ------------------------------------------------------------------
    m = re.fullmatch(r"(next|last)\s+(week|month|year)", text, re.IGNORECASE)
    if m:
        modifier = m.group(1).lower()
        unit = m.group(2).lower()
        direction = +1 if modifier == "next" else -1
        if unit == "week":
            return ref + timedelta(weeks=direction)
        if unit == "month":
            return ref + relativedelta(months=direction)
        if unit == "year":
            return ref + relativedelta(years=direction)

    # ------------------------------------------------------------------
    # 9. "the <weekday> of next/last/this week"
    # ------------------------------------------------------------------
    m = re.fullmatch(
        r"(?:the\s+)?("
        + "|".join(WEEKDAY_NAMES.keys())
        + r")\s+of\s+(next|last|this)\s+week",
        text,
        re.IGNORECASE,
    )
    if m:
        weekday = WEEKDAY_NAMES[m.group(1).lower()]
        modifier = m.group(2).lower()
        if modifier == "next":
            week_start = ref + timedelta(weeks=1) - timedelta(days=ref.weekday())
        elif modifier == "last":
            week_start = ref - timedelta(weeks=1) - timedelta(days=ref.weekday())
        else:
            week_start = ref - timedelta(days=ref.weekday())
        return week_start + timedelta(days=weekday)

    # ------------------------------------------------------------------
    # 10. "end of next/last/this month/year/week"
    # ------------------------------------------------------------------
    m = re.fullmatch(
        r"(?:the\s+)?end\s+of\s+(next|last|this)\s+(week|month|year)",
        text,
        re.IGNORECASE,
    )
    if m:
        modifier = m.group(1).lower()
        unit = m.group(2).lower()
        if unit == "week":
            start = ref - timedelta(days=ref.weekday())
            if modifier == "next":
                start += timedelta(weeks=1)
            elif modifier == "last":
                start -= timedelta(weeks=1)
            return start + timedelta(days=6)
        if unit == "month":
            base = ref + relativedelta(
                months=(1 if modifier == "next" else -1 if modifier == "last" else 0)
            )
            return (
                date(base.year, base.month, 1)
                + relativedelta(months=1)
                - timedelta(days=1)
            )
        if unit == "year":
            year = ref.year + (
                1 if modifier == "next" else -1 if modifier == "last" else 0
            )
            return date(year, 12, 31)

    # ------------------------------------------------------------------
    # 11. Attempt absolute date parsing (covers ISO, month-day-year, etc.)
    # ------------------------------------------------------------------
    # Normalise ordinal suffixes before passing to dateutil
    normalised = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", s, flags=re.IGNORECASE)
    result = _try_parse_absolute(normalised)
    if result is not None:
        return result

    # ------------------------------------------------------------------
    # 12. Last resort: try dateutil on the original string
    # ------------------------------------------------------------------
    result = _try_parse_absolute(s)
    if result is not None:
        return result

    raise ValueError(f"Unable to parse date string: {s!r}")


# ---------------------------------------------------------------------------
# Helpers used inside parse
# ---------------------------------------------------------------------------


def _normalise_unit(raw: str) -> str | None:
    raw = raw.lower()
    return UNIT_ALIASES.get(raw)


def _resolve_anchor(anchor_str: str, ref: date) -> date | None:
    """Resolve an anchor like 'today', 'tomorrow', 'yesterday', or an absolute date."""
    anchor_str = anchor_str.strip().lower()
    if anchor_str in ("today", "now"):
        return ref
    if anchor_str == "tomorrow":
        return ref + timedelta(days=1)
    if anchor_str == "yesterday":
        return ref - timedelta(days=1)
    # Try recursive parse
    try:
        return parse(anchor_str, today=ref)
    except ValueError:
        return None
