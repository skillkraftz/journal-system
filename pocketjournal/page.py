"""What a page type draws into (PageBox) and what it knows (PageContext)."""
import datetime as dt
from dataclasses import dataclass, field
from typing import Any, Mapping

from .config import Settings


@dataclass(frozen=True)
class PageBox:
    """One page at final size. Page-local coordinates: origin bottom-left, y up.

    Page 1 of a book is a right-hand page, so odd pages are right-hand: their
    gutter is on the left and their fore-edge on the right.
    """
    s: Settings
    is_right: bool

    @property
    def w(self) -> float:
        return self.s.page_w

    @property
    def h(self) -> float:
        return self.s.page_h

    @property
    def margin_left(self) -> float:
        return self.s.margin_gutter if self.is_right else self.s.margin_fore

    @property
    def margin_right(self) -> float:
        return self.s.margin_fore if self.is_right else self.s.margin_gutter

    @property
    def x0(self) -> float:
        return self.margin_left

    @property
    def x1(self) -> float:
        return self.w - self.margin_right

    @property
    def y0(self) -> float:
        return self.s.margin_bottom

    @property
    def y1(self) -> float:
        return self.h - self.s.margin_top

    @property
    def content_w(self) -> float:
        return self.x1 - self.x0

    @property
    def content_h(self) -> float:
        return self.y1 - self.y0

    def grid_area(self) -> "GridArea":
        """The whole 3 mm cells that fit in the content area, centered in it."""
        g = self.s.grid
        cols = int(self.content_w / g + 1e-9)
        rows = int(self.content_h / g + 1e-9)
        return GridArea(
            x0=self.x0 + (self.content_w - cols * g) / 2,
            y0=self.y0 + (self.content_h - rows * g) / 2,
            cols=cols, rows=rows, cell=g)


@dataclass(frozen=True)
class GridArea:
    x0: float
    y0: float
    cols: int
    rows: int
    cell: float

    @property
    def x1(self) -> float:
        return self.x0 + self.cols * self.cell

    @property
    def y1(self) -> float:
        return self.y0 + self.rows * self.cell

    def x(self, col: int) -> float:
        return self.x0 + col * self.cell

    def y(self, row: int) -> float:
        return self.y0 + row * self.cell


@dataclass(frozen=True)
class PageContext:
    page_number: int
    total_pages: int
    settings: Settings
    params: Mapping[str, Any] = field(default_factory=dict)
    # filled in by recipes: `each: day` sets date, `each: week` sets date
    # (the week's Sunday) and week (1-52); year and month come from the build
    date: dt.date | None = None
    year: int | None = None
    month: int | None = None
    week: int | None = None
