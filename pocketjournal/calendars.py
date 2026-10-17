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


def days_of_month(year: int, month: int) -> list[dt.date]:
    if not 1 <= month <= 12:
        raise ValueError(f"month must be 1-12, got {month}")
    return [dt.date(year, month, d)
            for d in range(1, calendar.monthrange(year, month)[1] + 1)]
