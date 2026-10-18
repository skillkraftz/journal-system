"""The page-type registry. A page type is a function (draw, box, ctx) that
draws one page in page-local millimeters; register it with @page_type."""
from typing import Callable

from .draw import Draw
from .page import PageBox, PageContext

PageFn = Callable[[Draw, PageBox, PageContext], None]
PAGE_TYPES: dict[str, PageFn] = {}


def page_type(name: str) -> Callable[[PageFn], PageFn]:
    def register(fn: PageFn) -> PageFn:
        if name in PAGE_TYPES:
            raise ValueError(f"page type {name!r} is already registered")
        PAGE_TYPES[name] = fn
        return fn
    return register


def get_page_type(name: str) -> PageFn:
    try:
        return PAGE_TYPES[name]
    except KeyError:
        raise KeyError(f"unknown page type {name!r}; "
                       f"known: {', '.join(sorted(PAGE_TYPES))}") from None


@page_type("blank")
def blank(d: Draw, box: PageBox, ctx: PageContext) -> None:
    pass


@page_type("lined")
def lined(d: Draw, box: PageBox, ctx: PageContext) -> None:
    """A light gray line on every grid row, top and bottom included.

    params: label - what the page is, shown by the spine in the header row
    """
    s, g = ctx.settings, box.grid_area()
    if ctx.params.get("label"):
        draw_header(d, box, ctx, str(ctx.params["label"]))
    for row in range(g.rows + 1):
        d.line(g.x0, g.y(row), g.x1, g.y(row), s.rule_weight, s.rule_gray)


@page_type("dots")
def dots(d: Draw, box: PageBox, ctx: PageContext) -> None:
    """A light gray dot on every grid intersection."""
    s, g = ctx.settings, box.grid_area()
    for row in range(g.rows + 1):
        for col in range(g.cols + 1):
            d.circle(g.x(col), g.y(row), s.dot_radius, s.dot_gray)


HEADER_ROWS = 1              # every numbered page starts with a one-row header


def header_base(box: PageBox, s) -> float:
    """Baseline of label-size text in the header row (the top grid row)."""
    return box.grid_area().y1 - s.grid + 0.7


def draw_page_number(d: Draw, box: PageBox, ctx: PageContext) -> None:
    """The page number, in the top outer corner of the header row. Books turn
    this on with `page_numbers: true`; it is not a page type."""
    s, g = ctx.settings, box.grid_area()
    d.text(g.x1 if box.is_right else g.x0, header_base(box, s), str(ctx.page_number),
           s.font_page_number, bold=True, anchor="r" if box.is_right else "l")


def draw_header(d: Draw, box: PageBox, ctx: PageContext, identity: str) -> None:
    """What this page is, in the top inner corner (by the spine). On an open
    spread it reads `30  July | July  31`."""
    s, g = ctx.settings, box.grid_area()
    d.text(g.x0 if box.is_right else g.x1, header_base(box, s), identity,
           s.font_label, bold=True, anchor="l" if box.is_right else "r")


@page_type("index")
def index(d: Draw, box: PageBox, ctx: PageContext) -> None:
    """A universal index: page number column and topic area, one entry per
    3 mm row, with a small date-range field in the top row.

    params: number_cols (grid columns for the page number column, default 3)
    """
    s, g = ctx.settings, box.grid_area()
    split = g.x(int(ctx.params.get("number_cols", 3)))
    head = g.y(g.rows - 2)                      # bottom of the two header rows
    base = lambda row_bottom: row_bottom + 0.7  # text baseline inside a row

    # row 0: title and "dates ____ - ____"
    top = base(g.y(g.rows - 1))
    d.text(g.x0, top, "INDEX", s.font_label, bold=True)
    f2, f1 = (g.x(g.cols - 5), g.x1), (g.x(g.cols - 11), g.x(g.cols - 6))
    d.text(f1[0] - 1.5, top, "dates", s.font_label, gray=0.4, anchor="r")
    for a, b in (f1, f2):
        d.line(a, g.y(g.rows - 1), b, g.y(g.rows - 1), s.rule_weight, s.rule_gray)
    d.text((f1[1] + f2[0]) / 2, top, "-", s.font_label, gray=0.4, anchor="c")

    # row 1: column labels, then a black line under the header
    row1 = base(g.y(g.rows - 2))
    d.text((g.x0 + split) / 2, row1, "pg", s.font_label, gray=0.4, anchor="c")
    d.text(split + 1.0, row1, "topic", s.font_label, gray=0.4)
    d.line(g.x0, head, g.x1, head, s.structure_weight)

    # entries
    for row in range(g.rows - 2):
        d.line(g.x0, g.y(row), g.x1, g.y(row), s.rule_weight, s.rule_gray)
    d.line(split, g.y(0), split, head, s.structure_weight)


from . import yearpages  # noqa: E402,F401  (registers the year journal page types)
from . import monthlypages  # noqa: E402,F401  (registers the monthly journal page types)
