"""Indexes drawn like the year journal's covers: two sideways columns, read
with the book turned a quarter turn clockwise. Pages 1-26 are the lower column,
27-52 the upper one; each page is a 3 mm strip with a narrow number zone at its
start and open space after it for handwriting.

    index        plain books: 26 strips per column, a darker line at the
                 quarter points (after pages 13, 26 and 39)
    page_index   monthly journal: 26 strips per column, each with a small gray
                 label saying what kind of page it is
"""
from .draw import Draw
from .page import PageBox, PageContext
from .pagetypes import label_for, page_type
from .yearpages import NUMBER_ZONE, _cap, _sideways_number, _text_base

PAGES = 52
PER_COLUMN = PAGES // 2
QUARTER = PAGES // 4         # quarter points of the book: pages 13, 26, 39
CENTER_PAGE = PAGES // 2     # the spread at the stitches
LABEL_GRAY = 0.4


def _column(d: Draw, s, left: float, pitch: float, y_a: float, height: float,
            pages: list, labels: dict[int, str], dark_after: frozenset = frozenset()) -> None:
    """One sideways column: a 3 mm strip per page, with a small gray label in
    its open space. The line after a page in `dark_after` is drawn darker."""
    y_b, open_y = y_a + height, y_a + NUMBER_ZONE
    right = left + len(pages) * pitch
    for k, page in enumerate(pages):
        x0, cx = left + k * pitch, left + (k + 0.5) * pitch
        d.line(x0, y_a, x0, y_b, s.rule_weight, s.rule_gray)
        d.line(x0 + pitch, y_a, x0 + pitch, y_b, s.rule_weight,
               s.separator_gray if page in dark_after else s.rule_gray)
        _sideways_number(d, s, cx, y_a + NUMBER_ZONE / 2, str(page))
        if labels.get(page):
            d.text(cx + _cap(s.font_label) / 2, open_y + 1.5, labels[page],
                   s.font_label, gray=LABEL_GRAY, rotate=90)
    d.line(left, open_y, right, open_y, s.structure_weight)
    d.rect(left, y_a, right - left, height, s.structure_weight)


def _columns(d: Draw, box: PageBox, ctx: PageContext, labels: dict[int, str],
             dark_after: frozenset = frozenset()) -> None:
    """Both columns: 26 strips each at exactly one grid cell, centered."""
    s, g = ctx.settings, box.grid_area()
    pitch, height = g.cell, g.rows // 2 * g.cell
    left = g.x0 + (g.x1 - g.x0 - PER_COLUMN * pitch) / 2
    for c in range(2):
        pages = list(range(c * PER_COLUMN + 1, (c + 1) * PER_COLUMN + 1))
        _column(d, s, left, pitch, g.y0 + c * height, height, pages, labels, dark_after)


@page_type("index")
def index(d: Draw, box: PageBox, ctx: PageContext) -> None:
    """Plain books: a universal index (page number, topic) in two sideways
    columns of 26 strips at exactly 3 mm. The line after pages 13, 26 and 39 is
    slightly darker so the quarter points of the book stay visible."""
    _columns(d, box, ctx, {}, frozenset(range(QUARTER, PAGES, QUARTER)))


@page_type("page_index")
def page_index(d: Draw, box: PageBox, ctx: PageContext) -> None:
    """Monthly journal: all 52 pages, two sideways columns of 26 strips on the
    3 mm grid. Known page types start their strip with a small label (SUN 1,
    wk 45, patterns, questions, idea:); lined and dot pages stay blank."""
    if len(ctx.book_pages) != PAGES:
        raise ValueError(f"the page index needs the book's {PAGES} pages")
    s, g = ctx.settings, box.grid_area()
    labels = {n: label_for(spec) for n, spec in enumerate(ctx.book_pages, 1)}
    _columns(d, box, ctx, labels)


# Inside front cover of the plain books -----------------------------------------

PURPOSE_LINES = 3            # writing lines under the "for:" label
GOAL_POSTS = ("started", "p13", "p26", "p39", "done")   # dates; p26 is the center spread


@page_type("book_purpose")
def book_purpose(d: Draw, box: PageBox, ctx: PageContext) -> None:
    """Plain books, inside front cover: what the book is for (a gray label and
    a few writing lines), one compact row of date fields for the goal posts, and
    light 3 mm lines for the rest. The p26 field is tinted: the center spread,
    where the owner checks progress."""
    s, g = ctx.settings, box.grid_area()
    row = lambda n: g.y1 - n * g.cell

    d.text(g.x0 + 0.8, _text_base(row(1)), "for:", s.font_label, gray=LABEL_GRAY)
    top = 1 + PURPOSE_LINES                                  # rows used by the purpose block
    for r in range(1, top + 1):
        d.line(g.x0, row(r), g.x1, row(r), s.rule_weight, s.rule_gray)
    d.line(g.x0, row(top), g.x1, row(top), s.structure_weight)

    # goal posts: two rows, the label above a blank row for the date
    fields_top, fields_bottom = row(top), row(top + 2)
    w = (g.x1 - g.x0) / len(GOAL_POSTS)
    for k, name in enumerate(GOAL_POSTS):
        x0 = g.x0 + k * w
        if name == "p26":
            d.fill_rect(x0, fields_bottom, w, fields_top - fields_bottom, s.tint_gray)
        if k:
            d.line(x0, fields_bottom, x0, fields_top, s.rule_weight, s.separator_gray)
        d.text(x0 + 0.8, _text_base(row(top + 1)), name, s.font_label, gray=LABEL_GRAY)
    d.line(g.x0, fields_bottom, g.x1, fields_bottom, s.structure_weight)

    for r in range(top + 3, g.rows + 1):
        d.line(g.x0, row(r), g.x1, row(r), s.rule_weight, s.rule_gray)
