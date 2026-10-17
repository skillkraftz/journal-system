import datetime as dt
from pathlib import Path

import numpy as np
import pypdfium2 as pdfium
import pytest
from pypdf import PdfReader

from pocketjournal import calendars, cli
from pocketjournal.book import build_book as build_folder, write_pages_pdf
from pocketjournal.config import DEFAULT as S
from pocketjournal.draw import Draw
from pocketjournal.page import PageBox, PageContext
from pocketjournal.pagetypes import draw_page_number, get_page_type
from pocketjournal.recipe import (RecipeError, build_book, list_recipes,
                                  load_recipe, parse_recipe)

MM = 72 / 25.4


def recipe(**kw):
    return parse_recipe({"name": "t", **kw})


# ---- calendar ---------------------------------------------------------------

@pytest.mark.parametrize("year", [2024, 2025, 2026, 2027])
def test_weeks(year):
    weeks = calendars.weeks_of_year(year)
    assert len(weeks) == 52
    assert all(d.weekday() == 6 for _, d in weeks)               # Sundays
    first = weeks[0][1]
    assert first <= dt.date(year, 1, 1) < first + dt.timedelta(days=7)
    assert weeks[1][1] - first == dt.timedelta(days=7)


def test_days_of_month():
    assert len(calendars.days_of_month(2024, 2)) == 29
    assert len(calendars.days_of_month(2025, 2)) == 28
    with pytest.raises(ValueError):
        calendars.days_of_month(2025, 13)


# ---- recipes ----------------------------------------------------------------

def test_shipped_recipes():
    names = list(list_recipes())
    assert {"lined", "dots"} <= set(names)
    for name in ("lined", "dots"):
        book = build_book(load_recipe(name), S)
        assert len(book.pages) == 52
        assert book.page_numbers
        assert book.cover[1].type == "index"


def test_fill_after_fixed_pages():
    book = build_book(recipe(pages=[{"type": "dots", "repeat": 3}, "lined"],
                             fill={"type": "blank"}), S)
    assert [p.type for p in book.pages[:5]] == ["dots"] * 3 + ["lined", "blank"]
    assert len(book.pages) == 52


def test_each_day_and_week():
    r = recipe(pages=[{"type": "lined", "each": "day", "repeat": 2}], fill="blank")
    assert r.needs == ("year", "month")
    with pytest.raises(RecipeError, match="more than"):
        build_book(r, S, 2025, 2)              # 28 days x 2 pages = 56
    r = recipe(pages=[{"type": "lined", "each": "week"}])
    assert r.needs == ("year",)
    book = build_book(r, S, 2026)
    assert [p.week for p in book.pages] == list(range(1, 53))
    assert book.pages[0].date == calendars.week_start(2026, 1)


def test_each_day_context():
    book = build_book(recipe(pages=[{"type": "lined", "each": "day"}], fill="blank"),
                      S, 2026, 3)
    assert [p.date for p in book.pages[:31]] == calendars.days_of_month(2026, 3)
    assert book.pages[31].type == "blank" and book.pages[31].date is None


def test_dated_recipe_needs_year():
    with pytest.raises(RecipeError, match="needs a year"):
        build_book(recipe(pages=[{"type": "lined", "each": "week"}]), S)


def test_page_count_rules():
    with pytest.raises(RecipeError, match="fill"):
        build_book(recipe(pages=["lined"]), S)
    with pytest.raises(RecipeError, match="more than"):
        build_book(recipe(pages=[{"type": "lined", "repeat": 53}]), S)


@pytest.mark.parametrize("bad", [
    {"pages": [{"type": "nope"}]},
    {"pages": [{"type": "lined", "repeat": 0}]},
    {"pages": [{"type": "lined", "each": "year"}]},
    {"pages": [{"type": "lined", "colour": 1}]},
    {"cover": {"middle": "blank"}},
    {"fill": {"params": {}}},
    {"surprise": 1},
])
def test_bad_recipes(bad):
    with pytest.raises(RecipeError):
        parse_recipe({"name": "t", **bad})


# ---- index and page numbers ---------------------------------------------------

def render(fn, is_right, path):
    d = Draw(path, S.page_w, S.page_h, S)
    box = PageBox(S, is_right)
    fn(d, box, PageContext(7, 52, S))
    d.next_page()
    d.save()
    img = pdfium.PdfDocument(str(path))[0].render(scale=300 / 72).to_pil().convert("L")
    return np.array(img) < 250


def px(mm):
    return int(round(mm * 300 / 25.4))


def test_page_number_in_bottom_outer_margin(tmp_path):
    for is_right in (True, False):
        m = render(draw_page_number, is_right, tmp_path / f"n{is_right}.pdf")
        ys, xs = np.where(m)
        h, w = m.shape
        assert ys.min() >= h - px(S.margin_bottom)          # inside the bottom margin
        box = PageBox(S, is_right)
        if is_right:
            assert xs.max() <= px(box.x1) + 2 and xs.min() > w / 2
        else:
            assert xs.min() >= px(box.x0) - 2 and xs.max() < w / 2


def test_numbers_only_where_asked(tmp_path):
    lined = build_book(recipe(page_numbers=True, fill="lined"), S)
    plain = build_book(recipe(fill="lined"), S)
    for book, expect in ((lined, True), (plain, False)):
        pdf = tmp_path / f"{expect}.pdf"
        write_pages_pdf(book, pdf, S)
        pages = PdfReader(str(pdf)).pages
        assert ("2" in pages[1].extract_text().split()) is expect
    build_folder(lined, tmp_path / "out", S)
    assert not any(c.isdigit() for c in PdfReader(str(tmp_path / "out/cover.pdf")).pages[0].extract_text())


def test_index_is_on_the_grid(tmp_path):
    m = render(get_page_type("index"), True, tmp_path / "i.pdf")
    assert m.any()


# ---- entry point --------------------------------------------------------------

def test_cli_flags_build_folder(tmp_path):
    cli.main(["build", "lined", "--out", str(tmp_path), "--thickness", "0.08"])
    out = tmp_path / "lined"
    for f in ("print-first.pdf", "print-second.pdf", "cover.pdf", "preview.png",
              "summary.txt"):
        assert (out / f).is_file()
    assert "numbered" in (out / "summary.txt").read_text()


@pytest.fixture
def monthly_dir(tmp_path):
    d = tmp_path / "recipes"
    d.mkdir()
    (d / "days.yaml").write_text(
        "name: days\ntitle: Days\nfill: blank\n"
        "pages:\n  - {type: lined, each: day}\n")
    (d / "plain.yaml").write_text("name: plain\nfill: dots\n")
    return d


def test_all_months(tmp_path, monthly_dir):
    cli.main(["build", "days", "--year", "2026", "--all-months", "--recipes",
              str(monthly_dir), "--out", str(tmp_path / "o")])
    folders = sorted(p.name for p in (tmp_path / "o").iterdir())
    assert folders == [f"days-2026-{m:02d}" for m in range(1, 13)]


def test_missing_year_is_an_error(tmp_path, monthly_dir):
    with pytest.raises(SystemExit):
        cli.main(["build", "days", "--recipes", str(monthly_dir), "--out", str(tmp_path)])


def test_all_means_undated(monthly_dir):
    assert cli.undated(monthly_dir) == ["plain"]


def answers(*replies):
    it = iter(replies)
    return lambda prompt: next(it)


def test_interview_defaults(monthly_dir):
    s = S
    req, s2 = cli.interview(s, monthly_dir, ask=answers("", "", "", "", "", "", ""),
                            say=lambda *_: None, today=dt.date(2026, 5, 1)) or (None, None)
    assert req.recipes == ["days"] and (req.year, req.months) == (2026, [5])
    assert req.signatures == 1 and s2.paper_thickness == s.paper_thickness


def test_interview_choices(monthly_dir):
    req, s2 = cli.interview(S, monthly_dir,
                            ask=answers("days", "2027", "all", "2", "0.12", "out", "y"),
                            say=lambda *_: None)
    assert req.months == list(range(1, 13)) and req.year == 2027
    assert req.signatures == 2 and s2.paper_thickness == 0.12
    assert len(cli.build_folders(req, s2, monthly_dir)) == 12


def test_interview_undated_skips_date_questions(monthly_dir):
    req, _ = cli.interview(S, monthly_dir, ask=answers("plain", "", "", "", ""),
                           say=lambda *_: None)
    assert req.year is None and req.months is None


def test_interview_can_decline(monthly_dir):
    assert cli.interview(S, monthly_dir, ask=answers("plain", "", "", "", "n"),
                         say=lambda *_: None) is None
