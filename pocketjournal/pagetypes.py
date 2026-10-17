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
