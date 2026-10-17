"""Week and month math. Weeks run Sunday to Saturday. Week 1 is the week
containing January 1, and every year has exactly 52 weeks: December days past
week 52 are dropped on purpose (the end of the year is for planning the next)."""
import calendar
import datetime as dt

WEEKS_PER_YEAR = 52


def week_start(year: int, week: int) -> dt.date:
    """The Sunday that starts week `week` (1-52) of `year`."""
    if not 1 <= week <= WEEKS_PER_YEAR:
        raise ValueError(f"week must be 1-{WEEKS_PER_YEAR}, got {week}")
    jan1 = dt.date(year, 1, 1)
    days_since_sunday = (jan1.weekday() + 1) % 7      # Monday is 0 in Python
    return jan1 - dt.timedelta(days=days_since_sunday) + dt.timedelta(weeks=week - 1)


def weeks_of_year(year: int) -> list[tuple[int, dt.date]]:
    """[(week number, Sunday)] for the 52 weeks of the year."""
    return [(w, week_start(year, w)) for w in range(1, WEEKS_PER_YEAR + 1)]


def week_number(day: dt.date) -> int | None:
    """The year-journal week (1-52) that holds `day`, or None for the December
    days past week 52 that the year journal drops. The days before January 1 in
    week 1's Sunday-first week belong to the next year's week 1."""
    for year in (day.year + 1, day.year):
        start = week_start(year, 1)
        if start <= day:
            week = (day - start).days // 7 + 1
            return week if week <= WEEKS_PER_YEAR else None
    return None


def days_of_month(year: int, month: int) -> list[dt.date]:
    if not 1 <= month <= 12:
        raise ValueError(f"month must be 1-12, got {month}")
    return [dt.date(year, month, d)
            for d in range(1, calendar.monthrange(year, month)[1] + 1)]


def month_starts(year: int) -> list[float]:
    """Where each month starts on the year index, in weeks from the top of
    week 1, snapped to half weeks, plus the end (52.0): 13 numbers.

    A month starting on a week's 1st-2nd day snaps to that week's top, 3rd-5th
    to its middle, 6th-7th to the next week. January always starts at 0."""
    week1 = week_start(year, 1)
    starts = [0.0]
    for month in range(2, 13):
        week, day = divmod((dt.date(year, month, 1) - week1).days, 7)
        starts.append(min(float(WEEKS_PER_YEAR),
                          week + (0 if day <= 1 else 0.5 if day <= 4 else 1)))
    return starts + [float(WEEKS_PER_YEAR)]
