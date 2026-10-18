"""Monthly journal page types: the tracker (inside front cover), the daily Good
Time Journal page, the weekly reflection, the month-end pages and a pocket
quick reference (inside back cover, a first draft)."""
import calendar
import datetime as dt

import math

from reportlab.lib.units import mm as MM
from reportlab.pdfbase import pdfmetrics

from . import calendars
from .draw import Draw
from .page import PageBox, PageContext
from .pagetypes import HEADER_ROWS, draw_header, page_type
from .yearpages import DAY_NAMES, MONTH_NAMES, _cap, _text_base

# ---- Tracker settings -----------------------------------------------------------
# Columns, left to right: sleep, date, weekday letter, the habits, appointments.
HABITS = 12                  # habit columns; appointments get what is left
NAME_ROWS = 7                # grid rows above the days for vertical habit names
TIME_ROWS = 5                # grid rows below the days for vertical times
TRACKER_DAYS = 31            # rows reserved for days, so every month lines up
TRACKER_FONT = 6.0           # day numbers must fit a 3 mm column
WEEKEND_TINT = 0.965         # very faint gray behind weekend rows (None = off)

# ---- Daily page settings ----------------------------------------------------------
COVER_TITLE_ROWS = 2         # rows the quick reference keeps for its title
ENTRIES = 3                  # activity entries per day
ENTRY_ROWS = 6               # grid rows per entry
WRITE_COLS = 15              # grid columns of writing area; two 6-column dials follow
DIAL_COLS = 6
DIAL_RADIUS = 6.0            # mm
DIAL_SHADE = 0.85            # the negative half of the energy dial

# ---- Weekly reflection settings: lines under each prompt -----------------------------
# Spare rows go to the first prompt.
REFLECTION = [               # (prompt, writing rows)
    ("what engaged and energized me", 8),
    ("what drained me", 7),
    ("what surprised me", 6),
    ("top entry", 5),
    ("low entry", 5),
    ("one thing to do more of", 2),
    ("one thing to do less of", 2),
]
AEIOU = ["Activities", "Environments", "Interactions", "Objects", "Users"]
AEIOU_PROMPTS = ("top entry", "low entry")        # these get the AEIOU rows

# ---- Quick reference text (inside back cover; edit freely) ----------------------------
QUICK_REFERENCE = [
    ("LOG A DAY", [
        "Up to 3 entries: what you did, in a few words.",
        "Engagement: mark the dial from LO to HI.",
        "Flow: tick the box if time disappeared.",
        "Energy: mark NEG, 0 or POS. Shaded = drained.",
        "Journal lines: anything else worth keeping."]),
    ("TRACK THE MONTH (front cover)", [
        "Hours slept on the left, a habit per column, appointments on the "
        "right, times along the bottom."]),
    ("REFLECT (page after each Saturday)", [
        "Read the week back. Note what engaged and energized you, what "
        "drained you, what surprised you.",
        "Pick a top and a low entry and write its AEIOU.",
        "End with one thing to do more of and one to do less of."]),
    ("MONTH END", [
        "Write the patterns and takeaways. Move leftovers to the someday list."]),
    ("AEIOU: ask it of an entry", [
        "A Activities: what was I doing? Structured or not, "
        "a role I was playing?",
        "E Environments: where was I? How did it look and feel?",
        "I Interactions: with whom or what? New or familiar, "
        "formal or casual?",
        "O Objects: what things, tools or devices was I using?",
        "U Users: who else was there?"]),
]
QUICK_BODY_GRAY = 0.15


def _month_of(ctx: PageContext) -> int:
    if ctx.year is None or ctx.month is None:
        raise ValueError("this page needs a year and a month")
    return ctx.month


def _month_title(ctx: PageContext) -> str:
    return f"{calendar.month_name[_month_of(ctx)].upper()} {ctx.year}"


def _rules(d: Draw, s, g, x0: float, x1: float, row_from: int, row_to: int) -> None:
    """Light writing lines on the bottoms of rows `row_from` .. `row_to - 1`
    (row 0 is the top row of the grid)."""
    for r in range(row_from, row_to):
        y = g.y1 - (r + 1) * g.cell
        d.line(x0, y, x1, y, s.rule_weight, s.rule_gray)


# =============================================================================
# Inside front cover: the monthly tracker
# =============================================================================

@page_type("monthly_tracker")
def monthly_tracker(d: Draw, box: PageBox, ctx: PageContext) -> None:
    """Day rows (date and weekday letter), habit columns with room above for
    vertical names and below for vertical times, appointment lines to the
    right, and an offset half-row column on the left for hours of sleep.

    The grid is always laid out for 31 days from the top; a shorter month just
    has fewer rows, so the habit columns and the times strip stay put."""
    title = _month_title(ctx)
    s, g = ctx.settings, box.grid_area()
    if g.rows < 1 + NAME_ROWS + TRACKER_DAYS + TIME_ROWS:
        raise ValueError("the tracker does not fit this page; lower NAME_ROWS or TIME_ROWS")
    days = calendars.days_of_month(ctx.year, ctx.month)
    cell, half = g.cell, g.cell / 2
    SLEEP, DATE, WDAY, H0 = 0, 1, 2, 3
    A0 = H0 + HABITS                                   # first appointment column
    x = g.x
    zone_top = g.y1 - cell                             # below the title row
    top = zone_top - NAME_ROWS * cell                  # top of day 1
    bottom = top - len(days) * cell                    # bottom of the last day
    times_top = g.y0 + TIME_ROWS * cell

    d.text(g.x0, g.y1 - 2.4, title, s.font_heading, bold=True)

    # weekend tint: faint across the whole row, stronger behind date and weekday
    for i, day in enumerate(days):
        if day.weekday() >= 5:
            if WEEKEND_TINT is not None:
                d.fill_rect(x(DATE), top - (i + 1) * cell, g.x1 - x(DATE), cell, WEEKEND_TINT)
            d.fill_rect(x(DATE), top - (i + 1) * cell, 2 * cell, cell, s.tint_gray)

    # horizontal lines: one per row, a darker one after every Saturday
    for i in range(len(days) + 1):
        y = top - i * cell
        sat = i and days[i - 1].weekday() == 5
        d.line(x(DATE), y, g.x1, y, s.rule_weight,
               s.separator_gray if sat and i < len(days) else s.rule_gray)
    # the sleep column runs half a row lower, so each cell sits between two days
    for i in range(len(days) + 1):
        y = top - half - i * cell
        d.line(g.x0, y, x(DATE), y, s.rule_weight, s.rule_gray)

    # vertical lines: habit columns run from the names to the bottom of the page
    for k in range(H0, A0 + 1):
        d.line(x(k), g.y0, x(k), zone_top, s.rule_weight, s.rule_gray)
    for k in (DATE + 1, WDAY + 1):
        d.line(x(k), top, x(k), bottom, s.rule_weight, s.rule_gray)
    d.line(x(H0), zone_top, x(A0), zone_top, s.rule_weight, s.rule_gray)

    # structure: the day grid, the sleep column, the times strip
    d.rect(x(DATE), bottom, (A0 - DATE) * cell, len(days) * cell, s.structure_weight)
    d.rect(x(SLEEP), bottom - half, cell, len(days) * cell, s.structure_weight)
    d.rect(x(H0), g.y0, HABITS * cell, TIME_ROWS * cell, s.structure_weight)

    # labels
    for i, day in enumerate(days):
        base = top - (i + 1) * cell + (cell - _cap(TRACKER_FONT)) / 2
        d.text(x(DATE) + cell / 2, base, str(day.day), TRACKER_FONT, anchor="c")
        d.text(x(WDAY) + cell / 2, base, "SMTWTFS"[(day.weekday() + 1) % 7],
               TRACKER_FONT, gray=0.4, anchor="c")
    d.text(x(SLEEP) + cell / 2 + _cap(s.font_label) / 2, top + 1.0, "hrs sleep",
           s.font_label, gray=0.4, rotate=90)
    d.text(x(A0) + 0.8, top + 0.7, "appointments", s.font_label, gray=0.4)
    # habits and times share the weekday column: what is done daily above,
    # when each is scheduled below
    d.text(x(WDAY) + cell / 2 + _cap(s.font_label) / 2, top + 1.0, "habits",
           s.font_label, gray=0.4, rotate=90)
    times_w = pdfmetrics.stringWidth("times", s.font_regular, s.font_label) / MM
    d.text(x(WDAY) + cell / 2 + _cap(s.font_label) / 2, times_top - 1.0 - times_w, "times",
           s.font_label, gray=0.4, rotate=90)


# =============================================================================
# Daily page: Good Time Journal
# =============================================================================

def _dial(d: Draw, s, cx: float, base: float, kind: str) -> None:
    """A half-circle dial to mark by hand, with its labels. `base` is the y of
    the flat edge. kind: "engage" (LO to HI, plus a Flow checkbox) or
    "energy" (NEG, 0, POS; the negative half is shaded)."""
    r = DIAL_RADIUS
    if kind == "energy":
        d.wedge(cx, base, r, 90, 90, DIAL_SHADE)           # upper left quarter
    d.arc(cx, base, r, 0, 180, s.structure_weight)
    d.line(cx - r - 0.4, base, cx + r + 0.4, base, s.structure_weight)
    for k in range(5):                                      # ticks at 0, 45 ... 180
        a = k * 45
        ux, uy = math.cos(math.radians(a)), math.sin(math.radians(a))
        inner = r * (0.7 if k % 2 == 0 else 0.84)
        d.line(cx + inner * ux, base + inner * uy, cx + r * ux, base + r * uy,
               s.rule_weight, 0.3)
    if kind == "energy":
        d.line(cx, base, cx, base + r, s.rule_weight, 0.3)
    d.circle(cx, base, 0.8, 1.0)                           # pivot for a hand-drawn needle
    d.circle(cx, base, 0.8, 0.0, s.rule_weight)

    lo, hi, name = ("LO", "HI", "Engagement") if kind == "engage" else ("NEG", "POS", "Energy")
    label = s.font_label
    d.text(cx - r, base - 2.6, lo, label, gray=0.4, anchor="c")
    d.text(cx + r, base - 2.6, hi, label, gray=0.4, anchor="c")
    d.text(cx, base - 5.4, name, label, gray=0.4, anchor="c")
    if kind == "energy":
        d.text(cx, base + r + 0.7, "0", label, gray=0.4, anchor="c")
    else:
        box_w, y = 2.2, base + r + 1.3
        d.rect(cx + r - box_w, y, box_w, box_w, s.structure_weight)
        d.text(cx + r - box_w - 0.8, y + 0.4, "Flow", label, gray=0.4, anchor="r")


@page_type("daily")
def daily(d: Draw, box: PageBox, ctx: PageContext) -> None:
    """A Good Time Journal day: the date in the header, three activity entries (a short
    writing area, the Engagement dial with a Flow checkbox, the Energy dial),
    then 3 mm journal lines for the rest of the page."""
    if ctx.date is None:
        raise ValueError("the daily page needs a date (use `each: day`)")
    s, g = ctx.settings, box.grid_area()
    cell = g.cell
    row = lambda n: g.y1 - n * cell                      # y of the line n rows from the top

    day = ctx.date
    draw_header(d, box, ctx,
                f"{DAY_NAMES[(day.weekday() + 1) % 7]} {MONTH_NAMES[day.month - 1]} {day.day}")

    writing_x1 = g.x(WRITE_COLS)
    engage_cx = g.x(WRITE_COLS + DIAL_COLS / 2)
    energy_cx = g.x(WRITE_COLS + DIAL_COLS * 1.5)
    for n in range(ENTRIES):
        first = HEADER_ROWS + n * ENTRY_ROWS
        bottom = row(first + ENTRY_ROWS)
        d.line(g.x0, row(first), g.x1, row(first), s.structure_weight)
        _rules(d, s, g, g.x0, writing_x1, first, first + ENTRY_ROWS)
        d.line(writing_x1, bottom, writing_x1, row(first), s.rule_weight, s.separator_gray)
        d.text(g.x0 + 0.8, _text_base(row(first + 1)), "Activity:", s.font_label, gray=0.4)
        d.text(g.x0 + 0.8, _text_base(row(first + 3)), "Reflections:", s.font_label, gray=0.4)
        base = bottom + 7.0
        _dial(d, s, engage_cx, base, "engage")
        _dial(d, s, energy_cx, base, "energy")
    journal_top = HEADER_ROWS + ENTRIES * ENTRY_ROWS
    d.line(g.x0, row(journal_top), g.x1, row(journal_top), s.structure_weight)
    _rules(d, s, g, g.x0, g.x1, journal_top, g.rows)
    d.line(g.x0, row(HEADER_ROWS), g.x1, row(HEADER_ROWS), s.structure_weight)


# =============================================================================
# Weekly reflection, month end
# =============================================================================

@page_type("week_reflection")
def week_reflection(d: Draw, box: PageBox, ctx: PageContext) -> None:
    """Placed after a Saturday. ctx.date is the week's Sunday, ctx.week its
    year-journal number (blank for the December days the year journal drops).
    Prompts are small gray labels over writing lines; the top and low entries
    get one line per AEIOU letter."""
    if ctx.date is None:
        raise ValueError("the reflection page needs a date (use `after_saturday`)")
    s, g = ctx.settings, box.grid_area()
    cell = g.cell
    row = lambda n: g.y1 - n * cell

    draw_header(d, box, ctx, f"WEEK {ctx.week}" if ctx.week else "WEEK")

    sections = list(REFLECTION)
    used = HEADER_ROWS + sum(1 + n + (len(AEIOU) - n if p in AEIOU_PROMPTS else 0)
                                   for p, n in sections)
    sections[0] = (sections[0][0], sections[0][1] + g.rows - used)
    r = HEADER_ROWS
    d.line(g.x0, row(r), g.x1, row(r), s.structure_weight)
    for prompt, lines in sections:
        n = len(AEIOU) if prompt in AEIOU_PROMPTS else lines
        d.text(g.x0 + 0.8, _text_base(row(r + 1)), prompt, s.font_label, gray=0.4)
        if prompt in AEIOU_PROMPTS:
            for k, word in enumerate(AEIOU):
                d.text(g.x0 + 0.8, _text_base(row(r + 2 + k)), word[0], s.font_label, bold=True)
                d.text(g.x0 + 0.8 + pdfmetrics.stringWidth(word[0], s.font_bold, s.font_label) / MM,
                       _text_base(row(r + 2 + k)), word[1:], s.font_label, gray=0.65)
        _rules(d, s, g, g.x0, g.x1, r, r + 1 + n)
        r += 1 + n
        d.line(g.x0, row(r), g.x1, row(r), s.structure_weight)


@page_type("month_review")
def month_review(d: Draw, box: PageBox, ctx: PageContext) -> None:
    """Month end: patterns, then takeaways, as two halves of writing lines."""
    s, g = ctx.settings, box.grid_area()
    row = lambda n: g.y1 - n * g.cell
    draw_header(d, box, ctx, f"{calendar.month_name[_month_of(ctx)].upper()} REVIEW")
    r = HEADER_ROWS
    half = (g.rows - r) // 2
    for name, rows in (("patterns", half), ("takeaways", g.rows - r - half)):
        d.line(g.x0, row(r), g.x1, row(r), s.structure_weight)
        d.text(g.x0 + 0.8, _text_base(row(r + 1)), name, s.font_label, gray=0.4)
        _rules(d, s, g, g.x0, g.x1, r, r + rows)
        r += rows


@page_type("someday")
def someday(d: Draw, box: PageBox, ctx: PageContext) -> None:
    """Notes and a someday list: a dot and a writing line on every row."""
    s, g = ctx.settings, box.grid_area()
    draw_header(d, box, ctx, "NOTES / SOMEDAY")
    d.line(g.x0, g.y1 - HEADER_ROWS * g.cell, g.x1,
           g.y1 - HEADER_ROWS * g.cell, s.structure_weight)
    _rules(d, s, g, g.x0, g.x1, HEADER_ROWS, g.rows)
    for r in range(HEADER_ROWS, g.rows):
        d.circle(g.x0 + 1.2, g.y1 - (r + 0.5) * g.cell, 0.4, s.dot_gray)


# =============================================================================
# Inside back cover: quick reference (first draft)
# =============================================================================

def _wrap(text: str, font: str, size: float, width: float) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if line and pdfmetrics.stringWidth(trial, font, size) / MM > width:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + [line]


@page_type("quick_reference")
def quick_reference(d: Draw, box: PageBox, ctx: PageContext) -> None:
    """How to log, track, reflect, and the AEIOU prompts, so the book works
    alone. The text is QUICK_REFERENCE at the top of this file."""
    s, g = ctx.settings, box.grid_area()
    size, indent = s.font_label, 2.0
    d.text(g.x0, g.y1 - 2.4, "QUICK REFERENCE", s.font_heading, bold=True)
    r = COVER_TITLE_ROWS
    for title, items in QUICK_REFERENCE:
        d.line(g.x0, g.y1 - r * g.cell, g.x1, g.y1 - r * g.cell, s.structure_weight)
        d.text(g.x0, _text_base(g.y1 - (r + 1) * g.cell), title, size, bold=True)
        r += 1
        for item in items:
            for k, line in enumerate(_wrap(item, s.font_regular, size,
                                           g.x1 - g.x0 - indent - (0 if item[1] != ' ' else 2.8))):
                d.text(g.x0 + indent + (0 if k == 0 or item[1] != ' ' else 2.8),
                       _text_base(g.y1 - (r + 1) * g.cell), line, size,
                       gray=QUICK_BODY_GRAY)
                r += 1
        r += 1
    if r - 1 > g.rows:
        raise ValueError(f"the quick reference needs {r - 1} rows but a page has {g.rows}")
