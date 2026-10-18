"""Indexes drawn like the year journal's covers: two sideways columns, read
with the book turned a quarter turn clockwise. Pages 1-26 are the lower column,
27-52 the upper one; each page is a 3 mm strip with a narrow number zone at its
start and open space after it for handwriting.

    index        plain books: 26 pages per column plus a "goal post" strip
                 after pages 13, 26, 39 and 52 (a date field)
    page_index   monthly journal: 26 strips per column, each with a small gray
                 label saying what kind of page it is
"""
from .draw import Draw
from .page import PageBox, PageContext
from .pagetypes import label_for, page_type
from .yearpages import NUMBER_ZONE, _cap, _sideways_number

PAGES = 52
PER_COLUMN = PAGES // 2
GOAL_EVERY = 13              # a goal-post strip follows every 13th page
CENTER_PAGE = PAGES // 2     # the spread at the stitches
LABEL_GRAY = 0.4


def _column(d: Draw, s, left: float, pitch: float, y_a: float, height: float,
            strips: list, labels: dict[int, str], mark_center: bool) -> None:
    """One sideways column. `strips` holds a page number, or None for a goal
    post; `labels` maps page numbers to their small gray label."""
    y_b, open_y = y_a + height, y_a + NUMBER_ZONE
    right = left + len(strips) * pitch
    for k, page in enumerate(strips):
        x0, cx = left + k * pitch, left + (k + 0.5) * pitch
        if page is None:                                     # goal post: a date field
            for edge in (x0, x0 + pitch):
                d.line(edge, y_a, edge, y_b, s.structure_weight)
            continue
        if mark_center and page == CENTER_PAGE:                # subtle mark: a faint tint
            d.fill_rect(x0, y_a, pitch, height, s.tint_gray)
        d.line(x0, y_a, x0, y_b, s.rule_weight, s.rule_gray)
        d.line(x0 + pitch, y_a, x0 + pitch, y_b, s.rule_weight, s.rule_gray)
        _sideways_number(d, s, cx, y_a + NUMBER_ZONE / 2, str(page), bold=mark_center and page == CENTER_PAGE)
        if labels.get(page):
            d.text(cx + _cap(s.font_label) / 2, open_y + 1.5, labels[page],
                   s.font_label, gray=LABEL_GRAY, rotate=90)
    d.line(left, open_y, right, open_y, s.structure_weight)
    d.rect(left, y_a, right - left, height, s.structure_weight)


@page_type("index")
def index(d: Draw, box: PageBox, ctx: PageContext) -> None:
    """Plain books: a universal index (page number, topic) in two sideways
    columns, with a date field after pages 13, 26, 39 and 52 for when that
    point in the book was reached. Page 26, the center spread, is tinted.

    The 28 strips per column share the content width, so the pitch is 2.96 mm:
    as close to 3 mm as fits."""
    s, g = ctx.settings, box.grid_area()
    strips_per_column = PER_COLUMN + PER_COLUMN // GOAL_EVERY
    pitch = (box.x1 - box.x0) / strips_per_column
    height = g.rows // 2 * g.cell
    for c in range(2):
        strips = []
        for page in range(c * PER_COLUMN + 1, (c + 1) * PER_COLUMN + 1):
            strips.append(page)
            if page % GOAL_EVERY == 0:
                strips.append(None)
        _column(d, s, box.x0, pitch, g.y0 + c * height, height, strips, {}, True)


@page_type("page_index")
def page_index(d: Draw, box: PageBox, ctx: PageContext) -> None:
    """Monthly journal: all 52 pages, two sideways columns of 26 strips on the
    3 mm grid. Known page types start their strip with a small label (SUN 1,
    wk 45, patterns, questions, idea:); lined and dot pages stay blank."""
    if len(ctx.book_pages) != PAGES:
        raise ValueError(f"the page index needs the book's {PAGES} pages")
    s, g = ctx.settings, box.grid_area()
    labels = {n: label_for(spec) for n, spec in enumerate(ctx.book_pages, 1)}
    pitch, height = g.cell, g.rows // 2 * g.cell
    left = g.x0 + (g.x1 - g.x0 - PER_COLUMN * pitch) / 2     # center the 26 strips
    for c in range(2):
        pages = list(range(c * PER_COLUMN + 1, (c + 1) * PER_COLUMN + 1))
        _column(d, s, left, pitch, g.y0 + c * height, height, pages, labels, False)
