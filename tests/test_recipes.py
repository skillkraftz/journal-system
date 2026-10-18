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


@pytest.mark.parametrize("is_right", [True, False])
def test_plain_index_layout(tmp_path, is_right):
    m = render(get_page_type("index"), is_right, tmp_path / "i.pdf")
    box = PageBox(S, is_right)
    ys, xs = np.where(m)
    tol = 2
    assert ys.min() >= px(S.margin_top) - tol and ys.max() <= m.shape[0] - px(S.margin_bottom) + tol
    assert xs.min() >= px(box.x0) - tol and xs.max() <= px(box.x1) + tol
    # 28 strips per column: count the vertical strip boundaries along a scan row
    col = m[px(S.margin_top) + px(10)]                        # inside the upper column
    edges = np.count_nonzero(np.diff(col.astype(int)) == 1)
    assert edges >= 29


def test_plain_index_has_only_numbers(tmp_path):
    book = build_book(load_recipe("lined"), S)
    build_folder(book, tmp_path / "out", S)
    words = PdfReader(str(tmp_path / "out/cover.pdf")).pages[0].extract_text().split()
    assert sorted(w for w in words if w.isdigit()) == sorted(str(n) for n in range(1, 53))
    assert all(w.isdigit() for w in words)                    # no other labels


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


# ---- year journal ---------------------------------------------------------------

def test_month_starts_snap_to_half_weeks():
    # 2027: week 1 starts Sun Dec 27; Feb 1 is a Monday (2nd day) -> top of week 6
    starts = calendars.month_starts(2027)
    assert len(starts) == 13 and starts[0] == 0 and starts[-1] == 52
    assert starts[1] == 5.0
    assert all(b > a for a, b in zip(starts, starts[1:]))
    assert all(x * 2 == int(x * 2) for x in starts)
    # 3rd-5th day -> middle, 6th-7th day -> next week (2026: week 1 starts Dec 28)
    week1 = calendars.week_start(2026, 1)
    for m, s in enumerate(calendars.month_starts(2026)[1:12], 2):
        week, dow = divmod((dt.date(2026, m, 1) - week1).days, 7)
        assert s == week + (0 if dow < 2 else 0.5 if dow < 5 else 1)


def test_year_recipe():
    book = build_book(load_recipe("year"), S, 2027)
    assert len(book.pages) == 52 and book.page_numbers
    assert {p.type for p in book.pages} == {"week"}
    assert [p.type for p in book.cover] == ["year_goals", "year_index"]
    assert book.cover[0].year == 2027
    with pytest.raises(RecipeError, match="needs a year"):
        build_book(load_recipe("year"), S)


@pytest.mark.parametrize("style", ["rail", "corner", "strip"])
@pytest.mark.parametrize("is_right", [True, False])
def test_year_pages_stay_in_margins(tmp_path, style, is_right):
    box = PageBox(S, is_right)
    ctx = PageContext(7, 52, S, {"style": style}, calendars.week_start(2027, 6), 2027, None, 6)
    for name in ("week", "year_goals", "year_index"):
        path = tmp_path / f"{name}.pdf"
        d = Draw(path, S.page_w, S.page_h, S)
        get_page_type(name)(d, box, ctx)
        d.next_page()
        d.save()
        img = pdfium.PdfDocument(str(path))[0].render(scale=300 / 72).to_pil().convert("L")
        m = np.array(img) < 250
        h, w = m.shape
        assert m.any()
        tol = 2
        assert not m[:px(S.margin_top) - tol].any()
        assert not m[h - px(S.margin_bottom) + tol:].any()
        assert not m[:, :px(box.margin_left) - tol].any()
        assert not m[:, w - px(box.margin_right) + tol:].any()


def test_week_page_dates_and_unknown_style(tmp_path):
    book = build_book(load_recipe("year"), S, 2027)
    pdf = tmp_path / "y.pdf"
    write_pages_pdf(book, pdf, S)
    text = PdfReader(str(pdf)).pages[5].extract_text()      # week 6: Jan 31 - Feb 6
    assert "WEEK 6" in text and "JAN / FEB" in text and "FEB" in text
    for day in ("31", "1", "2", "3", "4", "5", "6"):
        assert day in text.split()
    with pytest.raises(ValueError, match="style"):
        ctx = PageContext(1, 52, S, {"style": "nope"}, dt.date(2027, 1, 3), 2027, None, 1)
        get_page_type("week")(Draw(tmp_path / "x.pdf", S.page_w, S.page_h, S),
                              PageBox(S, True), ctx)


def test_rail_leaves_room_for_a_postit():
    from pocketjournal.yearpages import RAIL_COLS
    box = PageBox(S, True)
    assert RAIL_COLS * S.grid + 3 * 25.4 <= box.content_w


# ---- monthly journal --------------------------------------------------------------

@pytest.mark.parametrize("day,week", [
    (dt.date(2027, 3, 6), 10), (dt.date(2027, 1, 2), 1), (dt.date(2026, 12, 27), 1),
    (dt.date(2026, 12, 19), 51), (dt.date(2026, 12, 26), 52), (dt.date(2024, 12, 29), 1),
])
def test_week_number(day, week):
    assert calendars.week_number(day) == week


def test_week_number_matches_week_start():
    for year in (2025, 2026, 2027):
        for w, sunday in calendars.weeks_of_year(year):
            assert calendars.week_number(sunday) == w
            assert calendars.week_number(sunday + dt.timedelta(6)) == w


@pytest.mark.parametrize("year", [2026, 2027, 2028])
def test_monthly_recipe_every_month(year):
    r = load_recipe("monthly")
    assert r.needs == ("year", "month")
    for month in range(1, 13):
        book = build_book(r, S, year, month)
        assert len(book.pages) == 52 and book.page_numbers
        days = calendars.days_of_month(year, month)
        types = [p.type for p in book.pages]
        dailies = [p for p in book.pages if p.type == "daily"]
        assert [p.date for p in dailies] == days                # this month only
        sats = [d for d in days if d.weekday() == 5]
        partial = days[-1].weekday() != 5
        reflections = [(i, p) for i, p in enumerate(book.pages) if p.type == "week_reflection"]
        assert len(reflections) == len(sats) + partial
        ends = sats + ([days[-1]] if partial else [])
        for (i, p), end in zip(reflections, ends):
            assert book.pages[i - 1].date == end               # right after that day
            assert p.date.weekday() == 6 and p.date <= end < p.date + dt.timedelta(7)
            assert p.week == calendars.week_number(end)
        n = len(days) + len(reflections)
        assert types[n:n + 2] == ["month_review", "questions"]
        rest = types[n + 2:]
        # the fill: [lined], then idea/dots spreads, then 3-4 lined pages
        start = 0
        if rest[0] == "lined":
            assert (n + 2 + 1) % 2 == 1 and rest[1] == "idea"   # an align page
            start = 1
        end = len(rest)
        while rest[end - 1] == "lined":
            end -= 1
        assert 3 <= len(rest) - end <= 4
        spreads = rest[start:end]
        assert spreads and spreads == ["idea", "dots"] * (len(spreads) // 2)
        for i, t in enumerate(types, 1):
            if t == "idea":
                assert i % 2 == 0 and types[i] == "dots"       # left page, dots facing
        assert [p.type for p in book.cover] == ["monthly_tracker", "page_index"]
        assert book.cover[0].month == month


def test_spread_fill_rules():
    fill = {"spread": ["idea", "dots"], "align": "lined", "end": {"type": "lined", "repeat": 2}}
    for fixed in range(0, 11):
        book = build_book(recipe(pages=[{"type": "blank", "repeat": fixed}] if fixed else [],
                                 fill=fill), S)
        types = [p.type for p in book.pages]
        assert len(types) == 52 and types[-2:] == ["lined"] * 2
        assert all(i % 2 == 0 for i, t in enumerate(types, 1) if t == "idea")
    for bad in ({"spread": ["idea"], "align": "lined", "end": "lined"},
                {"spread": ["idea", "dots"], "align": "lined"},
                {"spread": ["idea", "dots"], "align": "lined", "end": "lined", "x": 1}):
        with pytest.raises(RecipeError):
            parse_recipe({"name": "t", "fill": bad})
    with pytest.raises(RecipeError, match="no room"):
        build_book(recipe(pages=[{"type": "blank", "repeat": 51}], fill=fill), S)


def test_partial_week_reflection_dates(tmp_path):
    book = build_book(load_recipe("monthly"), S, 2027, 3)       # Mon Mar 1 .. Wed Mar 31
    pdf = tmp_path / "m.pdf"
    write_pages_pdf(book, pdf, S)
    pages = PdfReader(str(pdf)).pages
    first = next(i for i, p in enumerate(book.pages) if p.type == "week_reflection")
    last = max(i for i, p in enumerate(book.pages) if p.type == "week_reflection")
    assert "Mar 1 - Mar 6" in pages[first].extract_text()       # not Feb 28
    assert "Mar 28 - Mar 31" in pages[last].extract_text()      # not Apr 3


def test_questions_and_idea_pages_draw(tmp_path):
    book = build_book(load_recipe("monthly"), S, 2027, 3)
    pdf = tmp_path / "m.pdf"
    write_pages_pdf(book, pdf, S)
    pages = PdfReader(str(pdf)).pages
    q = next(i for i, p in enumerate(book.pages) if p.type == "questions")
    assert "questions" in pages[q].extract_text() and "patterns" in pages[q - 1].extract_text()
    text = pages[next(i for i, p in enumerate(book.pages) if p.type == "idea")].extract_text()
    for label in ("Idea:", "Problem it solves:", "Who it's for:", "Smallest test:", "Next step:"):
        assert label in text


def expected_label(p):
    return {"daily": lambda: f"{'SUN MON TUE WED THU FRI SAT'.split()[(p.date.weekday() + 1) % 7]} "
                             f"{p.date.day}",
            "week_reflection": lambda: f"wk {p.week}" if p.week else "wk",
            "month_review": lambda: "patterns", "questions": lambda: "questions",
            "idea": lambda: "idea:"}.get(p.type, lambda: "")()


@pytest.mark.parametrize("year", [2026, 2027, 2028])
def test_index_labels_match_page_types(year):
    from pocketjournal.pagetypes import label_for
    for month in range(1, 13):
        book = build_book(load_recipe("monthly"), S, year, month)
        for p in book.pages:
            assert label_for(p) == expected_label(p)
            assert (label_for(p) == "") == (p.type in ("lined", "dots"))
    assert label_for(book.pages[0]).startswith(("SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"))


def test_page_index_text(tmp_path):
    book = build_book(load_recipe("monthly"), S, 2026, 11)      # Nov 1 2026 is a Sunday
    build_folder(book, tmp_path / "out", S)
    words = PdfReader(str(tmp_path / "out/cover.pdf")).pages[0].extract_text().split()
    for w in ("SUN", "MON", "wk", "patterns", "questions", "idea:", "45", "52"):
        assert w in words


def test_page_index_needs_the_book(tmp_path):
    with pytest.raises(ValueError, match="52 pages"):
        get_page_type("page_index")(Draw(tmp_path / "x.pdf", S.page_w, S.page_h, S),
                                    PageBox(S, False), PageContext(0, 52, S))


def test_after_saturday_rules():
    with pytest.raises(RecipeError, match="each: day"):
        parse_recipe({"name": "t", "pages": [{"type": "lined", "after_saturday": "blank"}]})
    with pytest.raises(RecipeError, match="only allowed"):
        parse_recipe({"name": "t", "cover": {"front": {"type": "lined", "after_saturday": "blank"}}})


def test_monthly_pages_stay_in_margins(tmp_path):
    book = build_book(load_recipe("monthly"), S, 2027, 2)       # 28 days
    ctx_for = lambda spec: PageContext(7, 52, S, spec.params, spec.date, spec.year,
                                       spec.month, spec.week, book.pages)
    specs = list(book.cover) + [next(p for p in book.pages if p.type == t) for t in
                                ("daily", "week_reflection", "month_review", "questions", "idea")]
    for spec in specs:
        for is_right in (True, False):
            box = PageBox(S, is_right)
            path = tmp_path / f"{spec.type}{is_right}.pdf"
            d = Draw(path, S.page_w, S.page_h, S)
            get_page_type(spec.type)(d, box, ctx_for(spec))
            d.next_page()
            d.save()
            img = pdfium.PdfDocument(str(path))[0].render(scale=300 / 72).to_pil().convert("L")
            m = np.array(img) < 250
            h, w = m.shape
            tol = 2
            assert m.any()
            assert not m[:px(S.margin_top) - tol].any(), spec.type
            assert not m[h - px(S.margin_bottom) + tol:].any(), spec.type
            assert not m[:, :px(box.margin_left) - tol].any(), spec.type
            assert not m[:, w - px(box.margin_right) + tol:].any(), spec.type


def test_daily_and_tracker_text(tmp_path):
    book = build_book(load_recipe("monthly"), S, 2026, 11)      # Nov 1 2026 is a Sunday
    pdf = tmp_path / "m.pdf"
    write_pages_pdf(book, pdf, S)
    pages = PdfReader(str(pdf)).pages
    assert "SUN NOV 1" in pages[0].extract_text()
    assert "WEEK 45" in pages[7].extract_text()                 # Sun Nov 1 - Sat Nov 7
    tracker = tmp_path / "tracker.pdf"
    spec = book.cover[0]
    d = Draw(tracker, S.page_w, S.page_h, S)
    get_page_type(spec.type)(d, PageBox(S, True), PageContext(0, 52, S, spec.params, spec.date,
                                                            spec.year, spec.month, spec.week))
    d.next_page()
    d.save()
    cover = PdfReader(str(tracker)).pages[0].extract_text()
    assert "NOVEMBER 2026" in cover and "30" in cover.split() and "31" not in cover.split()


def test_cli_monthly_months(tmp_path):
    cli.main(["build", "monthly", "--year", "2027", "--month", "3", "--out", str(tmp_path)])
    assert (tmp_path / "monthly-2027-03" / "print-first.pdf").is_file()
    cli.main(["build", "monthly", "--year", "2027", "--all-months", "--out", str(tmp_path)])
    assert len(list(tmp_path.glob("monthly-2027-*"))) == 12
