"""Books: an ordered list of page specs plus a cover, built into a folder of
print-ready files."""
import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from . import imposition
from .config import Settings
from .draw import Draw
from .page import PageBox, PageContext
from .pagetypes import draw_page_number, get_page_type
from .preview import contact_sheet, save_pages


@dataclass(frozen=True)
class PageSpec:
    type: str
    params: Mapping[str, Any] = field(default_factory=dict)
    year: int | None = None
    month: int | None = None
    date: dt.date | None = None
    week: int | None = None


@dataclass(frozen=True)
class Book:
    name: str
    pages: tuple[PageSpec, ...]
    cover: tuple[PageSpec, PageSpec]   # inside front cover, inside back cover
    page_numbers: bool = False         # number the interior pages
    title: str = ""


def _draw_spec(d: Draw, spec: PageSpec, is_right: bool, number: int,
               total: int, s: Settings, numbered: bool = False,
               book_pages: tuple = ()) -> None:
    """number 0 is a cover page (never numbered)."""
    ctx = PageContext(number, total, s, spec.params, spec.date, spec.year,
                      spec.month, spec.week, tuple(book_pages))
    box = PageBox(s, is_right)
    get_page_type(spec.type)(d, box, ctx)
    if numbered and number:
        draw_page_number(d, box, ctx)


def write_pages_pdf(book: Book, path: Path, s: Settings) -> None:
    """Every interior page at final size, in order (for preview and checking)."""
    d = Draw(path, s.page_w, s.page_h, s)
    for n, spec in enumerate(book.pages, 1):
        _draw_spec(d, spec, bool(n % 2), n, len(book.pages), s, book.page_numbers,
                   book.pages)
        d.next_page()
    d.save()


def build_book(book: Book, out_dir: Path, s: Settings, signatures: int = 1) -> dict:
    s.validate()
    out_dir.mkdir(parents=True, exist_ok=True)
    total = len(book.pages)
    sigs = imposition.impose(total, s, signatures)

    def draw_page(d: Draw, n: int, is_right: bool) -> None:
        _draw_spec(d, book.pages[n - 1], is_right, n, total, s, book.page_numbers,
                   book.pages)

    files = []
    for sig in sigs:
        prefix = f"sig{sig.number}-" if len(sigs) > 1 else ""
        first, second = out_dir / f"{prefix}print-first.pdf", out_dir / f"{prefix}print-second.pdf"
        imposition.write_signature(sig, draw_page, s, first, second)
        files += [first.name, second.name]

    left, right = book.cover
    imposition.write_cover(
        out_dir / "cover.pdf",
        lambda d, r: _draw_spec(d, left, r, 0, total, s, book_pages=book.pages),
        lambda d, r: _draw_spec(d, right, r, 0, total, s, book_pages=book.pages), s)
    pages_pdf = out_dir / "pages.pdf"
    write_pages_pdf(book, pages_pdf, s)
    contact_sheet(pages_pdf, out_dir / "preview.png", s)
    save_pages(out_dir / "cover.pdf", out_dir, "cover", dpi=100)
    (out_dir / "cover-01.png").replace(out_dir / "cover.png")
    files += ["cover.pdf", "pages.pdf", "preview.png", "cover.png"]

    summary = _summary(book, sigs, s, files)
    (out_dir / "summary.txt").write_text(summary)
    return {"dir": out_dir, "signatures": sigs, "files": files, "summary": summary}


def _summary(book: Book, sigs, s: Settings, files) -> str:
    sheets = sum(len(g.sheets) for g in sigs)
    lines = [
        f"Book: {book.title or book.name}",
        f"Pages: {len(book.pages)} interior ({sheets} sheets in {len(sigs)} signature(s))"
        + (", numbered" if book.page_numbers else ""),
        f"Page size: {s.page_w:.1f} x {s.page_h:.1f} mm, on {s.sheet_w:.1f} x {s.sheet_h:.1f} mm sheets",
        f"Margins: top {s.margin_top}, bottom {s.margin_bottom}, "
        f"fore-edge {s.margin_fore}, gutter {s.margin_gutter} mm; grid {s.grid} mm",
        f"Creep: {s.paper_thickness} mm per sheet "
        f"(max {max(s.max_creep(len(g.sheets)) for g in sigs):.2f} mm)",
        f"Back offset: x {s.back_offset_x} mm, y {s.back_offset_y} mm",
        "",
        "Files: " + ", ".join(files),
        "",
        "Print each signature: print-first, put the stack back in the tray the",
        "same way, then print-second. Fold, sew, wrap in the cover, then measure",
        f"{s.page_w / 25.4:.1f} in from the fold and trim the fore-edge.",
        "Cover: print cover.pdf single-sided on the cover paper.",
    ]
    return "\n".join(lines) + "\n"
