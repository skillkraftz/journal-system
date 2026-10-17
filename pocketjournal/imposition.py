"""Saddle-stitch imposition for half-letter sheets with manual duplex.

Each sheet carries a two-page spread on each side, landscape, centered on the
sheet's fold line. A signature of 4n pages nests n sheets. Sheet 0 is the
outermost. Sheet k of n (0-based) carries, with p = 1..4n the signature page:

    front: left = 4n - 2k,      right = 2k + 1
    back:  left = 2k + 2,       right = 4n - 2k - 1

Manual duplex (same as reference/booklet): print-first.pdf holds the sheet
fronts in REVERSE order, print-second.pdf the sheet backs in FORWARD order.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from .config import Settings
from .draw import Draw
from .page import PageBox

# Draws one page's content in page-local mm; the bool says "right-hand page".
Drawer = Callable[[Draw, bool], None]
# Draws book page number n (1-based); the bool says "right-hand page".
PageDrawer = Callable[[Draw, int, bool], None]


@dataclass(frozen=True)
class SheetSide:
    left: Optional[int]    # book page numbers; None is a blank filler page
    right: Optional[int]


@dataclass(frozen=True)
class Sheet:
    index: int             # 0 is the outermost sheet of its signature
    creep: float           # mm the pages shift toward the fold
    front: SheetSide
    back: SheetSide


@dataclass(frozen=True)
class Signature:
    number: int            # 1-based
    first_page: int        # first book page in this signature
    pages: int             # multiple of 4, includes filler pages
    sheets: tuple[Sheet, ...]


def signature_sizes(total_pages: int, signatures: int = 1) -> list[int]:
    """Pages per signature, each a multiple of 4. Pages are split evenly and
    rounded up, like reference/booklet; fewer signatures come back if the
    pages run out."""
    if total_pages < 1 or signatures < 1:
        raise ValueError("need at least one page and one signature")
    per = -(-(-(-total_pages // signatures)) // 4) * 4
    sizes, left = [], total_pages
    while left > 0:
        sizes.append(per)
        left -= per
    return sizes


def creep_for(sheet_index: int, s: Settings) -> float:
    """Sheets wrapped around this one times the paper thickness."""
    return sheet_index * s.paper_thickness


def impose(total_pages: int, s: Settings, signatures: int = 1) -> list[Signature]:
    result, first = [], 1
    for number, pages in enumerate(signature_sizes(total_pages, signatures), 1):
        def book(local: int) -> Optional[int]:
            page = first + local - 1
            return page if page <= total_pages else None
        n = pages // 4
        sheets = tuple(
            Sheet(index=k, creep=creep_for(k, s),
                  front=SheetSide(book(4 * n - 2 * k), book(2 * k + 1)),
                  back=SheetSide(book(2 * k + 2), book(4 * n - 2 * k - 1)))
            for k in range(n))
        result.append(Signature(number, first, pages, sheets))
        first += pages
    return result


def duplex_order(sheets: int) -> tuple[list[int], list[int]]:
    """Sheet indexes in print order: (print-first fronts, print-second backs)."""
    return list(range(sheets - 1, -1, -1)), list(range(sheets))


# ---- Geometry on the sheet ----------------------------------------------

def page_origin(is_right: bool, creep: float, s: Settings) -> tuple[float, float]:
    """Sheet position (mm) of a page's bottom-left corner. Pages shift toward
    the fold by `creep`, so the left page moves right and the right page left."""
    y = (s.sheet_h - s.page_h) / 2
    if is_right:
        return s.fold_x - creep, y
    return s.fold_x - s.page_w + creep, y


def draw_spread(d: Draw, left: Optional[Drawer], right: Optional[Drawer],
                creep: float, s: Settings) -> None:
    """Draw one sheet side. Each page is clipped to its own box, so nothing can
    land in the trim zone however a page type behaves."""
    for is_right, drawer in ((False, left), (True, right)):
        if drawer is None:
            continue
        x, y = page_origin(is_right, creep, s)
        with d.shifted(x, y):
            d.clip(0, 0, s.page_w, s.page_h)
            drawer(d, is_right)


def _numbered(page: Optional[int], draw_page: PageDrawer) -> Optional[Drawer]:
    if page is None:
        return None

    def drawer(d: Draw, is_right: bool) -> None:
        if is_right != bool(page % 2):
            raise AssertionError(f"page {page} landed on the wrong side")
        draw_page(d, page, is_right)
    return drawer


def _write_sides(path: Path, sides: list[tuple[Sheet, SheetSide]], back: bool,
                 draw_page: PageDrawer, s: Settings) -> None:
    d = Draw(path, s.sheet_w, s.sheet_h, s)
    dx, dy = (s.back_offset_x, s.back_offset_y) if back else (0.0, 0.0)
    for sheet, side in sides:
        with d.shifted(dx, dy):
            draw_spread(d, _numbered(side.left, draw_page),
                        _numbered(side.right, draw_page), sheet.creep, s)
        d.next_page()
    d.save()


def write_signature(sig: Signature, draw_page: PageDrawer, s: Settings,
                    first_path: Path, second_path: Path) -> None:
    """Write the manual duplex pair for one signature."""
    s.validate(len(sig.sheets))
    fronts, backs = duplex_order(len(sig.sheets))
    _write_sides(first_path, [(sig.sheets[i], sig.sheets[i].front) for i in fronts],
                 False, draw_page, s)
    _write_sides(second_path, [(sig.sheets[i], sig.sheets[i].back) for i in backs],
                 True, draw_page, s)


def write_cover(path: Path, left: Drawer, right: Drawer, s: Settings) -> None:
    """The cover spread: inside front cover on the left, inside back cover on
    the right, single-sided, centered, no creep."""
    d = Draw(path, s.sheet_w, s.sheet_h, s)
    draw_spread(d, left, right, 0.0, s)
    d.save()
