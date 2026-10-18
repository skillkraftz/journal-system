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
    """A light gray line on every grid row, top and bottom included."""
    s, g = ctx.settings, box.grid_area()
    for row in range(g.rows + 1):
        d.line(g.x0, g.y(row), g.x1, g.y(row), s.rule_weight, s.rule_gray)


@page_type("dots")
def dots(d: Draw, box: PageBox, ctx: PageContext) -> None:
    """A light gray dot on every grid intersection."""
    s, g = ctx.settings, box.grid_area()
    for row in range(g.rows + 1):
        for col in range(g.cols + 1):
            d.circle(g.x(col), g.y(row), s.dot_radius, s.dot_gray)


def draw_page_number(d: Draw, box: PageBox, ctx: PageContext) -> None:
    """The page number, in the bottom outer corner, centered in the bottom
    margin so it never touches the writing area. Books turn this on with
    `page_numbers: true`; it is not a page type."""
    s = ctx.settings
    size_mm = s.font_page_number * 25.4 / 72
    baseline = (s.margin_bottom - 0.62 * size_mm) / 2     # 0.62: cap height / size
    if box.is_right:
        d.text(box.x1, baseline, str(ctx.page_number), s.font_page_number, anchor="r")
    else:
        d.text(box.x0, baseline, str(ctx.page_number), s.font_page_number, anchor="l")


from . import indexpages  # noqa: E402,F401  (registers the index page types)
from . import yearpages  # noqa: E402,F401  (registers the year journal page types)
from . import monthlypages  # noqa: E402,F401  (registers the monthly journal page types)
