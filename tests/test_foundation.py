import io
from dataclasses import replace

import numpy as np
import pypdfium2 as pdfium
import pytest
from pypdf import PdfReader

from pocketjournal import imposition as imp
from pocketjournal.book import build_book, library, write_pages_pdf
from pocketjournal.calibration import write_calibration
from pocketjournal.config import DEFAULT as S
from pocketjournal.draw import Draw
from pocketjournal.page import PageBox, PageContext
from pocketjournal.pagetypes import PAGE_TYPES, get_page_type

MM = 72 / 25.4
DPI = 300


def ink(path, page=0, dpi=DPI):
    """Dark-pixel mask of a PDF page (True where anything is printed)."""
    pdf = pdfium.PdfDocument(str(path))
    img = pdf[page].render(scale=dpi / 72).to_pil().convert("L")
    pdf.close()
    return np.array(img) < 250


def cols(mm_x, dpi=DPI):
    return int(round(mm_x / 25.4 * dpi))


def label_page(d, n, is_right):
    d.text(10, 10, f"P{n}", 10)


def page_labels(path):
    return [PdfReader(str(path)).pages[i].extract_text().split()
            for i in range(len(PdfReader(str(path)).pages))]


def test_registry():
    assert {"blank", "lined", "dots"} <= set(PAGE_TYPES)
    with pytest.raises(KeyError):
        get_page_type("nope")


def test_saddle_stitch_order_8_pages():
    (sig,) = imp.impose(8, S)
    assert [(x.front.left, x.front.right, x.back.left, x.back.right) for x in sig.sheets] == [
        (8, 1, 2, 7), (6, 3, 4, 5)]


@pytest.mark.parametrize("pages", [4, 12, 52])
def test_every_page_once_and_spreads_sum(pages):
    (sig,) = imp.impose(pages, S)
    seen = []
    for sh in sig.sheets:
        for side in (sh.front, sh.back):
            assert side.left + side.right == pages + 1
            seen += [side.left, side.right]
    assert sorted(seen) == list(range(1, pages + 1))
    assert len(sig.sheets) == pages // 4


def test_multiple_signatures_pad_with_blanks():
    sigs = imp.impose(10, S, signatures=2)
    assert [g.pages for g in sigs] == [8, 8]
    assert sigs[1].first_page == 9
    pages = [p for g in sigs for sh in g.sheets for side in (sh.front, sh.back)
             for p in (side.left, side.right)]
    assert sorted(p for p in pages if p) == list(range(1, 11))
    assert pages.count(None) == 6


def test_duplex_order_matches_booklet():
    # reference/booklet: sheets alternate front/back; fronts = odd pages
    # reversed, backs = even pages in order.
    n = 13
    flat = [(k, side) for k in range(n) for side in ("f", "b")]
    first = [k for k, side in reversed([x for x in flat if x[1] == "f"])]
    second = [k for k, side in flat if side == "b"]
    assert imp.duplex_order(n) == (first, second)


def test_duplex_files(tmp_path):
    (sig,) = imp.impose(8, S)
    f, b = tmp_path / "f.pdf", tmp_path / "b.pdf"
    imp.write_signature(sig, label_page, S, f, b)
    # fronts in reverse sheet order, backs in forward order
    assert [sorted(x) for x in page_labels(f)] == [["P3", "P6"], ["P1", "P8"]]
    assert [sorted(x) for x in page_labels(b)] == [["P2", "P7"], ["P4", "P5"]]


def test_duplex_file_page_counts(tmp_path):
    book = library(S)["lined"]
    build_book(book, tmp_path, S)
    assert len(PdfReader(str(tmp_path / "print-first.pdf")).pages) == 13
    assert len(PdfReader(str(tmp_path / "print-second.pdf")).pages) == 13
    assert len(PdfReader(str(tmp_path / "pages.pdf")).pages) == 52
    assert len(PdfReader(str(tmp_path / "cover.pdf")).pages) == 1


def test_sheet_size_is_half_letter(tmp_path):
    build_book(library(S)["dots"], tmp_path, S)
    box = PdfReader(str(tmp_path / "print-first.pdf")).pages[0].mediabox
    assert float(box.width) == pytest.approx(8.5 * 72, abs=0.01)
    assert float(box.height) == pytest.approx(5.5 * 72, abs=0.01)


def test_centering_and_geometry():
    (sig,) = imp.impose(52, S)
    lx, _ = imp.page_origin(False, 0, S)
    rx, ry = imp.page_origin(True, 0, S)
    assert lx == pytest.approx(S.trim_zone) == pytest.approx(19.05)
    assert rx == pytest.approx(S.fold_x)
    assert rx + S.page_w == pytest.approx(S.sheet_w - S.trim_zone)
    assert ry == 0
    # spread is symmetric about the fold
    assert S.fold_x - lx == pytest.approx(rx + S.page_w - S.fold_x)


def test_creep():
    (sig,) = imp.impose(52, S)
    assert [sh.creep for sh in sig.sheets] == pytest.approx(
        [k * S.paper_thickness for k in range(13)])
    assert sig.sheets[0].creep == 0
    assert sig.sheets[-1].creep == pytest.approx(1.2)
    lx, _ = imp.page_origin(False, 1.2, S)
    rx, _ = imp.page_origin(True, 1.2, S)
    assert lx == pytest.approx(S.trim_zone + 1.2)      # moved right, toward fold
    assert rx == pytest.approx(S.fold_x - 1.2)         # moved left, toward fold


def test_creep_cannot_cross_fold():
    with pytest.raises(ValueError):
        replace(S, paper_thickness=0.5).validate()


def test_nothing_in_trim_zone(tmp_path):
    thick = replace(S, paper_thickness=0.2)   # exaggerate creep
    for name, book in library(thick).items():
        out = tmp_path / name
        build_book(book, out, thick)
        for pdf in ("print-first.pdf", "print-second.pdf", "cover.pdf"):
            n = len(PdfReader(str(out / pdf)).pages)
            for i in range(n):
                m = ink(out / pdf, i)
                assert m.any() or pdf == "cover.pdf"   # plain covers are blank
                zone = cols(thick.trim_zone) - 1
                assert not m[:, :zone].any() and not m[:, -zone:].any()


def test_nothing_in_page_margins(tmp_path):
    for name in ("lined", "dots", "blank"):
        for is_right in (True, False):
            path = tmp_path / f"{name}{is_right}.pdf"
            d = Draw(path, S.page_w, S.page_h, S)
            box = PageBox(S, is_right)
            get_page_type(name)(d, box, PageContext(1, 52, S))
            d.next_page()
            d.save()
            m = ink(path)
            h, w = m.shape
            if name == "blank":
                assert not m.any()
                continue
            assert m.any()
            tol = 2   # px of antialiasing slack
            assert not m[:cols(S.margin_top) - tol].any()
            assert not m[h - cols(S.margin_bottom) + tol:].any()
            assert not m[:, :cols(box.margin_left) - tol].any()
            assert not m[:, w - cols(box.margin_right) + tol:].any()


def test_grid_is_centered_on_3mm():
    g = PageBox(S, True).grid_area()
    assert (g.cols, g.rows) == (27, 44)
    box = PageBox(S, True)
    assert g.x0 - box.x0 == pytest.approx(box.x1 - g.x1)
    assert g.y0 - box.y0 == pytest.approx(box.y1 - g.y1)


def test_back_offset_moves_back_only(tmp_path):
    book = library(S)["lined"]
    shifted = replace(S, back_offset_x=1.0, back_offset_y=-0.5)
    a, b = tmp_path / "a", tmp_path / "b"
    build_book(book, a, S)
    build_book(book, b, shifted)
    assert (a / "print-first.pdf").read_bytes() == (b / "print-first.pdf").read_bytes()
    ma, mb = ink(a / "print-second.pdf"), ink(b / "print-second.pdf")

    def bbox(m):
        ys, xs = np.where(m)
        return xs.min(), xs.max(), ys.min(), ys.max()
    x0a, x1a, _, _ = bbox(ma)
    x0b, x1b, _, _ = bbox(mb)
    assert x0b - x0a == pytest.approx(cols(1.0), abs=2)


def test_calibration(tmp_path):
    first, second = write_calibration(tmp_path, S)
    for p in (first, second):
        m = ink(p)
        assert m[:, :3].any() and m[:, -3:].any()     # rulers reach every edge
        assert m[:3].any() and m[-3:].any()
    shifted = replace(S, back_offset_x=2.0)
    _, second2 = write_calibration(tmp_path / "s", shifted)
    xs = lambda path: np.where(ink(path))[1]
    assert xs(second2).min() >= xs(second).min()
    assert first.read_bytes() == write_calibration(tmp_path / "t", shifted)[0].read_bytes()
