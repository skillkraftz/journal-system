"""Year journal page types: the weekly page (`week`) and the two inside
covers (`year_goals`, `year_index`)."""
import calendar
import datetime as dt

from .calendars import WEEKS_PER_YEAR, month_starts
from .draw import Draw
from .page import PageBox, PageContext
from .pagetypes import HEADER_ROWS, draw_header, page_type

DAY_NAMES = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
MONTH_NAMES = [m.upper() for m in calendar.month_abbr[1:]]

# ---- Weekly page settings ---------------------------------------------------
DAY_ROWS = 4                 # grid rows per day (3 mm each)
RAIL_COLS = 2                # width of the date rail, in grid columns
GOAL_ROWS = 8                # rows under the header; the outcome gets what is left

# ---- Cover settings -----------------------------------------------------------
NUMBER_ZONE = 4.5            # mm along a sideways column kept for week numbers:
                             # two digits at label size, plus a little padding
GOALS_HEADER_ROWS = 8        # grid rows of the year-and-goals band
INDEX_COLUMN_ROWS = 22       # grid rows per index column (two fill the page)


def _text_base(row_bottom: float) -> float:
    """Baseline of label-size text sitting in a 3 mm row."""
    return row_bottom + 0.7


def _cap(size_pt: float) -> float:
    """Approximate cap height in mm of Courier Prime at this size."""
    return 0.62 * size_pt * 25.4 / 72


# =============================================================================
# Weekly page
# =============================================================================

@page_type("week")
def week(d: Draw, box: PageBox, ctx: PageContext) -> None:
    """One week, Sunday to Saturday: header (month by the spine, the page
    number, which is the week number, at the outer corner), goal, seven days,
    outcome.

    Quiet by design: light gray writing lines, thin black separators, the
    dates in a narrow rail at the outer edge so a post-it note can cover the
    page and the dates still show. Weekends get a faint tint in the rail, the
    1st of a month gets a black separator and a month label."""
    s, g = ctx.settings, box.grid_area()
    if ctx.date is None:
        raise ValueError("the week page needs a date (use `each: week`)")
    days = [ctx.date + dt.timedelta(i) for i in range(7)]
    header_rows, goal_rows = HEADER_ROWS, GOAL_ROWS
    outcome_rows = g.rows - header_rows - goal_rows - 7 * DAY_ROWS
    cell = g.cell
    row = lambda n: g.y1 - n * cell                  # y of the line n rows from the top
    days_top, outcome_top = row(header_rows + goal_rows), row(header_rows + goal_rows + 7 * DAY_ROWS)

    # The rail sits on the outer edge: right on right-hand pages.
    rail_w = RAIL_COLS * cell
    rail_x0 = g.x1 - rail_w if box.is_right else g.x0
    rail_x1 = rail_x0 + rail_w
    rules_x0, rules_x1 = (g.x0, rail_x0) if box.is_right else (rail_x1, g.x1)

    def section_line(y):
        d.line(g.x0, y, g.x1, y, s.structure_weight)

    def rules(top, rows, closed=False):
        for k in range(1, rows + (1 if closed else 0)):
            d.line(rules_x0, top - k * cell, rules_x1, top - k * cell,
                   s.rule_weight, s.rule_gray)

    draw_header(d, box, ctx, _month_label(days))
    section_line(row(header_rows))

    # goal
    rules(row(header_rows), goal_rows)
    section_line(days_top)
    # outcome
    rules(outcome_top, outcome_rows, closed=True)

    # days: tint first, then lines, then labels
    for i, day in enumerate(days):
        top = days_top - i * DAY_ROWS * cell
        if day.weekday() >= 5:
            d.fill_rect(rail_x0, top - DAY_ROWS * cell, rail_w, DAY_ROWS * cell, s.tint_gray)
        if i:
            if day.day == 1:
                section_line(top)
            else:
                d.line(g.x0, top, g.x1, top, s.rule_weight, s.separator_gray)
        rules(top, DAY_ROWS)
    section_line(outcome_top)

    edge = rail_x0 if box.is_right else rail_x1
    d.line(edge, row(header_rows), edge, g.y0, s.structure_weight)
    cx = (rail_x0 + rail_x1) / 2
    for i, day in enumerate(days):
        _rail_label(d, s, cx, days_top - i * DAY_ROWS * cell, day)
    for name, top, rows in (("GOAL", row(header_rows), goal_rows),
                            ("OUTCOME", outcome_top, outcome_rows)):
        mid = top - rows * cell / 2
        d.text(cx + _cap(s.font_label) / 2, mid, name, s.font_label,
               gray=0.4, anchor="c", rotate=90)


def _month_label(days) -> str:
    """"JULY", or "JUN / JUL" when the week spans two months."""
    months = list(dict.fromkeys(day.month for day in days))
    if len(months) == 1:
        return calendar.month_name[months[0]].upper()
    return " / ".join(MONTH_NAMES[m - 1] for m in months)


def _rail_label(d: Draw, s, cx: float, top: float, day: dt.date) -> None:
    """Weekday, date, and (on the 1st) the month, stacked in the rail."""
    cell = s.grid
    d.text(cx, _text_base(top - cell), DAY_NAMES[(day.weekday() + 1) % 7],
           s.font_label, gray=0.4, anchor="c")
    d.text(cx, top - 2.5 * cell - _cap(9) / 2, str(day.day), 9, bold=True, anchor="c")
    if day.day == 1:
        d.text(cx, _text_base(top - 4 * cell), MONTH_NAMES[day.month - 1],
               s.font_label, anchor="c")


# =============================================================================
# Covers: sideways columns
#
# Both covers are meant to be read with the book turned a quarter turn
# clockwise: text runs upward, week strips are 3 mm bands side by side, and
# the first column (weeks 1-26) is the lower half of the page.
# =============================================================================

def _sideways_number(d: Draw, s, cx: float, y: float, text: str, bold=False) -> None:
    """Centered at (cx, y), reading upward."""
    d.text(cx + _cap(s.font_label) / 2, y, text, s.font_label, bold=bold,
           anchor="c", rotate=90)


@page_type("year_goals")
def year_goals(d: Draw, box: PageBox, ctx: PageContext) -> None:
    """Inside front cover: the year and its goals on top, then all 52 weeks in
    two sideways columns (Q1-Q2 below, Q3-Q4 above), each with a week number
    and a writing line for how it went. No labels on those lines.

    The 28 strips per column (13 weeks + a heading row, twice) share the
    content width, so the pitch is 2.96 mm: as close to 3 mm as fits."""
    s, g = ctx.settings, box.grid_area()
    year = str(ctx.year) if ctx.year is not None else "20__"
    d.text(g.x0, g.y1 - 2.4, year, 11, bold=True)
    d.text(g.x0 + len(year) * 11 * 0.6 * 25.4 / 72 + 2.0, g.y1 - 2.4, "goals",
           s.font_label, gray=0.4)
    for k in range(2, GOALS_HEADER_ROWS):
        d.line(g.x0, g.y1 - k * g.cell, g.x1, g.y1 - k * g.cell, s.rule_weight, s.rule_gray)
    band_bottom = g.y1 - GOALS_HEADER_ROWS * g.cell
    d.line(g.x0, band_bottom, g.x1, band_bottom, s.structure_weight)

    left, right = box.x0, box.x1
    pitch = (right - left) / 28
    height = (band_bottom - g.y0) / 2
    cols = [(g.y0, ["Q1", *range(1, 14), "Q2", *range(14, 27)]),
            (g.y0 + height, ["Q3", *range(27, 40), "Q4", *range(40, 53)])]
    for y_a, labels in cols:
        y_b = y_a + height
        for k in range(29):
            d.line(left + k * pitch, y_a, left + k * pitch, y_b, s.rule_weight, s.rule_gray)
        for k, label in enumerate(labels):
            cx = left + (k + 0.5) * pitch
            if isinstance(label, str):                  # quarter heading row
                for edge in (k, k + 1):
                    d.line(left + edge * pitch, y_a, left + edge * pitch, y_b, s.structure_weight)
                _sideways_number(d, s, cx, y_a + NUMBER_ZONE / 2, label, bold=True)
            else:
                _sideways_number(d, s, cx, y_a + NUMBER_ZONE / 2, str(label))
        d.line(left, y_a + NUMBER_ZONE, right, y_a + NUMBER_ZONE, s.structure_weight)
        d.rect(left, y_a, right - left, height, s.structure_weight)


@page_type("year_index")
def year_index(d: Draw, box: PageBox, ctx: PageContext) -> None:
    """Inside back cover: an index of the year. Two sideways columns of 26 week
    boxes (3 mm each); beside them open space divided only where months
    change (snapped to half weeks), with a small month label in each part."""
    if ctx.year is None:
        raise ValueError("the year index needs a year")
    s, g = ctx.settings, box.grid_area()
    per_col = WEEKS_PER_YEAR // 2
    left = g.x0 + (g.x1 - g.x0 - per_col * g.cell) / 2     # center the 26 strips
    pitch, height = g.cell, INDEX_COLUMN_ROWS * g.cell
    starts = month_starts(ctx.year)
    for c in range(2):
        y_a, lo = g.y0 + c * height, c * per_col
        y_b, open_y = y_a + height, y_a + NUMBER_ZONE
        for k in range(per_col + 1):                         # week box lines
            d.line(left + k * pitch, y_a, left + k * pitch, open_y, s.rule_weight, s.rule_gray)
        for k in range(per_col):
            _sideways_number(d, s, left + (k + 0.5) * pitch, y_a + NUMBER_ZONE / 2,
                             str(lo + k + 1))
        for m in range(12):
            a, b = max(starts[m], lo), min(starts[m + 1], lo + per_col)
            if b <= a:
                continue
            x = left + (a - lo) * pitch
            if lo + 1 <= a <= lo + per_col - 1:              # closer to the outline, it would double it
                d.line(x, open_y, x, y_b, s.structure_weight)
            if b - a >= 1:                                   # no label on half-week slivers
                d.text(x + _cap(s.font_label) + 0.8, open_y + 1.5, MONTH_NAMES[m],
                       s.font_label, gray=0.4, rotate=90)
        d.line(left, open_y, left + per_col * pitch, open_y, s.structure_weight)
        d.rect(left, y_a, per_col * pitch, height, s.structure_weight)
