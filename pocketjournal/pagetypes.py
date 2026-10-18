"""The page-type registry. A page type is a function (draw, box, ctx) that
draws one page in page-local millimeters; register it with @page_type."""
from typing import Any, Callable

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


# Short labels the monthly page index prints for each kind of page. A function
# takes the page's PageSpec and returns the label; types without one stay blank.
INDEX_LABELS: dict[str, Callable[[Any], str]] = {}


def index_label(name: str) -> Callable:
    def register(fn: Callable[[Any], str]) -> Callable[[Any], str]:
        INDEX_LABELS[name] = fn
        return fn
    return register


def label_for(spec: Any) -> str:
    fn = INDEX_LABELS.get(spec.type)
    return fn(spec) if fn else ""


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
    if ctx.params.get("label"):                      # the header rule every headed page has
        d.line(g.x0, g.y1 - HEADER_ROWS * g.cell, g.x1, g.y1 - HEADER_ROWS * g.cell,
               s.structure_weight)


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


from . import indexpages  # noqa: E402,F401  (registers the index page types)
from . import yearpages  # noqa: E402,F401  (registers the year journal page types)
from . import monthlypages  # noqa: E402,F401  (registers the monthly journal page types)
