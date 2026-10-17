#!/usr/bin/env python3
"""
Pocket notebook templates, drawn as margin-free PNGs. Needs: pip install pillow

Every image is exactly 7.5" x 10" (a letter page inside 0.5" margins), so it
fills one page of the Word document, same as the monthly tracker.

Usage: python3 pocket_templates.py 2027   (the year is optional)

Makes:
  year-cover.png        inside front cover of the year book (week outcomes)
  year-index-YYYY.png   inside back cover of the year book (month map)
  weekly-YYYY/          52 weekly pages, week-01.png to week-52.png (+ .zip)
  daily-good-time.png   daily page: 3 activity dials, then journal lines
  monthly-tracker.png   the monthly tracker grid
"""
import datetime as dt
import math
import os
import sys
import zipfile
from PIL import Image, ImageDraw, ImageFont

# ---- Settings (inches unless noted) ----
DPI = 600
YEAR = 2027                  # or pass it: python3 pocket_templates.py 2028
WEEK_START = "sun"           # "sun": Sun-Sat weeks, week 1 holds Jan 1 (US calendars)
                             # "mon": ISO weeks, Mon-Sun, week 1 holds Jan 4
LINE_GAP = 0.42              # journal line spacing on the daily page
PAGE_W, PAGE_H = 7.5, 10.0   # letter page minus 0.5" margins
EDGE = 0.03                  # keeps outer lines from being clipped at the image edge
THIN, THICK = 0.5, 1.5       # line weights in points (same as the tracker)
HEADER_H = 1.45              # "Yr ___ Goals:" band at the top of the cover
INDEX_HEADER = False         # True gives the index a "Yr ___ Index" band too
NUM_W = 0.45                 # width of the week-number boxes
NUM_PT, HEAD_PT, MONTH_PT = 12, 18, 11   # font sizes in points
TURN = 90                    # 90 puts Q1 at the left edge, -90 at the right edge
FONT_PATHS = [
    "/usr/share/fonts/opentype/courier-prime/CourierPrime-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
    "C:/Windows/Fonts/courbd.ttf",
    "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
]
MONTHS = "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()


def px(inches):
    return round(inches * DPI)


def lw(points):
    return max(1, round(points / 72 * DPI))


_fonts = {}
def font(size_pt):
    if size_pt not in _fonts:
        size = round(size_pt / 72 * DPI)
        for path in FONT_PATHS:
            try:
                _fonts[size_pt] = ImageFont.truetype(path, size)
                break
            except OSError:
                continue
        else:
            _fonts[size_pt] = ImageFont.load_default(size=size)
    return _fonts[size_pt]


class Sheet:
    """A white image drawn on in inches, measured from the top-left corner."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.img = Image.new("L", (px(w), px(h)), 255)
        self.d = ImageDraw.Draw(self.img)

    def line(self, x1, y1, x2, y2, weight=THIN):
        self.d.line([(px(x1), px(y1)), (px(x2), px(y2))], fill=0, width=lw(weight))

    def rect(self, x1, y1, x2, y2, weight=THICK):
        h = weight / 144  # half the line width, so the corners close
        self.line(x1 - h, y1, x2 + h, y1, weight)
        self.line(x1 - h, y2, x2 + h, y2, weight)
        self.line(x1, y1 - h, x1, y2 + h, weight)
        self.line(x2, y1 - h, x2, y2 + h, weight)

    def text(self, x, y, s, size, anchor="mm"):
        self.d.text((px(x), px(y)), s, font=font(size), fill=0, anchor=anchor)

    def save(self, path):
        self.img.save(path, dpi=(DPI, DPI))
        print(f'Wrote {path} ({self.img.width / DPI:.2f}" x {self.img.height / DPI:.2f}")')


def sideways_page(title, show_header, draw_grid):
    """Portrait page: optional header on top, grid drawn landscape and turned."""
    page = Sheet(PAGE_W, PAGE_H)
    top = HEADER_H if show_header else 0
    grid = Sheet(PAGE_H - top, PAGE_W)
    draw_grid(grid)
    turned = grid.img.rotate(TURN, expand=True)
    page.img.paste(turned, (0, page.img.height - turned.height))
    if show_header:
        page.text(EDGE + 0.06, 0.28, "Yr", HEAD_PT, anchor="lm")
        page.rect(EDGE + 0.6, 0.08, EDGE + 1.85, 0.48, THIN)
        page.text(EDGE + 2.05, 0.28, title, HEAD_PT, anchor="lm")
        page.line(0, top, PAGE_W, top, THIN)
    return page


def cover_grid(g):
    """Two columns: quarter heading rows, week boxes, a writing line per week."""
    cols = [["Q1", *range(1, 14), "Q2", *range(14, 27)],
            ["Q3", *range(27, 40), "Q4", *range(40, 53)]]
    n = len(cols[0])
    row_h = (g.h - 2 * EDGE) / n
    col_w = (g.w - 2 * EDGE) / 2
    for c, labels in enumerate(cols):
        x0 = EDGE + c * col_w
        x_end = x0 + col_w
        for r in range(n + 1):
            g.line(x0, EDGE + r * row_h, x_end, EDGE + r * row_h, THIN)
        for r, label in enumerate(labels):
            y = EDGE + r * row_h
            g.text(x0 + NUM_W / 2, y + row_h / 2, str(label), NUM_PT)
            if isinstance(label, str):  # quarter heading row
                g.line(x0, y, x_end, y, THICK)
                g.line(x0, y + row_h, x_end, y + row_h, THICK)
        g.rect(x0, EDGE, x0 + NUM_W, g.h - EDGE)


def week1_start(year):
    """First day of week 1."""
    if WEEK_START == "mon":
        return dt.date.fromisocalendar(year, 1, 1)
    jan1 = dt.date(year, 1, 1)
    return jan1 - dt.timedelta(days=(jan1.weekday() + 1) % 7)


def month_starts(year):
    """Where each month starts, in weeks from the top of week 1.
    Starts on a week's 1st-2nd day snap to that week, 3rd-5th to its middle, 6th-7th to the next."""
    w1 = week1_start(year)
    starts = [0.0]
    for m in range(2, 13):
        days = (dt.date(year, m, 1) - w1).days
        week, dow = divmod(days, 7)
        starts.append(min(52.0, week + (0 if dow <= 1 else 0.5 if dow <= 4 else 1)))
    return starts + [52.0]


def index_grid(g):
    """Two columns of week boxes; the open space is divided only where months change."""
    per_col = 26
    row_h = (g.h - 2 * EDGE) / per_col
    col_w = (g.w - 2 * EDGE) / 2
    starts = month_starts(YEAR)
    for c in range(2):
        x0 = EDGE + c * col_w
        xn, x_end = x0 + NUM_W, x0 + col_w
        lo, hi = c * per_col, (c + 1) * per_col
        for r in range(per_col):
            y = EDGE + r * row_h
            g.text(x0 + NUM_W / 2, y + row_h / 2, str(lo + r + 1), NUM_PT)
            g.line(x0, y, xn, y, THIN)
        g.rect(x0, EDGE, xn, g.h - EDGE)
        g.line(xn, g.h - EDGE, x_end, g.h - EDGE, THIN)
        for m in range(12):
            a, b = max(starts[m], lo), min(starts[m + 1], hi)
            if b <= a:
                continue
            ya = EDGE + (a - lo) * row_h
            g.line(xn, ya, x_end, ya, THIN)
            if b - a >= 1:  # no label on half-week slivers; the month is labeled where it continues
                g.text(xn + 0.08, ya + 0.05, MONTHS[m], MONTH_PT, anchor="lt")


def label_boxes(s, x, y, labels, h=0.32, size=NUM_PT):
    """Small outlined label boxes in a row, sized to their text. Returns the right edge."""
    for text in labels:
        w = max(0.32, font(size).getlength(text) / DPI + 0.14)
        s.rect(x, y, x + w, y + h, THIN)
        s.text(x + w / 2, y + h / 2, text, size)
        x += w
    return x


def weekly_page(year, week):
    """Month(s) top-left, week number top-right, then Goal, seven days, Outcome."""
    s = Sheet(PAGE_W, PAGE_H)
    first = week1_start(year) + dt.timedelta(weeks=week - 1)
    days = [first + dt.timedelta(days=i) for i in range(7)]
    months = "/".join(dict.fromkeys(MONTHS[d.month - 1] for d in days))
    letters = "SMTWTFS" if WEEK_START == "sun" else "MTWTFSS"
    head = 0.55
    label_boxes(s, EDGE, EDGE, [months], h=0.45, size=HEAD_PT)
    num = str(week)
    w = font(HEAD_PT).getlength(num) / DPI + 0.3
    s.rect(PAGE_W - EDGE - w, EDGE, PAGE_W - EDGE, EDGE + 0.45, THIN)
    s.text(PAGE_W - EDGE - w / 2, EDGE + 0.225, num, HEAD_PT)
    box_h = (PAGE_H - EDGE - head) / 9
    rows = [["GOAL"]] + [[letters[i], str(d.day) if d.day != 1 else f"{MONTHS[d.month - 1]} 1"]
                         for i, d in enumerate(days)] + [["OUTCOME"]]
    for r, labels in enumerate(rows):
        y = head + r * box_h
        s.line(0, y, PAGE_W, y, THICK if r in (0, 1, 8) else THIN)
        label_boxes(s, EDGE, y, labels)
    s.line(0, PAGE_H - EDGE, PAGE_W, PAGE_H - EDGE, THICK)
    return s


def gauge(s, cx, cy, r, kind):
    """A half-circle dial to mark by hand: engagement (LO-HI + Flow) or energy (NEG-0-POS)."""
    box = [px(cx - r), px(cy - r), px(cx + r), px(cy + r)]
    if kind == "energy":
        s.d.pieslice(box, 180, 270, fill=205)          # negative half shaded
        s.line(cx, cy - r, cx, cy, THIN)
    s.d.arc(box, 180, 360, fill=0, width=lw(THICK))
    for i in range(9):
        a = math.radians(180 + i * 22.5)
        r1 = r * (0.72 if i % 2 == 0 else 0.84)
        s.line(cx + r1 * math.cos(a), cy + r1 * math.sin(a),
               cx + r * math.cos(a), cy + r * math.sin(a), THIN)
    s.line(cx - r - 0.02, cy, cx + r + 0.02, cy, THICK)
    pr = 0.09
    s.d.ellipse([px(cx - pr), px(cy - pr), px(cx + pr), px(cy + pr)],
                fill=255, outline=0, width=lw(THIN))
    lo, hi, name = ("LO", "HI", "Engagement") if kind == "engage" else ("NEG", "POS", "Energy")
    s.text(cx - r - 0.06, cy - 0.06, lo, 9, anchor="rm")
    s.text(cx + r + 0.06, cy - 0.06, hi, 9, anchor="lm")
    s.text(cx, cy + pr + 0.05, name, 10, anchor="mt")
    if kind == "engage":
        b = 0.15
        s.rect(cx + r - b / 2, cy - r - 0.02 - b, cx + r + b / 2, cy - r - 0.02, THIN)
        s.text(cx + r - b / 2 - 0.04, cy - r - 0.02 - b / 2, "Flow", 9, anchor="rm")
    else:
        s.text(cx, cy - r - 0.03, "0", 9, anchor="mb")


def daily_page(activities=3):
    """Good Time Journal day: date, a few activity boxes with dials, journal lines below."""
    s = Sheet(PAGE_W, PAGE_H)
    s.text(EDGE + 0.05, 0.3, "Date:", 14, anchor="lm")
    s.line(EDGE + 0.85, 0.42, EDGE + 3.6, 0.42, THIN)
    top, row_h, r = 0.6, 1.25, 0.5
    right = PAGE_W - EDGE
    energy_cx = right - 0.5 - r
    engage_cx = energy_cx - 1.8
    split = engage_cx - r - 0.4
    for i in range(activities):
        y = top + i * row_h
        s.rect(EDGE, y, right, y + row_h)
        s.line(split, y, split, y + row_h, THIN)
        cy = y + 0.3 + r
        gauge(s, engage_cx, cy, r, "engage")
        gauge(s, energy_cx, cy, r, "energy")
    y = top + activities * row_h + LINE_GAP
    while y <= PAGE_H - EDGE:
        s.line(EDGE, y, right, y, THIN)
        y += LINE_GAP
    return s


def weekly_pages(year):
    """All 52 weekly pages in a folder, plus a zip of that folder."""
    folder = f"weekly-{year}"
    os.makedirs(folder, exist_ok=True)
    for week in range(1, 53):
        weekly_page(year, week).save(os.path.join(folder, f"week-{week:02d}.png"))
    with zipfile.ZipFile(f"{folder}.zip", "w") as z:
        for name in sorted(os.listdir(folder)):
            z.write(os.path.join(folder, name), os.path.join(folder, name))
    print(f"Wrote {folder}.zip")


def monthly_tracker():
    """The original tracker, same geometry, filling the 7.5" x 10" area."""
    CELL, COLS, ROWS, TOP_SPACE = 0.255, 13, 31, 1.35
    s = Sheet(PAGE_W, PAGE_H)
    left, right, top, bottom = EDGE, PAGE_W, 0, PAGE_H
    gx0 = left + CELL
    gx1 = gx0 + COLS * CELL
    gy0 = top + TOP_SPACE
    gy1 = gy0 + ROWS * CELL
    half = CELL / 2
    for k in range(2, COLS + 2):           # main grid verticals, top to bottom
        s.line(left + k * CELL, top, left + k * CELL, bottom, THIN)
    for r in range(ROWS + 1):              # rows, extended to the right edge
        s.line(gx0, gy0 + r * CELL, right, gy0 + r * CELL, THIN)
    for r in range(ROWS + 1):              # offset (sleep) column, half a cell down
        s.line(left, gy0 + half + r * CELL, gx0, gy0 + half + r * CELL, THIN)
    s.rect(gx0, gy0, gx1, gy1)
    s.rect(left, gy0 + half, gx0, gy1 + half)
    for d in range(1, ROWS + 1):
        s.text(gx0 + half, gy0 + (d - 0.5) * CELL, str(d), NUM_PT)
    return s


if __name__ == "__main__":
    if len(sys.argv) > 1:
        YEAR = int(sys.argv[1])
    sideways_page("Goals:", True, cover_grid).save("year-cover.png")
    sideways_page("Index", INDEX_HEADER, index_grid).save(f"year-index-{YEAR}.png")
    monthly_tracker().save("monthly-tracker.png")
    daily_page().save("daily-good-time.png")
    weekly_pages(YEAR)
