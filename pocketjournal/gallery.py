"""The `previews` command: regenerate everything in `previews/`.

One PNG per page type at final size (`page-<type>.png`), a contact sheet and
the cover spread of every recipe (`<book>-contact-sheet.png`,
`<book>-cover.png`) and the two calibration sheets. Run it in every change
that touches a design, so the previews are never stale.
"""
import datetime as dt
import shutil
import tempfile
from pathlib import Path

from . import book as books
from . import calendars
from . import recipe as recipes
from .calibration import write_calibration
from .config import RECIPE_DIR, Settings
from .draw import Draw
from .page import PageBox, PageContext
from .pagetypes import PAGE_TYPES, draw_page_number, get_page_type
from .preview import save_pages

SAMPLE_YEAR, SAMPLE_MONTH = 2026, 10
SAMPLE_DAY = dt.date(2026, 10, 26)           # a Monday
SAMPLE_WEEK_SUNDAY = dt.date(2026, 6, 28)    # a week that spans two months
# page types that sit inside a book (and so carry a page number and header)
INTERIOR = {"lined", "dots", "week", "daily", "week_reflection", "month_review", "someday"}
SAMPLE_NUMBER = 13                           # odd: a right-hand page
DPI = 200


def _sample_context(name: str, s: Settings) -> PageContext:
    date = SAMPLE_WEEK_SUNDAY if name in ("week", "week_reflection") else SAMPLE_DAY
    week = calendars.week_number(SAMPLE_WEEK_SUNDAY) if name in ("week", "week_reflection") else None
    params = {"label": "NOTES"} if name == "lined" else {}
    return PageContext(SAMPLE_NUMBER, s.book_pages, s, params, date,
                       SAMPLE_YEAR, SAMPLE_MONTH, week)


def render_page_type(name: str, s: Settings, tmp: Path, out: Path) -> Path:
    """One page type at final size, as a right-hand page."""
    ctx, box = _sample_context(name, s), PageBox(s, True)
    pdf = tmp / f"{name}.pdf"
    d = Draw(pdf, s.page_w, s.page_h, s)
    get_page_type(name)(d, box, ctx)
    if name in INTERIOR:
        draw_page_number(d, box, ctx)
    d.next_page()
    d.save()
    [png] = save_pages(pdf, tmp, name, dpi=DPI)
    shutil.move(png, out)
    return out


def write_previews(out_dir: Path, s: Settings, recipe_dir: Path = RECIPE_DIR) -> list[Path]:
    """Replace the PNGs in out_dir with fresh ones; returns what was written."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.png"):
        old.unlink()
    written = []
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        for name in sorted(PAGE_TYPES):
            if name != "blank":
                written.append(render_page_type(name, s, tmp, out_dir / f"page-{name}.png"))
        for name, r in recipes.list_recipes(recipe_dir).items():
            book = recipes.build_book(r, s, SAMPLE_YEAR if "year" in r.needs else None,
                                      SAMPLE_MONTH if "month" in r.needs else None)
            folder = tmp / name
            books.build_book(book, folder, s)
            for src, dst in (("preview.png", "contact-sheet"), ("cover.png", "cover")):
                target = out_dir / f"{name}-{dst}.png"
                shutil.copy(folder / src, target)
                written.append(target)
        first, second = write_calibration(tmp / "calibration", s)
        for pdf, side in ((first, "front"), (second, "back")):
            [png] = save_pages(pdf, tmp, f"calibration-{side}", dpi=DPI)
            target = out_dir / f"calibration-{side}.png"
            shutil.move(png, target)
            written.append(target)
    return written
