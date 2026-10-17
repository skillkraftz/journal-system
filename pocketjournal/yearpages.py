"""Year journal page types: the weekly page (`week`) and the two inside
covers (`year_goals`, `year_index`)."""
import calendar
import datetime as dt

from .calendars import WEEKS_PER_YEAR, month_starts
from .draw import Draw
from .page import PageBox, PageContext
from .pagetypes import page_type

DAY_NAMES = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
MONTH_NAMES = [m.upper() for m in calendar.month_abbr[1:]]

# ---- Weekly page settings ---------------------------------------------------
DAY_ROWS = 4                 # grid rows per day (3 mm each)
RAIL_COLS = 2                # width of the date rail, in grid columns
# Rows above the days, per style: (header, goal). Outcome gets what is left.
WEEK_STYLES = {"rail": (2, 7), "corner": (2, 7), "strip": (4, 6)}

# ---- Cover settings -----------------------------------------------------------
NUMBER_ZONE = 6.0            # mm along a sideways column kept for week numbers
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
    """One week, Sunday to Saturday: header, goal, seven days, outcome.

    Quiet by design: light gray writing lines, thin black separators, day
    labels as small text instead of boxes. Weekends get a faint tint (or bold
    label), the 1st of a month gets a black separator and a month label.

    params: style - how the days are labeled, so a post-it note can cover the
        page and the dates still show:
      rail    (default) week dates in a narrow rail at the outer edge
      corner  small label in the corner of each day, no rail
      strip   all seven dates in a strip under the header
    """
    s, g = ctx.settings, box.grid_area()
    style = ctx.params.get("style", "rail")
    if style not in WEEK_STYLES:
        raise ValueError(f"week style {style!r}; use one of {', '.join(WEEK_STYLES)}")
    if ctx.date is None:
        raise ValueError("the week page needs a date (use `each: week`)")
    days = [ctx.date + dt.timedelta(i) for i in range(7)]
    header_rows, goal_rows = WEEK_STYLES[style]
    outcome_rows = g.rows - header_rows - goal_rows - 7 * DAY_ROWS
    cell = g.cell
    row = lambda n: g.y1 - n * cell                  # y of the line n rows from the top
    days_top, outcome_top = row(header_rows + goal_rows), row(header_rows + goal_rows + 7 * DAY_ROWS)

    # The rail sits on the outer edge: right on right-hand pages.
    rail_w = RAIL_COLS * cell if style == "rail" else 0.0
    rail_x0 = g.x1 - rail_w if box.is_right else g.x0
    rail_x1 = rail_x0 + rail_w
    rules_x0, rules_x1 = (g.x0, rail_x0) if box.is_right else (rail_x1, g.x1)

    def section_line(y):
        d.line(g.x0, y, g.x1, y, s.structure_weight)

    def rules(top, rows, closed=False):
        for k in range(1, rows + (1 if closed else 0)):
            d.line(rules_x0, top - k * cell, rules_x1, top - k * cell,
                   s.rule_weight, s.rule_gray)

    _week_header(d, s, g, row, days, ctx, style)
    section_line(row(header_rows))

    # goal
    rules(row(header_rows), goal_rows)
    section_line(days_top)
    # outcome
    rules(outcome_top, outcome_rows, closed=True)

    # days: tint first, then lines, then labels
    for i, day in enumerate(days):
        top = days_top - i * DAY_ROWS * cell
        weekend, first = day.weekday() >= 5, day.day == 1
        if weekend and style == "rail":
            d.fill_rect(rail_x0, top - DAY_ROWS * cell, rail_w, DAY_ROWS * cell, s.tint_gray)
        if i:
            if first:
                section_line(top)
            else:
                d.line(g.x0, top, g.x1, top, s.rule_weight, s.separator_gray)
        rules(top, DAY_ROWS)
    section_line(outcome_top)

    if style == "rail":
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
    else:
        for name, top in (("goal", row(header_rows)), ("outcome", outcome_top)):
            d.text(g.x0 + 0.8, _text_base(top - cell), name, s.font_label, gray=0.4)
        for i, day in enumerate(days):
            top = days_top - i * DAY_ROWS * cell
            name = DAY_NAMES[(day.weekday() + 1) % 7]
            label = name if style == "strip" else (
                f"{MONTH_NAMES[day.month - 1]} 1" if day.day == 1 else f"{name} {day.day}")
            weekend = day.weekday() >= 5
            d.text(g.x0 + 0.8, _text_base(top - cell), label, s.font_label,
                   bold=weekend, gray=0.0 if weekend else 0.4)


def _rail_label(d: Draw, s, cx: float, top: float, day: dt.date) -> None:
    """Weekday, date, and (on the 1st) the month, stacked in the rail."""
    cell = s.grid
    d.text(cx, _text_base(top - cell), DAY_NAMES[(day.weekday() + 1) % 7],
           s.font_label, gray=0.4, anchor="c")
    d.text(cx, top - 2.5 * cell - _cap(9) / 2, str(day.day), 9, bold=True, anchor="c")
    if day.day == 1:
        d.text(cx, _text_base(top - 4 * cell), MONTH_NAMES[day.month - 1],
               s.font_label, anchor="c")


def _week_header(d: Draw, s, g, row, days, ctx: PageContext, style: str) -> None:
    """Week number and month(s) on top; a date range below (or the date strip)."""
    months = list(dict.fromkeys(day.month for day in days))
    if len(months) == 1:
        month_text = calendar.month_name[months[0]].upper()
    else:
        month_text = " / ".join(MONTH_NAMES[m - 1] for m in months)
    year = str(ctx.year if ctx.year is not None else days[-1].year)
    base = _text_base(row(1))
    d.text(g.x0, base, f"WEEK {ctx.week}", s.font_heading, bold=True)
    if style != "strip":
        d.text(g.x1, base, month_text, s.font_heading, bold=True, anchor="r")
        first, last = days[0], days[-1]
        span = f"{calendar.month_abbr[first.month]} {first.day} - " \
               f"{calendar.month_abbr[last.month]} {last.day}"
        d.text(g.x0, _text_base(row(2)), span, s.font_label, gray=0.4)
        d.text(g.x1, _text_base(row(2)), year, s.font_label, gray=0.4, anchor="r")
        return

    d.text(g.x1, base, f"{month_text} {year}", s.font_heading, bold=True, anchor="r")
    col_w = (g.x1 - g.x0) / 7
    for i, day in enumerate(days):
        x0, cx = g.x0 + i * col_w, g.x0 + (i + 0.5) * col_w
        if day.weekday() >= 5:
            d.fill_rect(x0, row(4), col_w, 3 * g.cell, s.tint_gray)
        if day.day == 1 and i:
            d.line(x0, row(4), x0, row(1), s.structure_weight)
        d.text(cx, _text_base(row(2)), DAY_NAMES[i], s.font_label, gray=0.4, anchor="c")
        d.text(cx, row(3) + 0.5, str(day.day),
               9, bold=True, anchor="c")
        if day.day == 1:
            d.text(cx, _text_base(row(4)), MONTH_NAMES[day.month - 1], s.font_label,
                   anchor="c")


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
    and a writing line for how it went.

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
                d.text(cx + _cap(s.font_label) / 2, y_a + NUMBER_ZONE + 1.5, "how it went",
                       s.font_label, gray=0.4, rotate=90)
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
            if a > lo:                                       # else the outline is the line
                d.line(x, open_y, x, y_b, s.structure_weight)
            if b - a >= 1:                                   # no label on half-week slivers
                d.text(x + _cap(s.font_label) + 0.8, open_y + 1.5, MONTH_NAMES[m],
                       s.font_label, gray=0.4, rotate=90)
        d.line(left, open_y, left + per_col * pitch, open_y, s.structure_weight)
        d.rect(left, y_a, per_col * pitch, height, s.structure_weight)
