"""The calibration sheet: one two-sided half-letter sheet, printed with the
same manual duplex routine as a book.

(a) Edge rulers: millimeter rulers start at each paper edge. The first line
    that prints, on each edge, is how close to the edge the printer can reach.
(b) Alignment: crosshairs sit symmetrically about the fold line, so a front
    crosshair lands on the matching back crosshair when you hold the sheet to
    the light. Read the offset off the tick marks and enter it as
    back_offset_x / back_offset_y in config.py (or --back-dx / --back-dy).
"""
from pathlib import Path

from .config import Settings
from .draw import Draw

RULER_LENGTH = 20        # mm in from the edge
RULER_POSITIONS = (0.25, 0.75)   # along each edge, as a fraction of its length
CROSS_ARM = 6            # mm
CROSS_OFFSET = (60, 40)  # crosshair distance from the sheet center (x, y)


def _ruler(d: Draw, s: Settings, edge: str, along: float) -> None:
    """A ruler whose zero is the paper edge, running inward `RULER_LENGTH` mm;
    1 mm ticks, longer at 5 and 10, numbered every 5 mm."""
    W, H = s.sheet_w, s.sheet_h

    def at(u: float, v: float) -> tuple[float, float]:
        return {"left": (u, along + v), "right": (W - u, along + v),
                "bottom": (along + v, u), "top": (along + v, H - u)}[edge]

    w = s.fine_weight
    d.line(*at(0, 0), *at(RULER_LENGTH, 0), w)
    for u in range(RULER_LENGTH + 1):
        tick = 3 if u % 10 == 0 else 2 if u % 5 == 0 else 1
        d.line(*at(u, 0), *at(u, tick), w)
        if u and u % 5 == 0:
            x, y = at(u, 3.6)
            if edge in ("left", "right"):
                d.text(x, y, str(u), s.font_min, anchor="c")
            else:
                d.text(x, y - 0.7, str(u), s.font_min)


def _crosshair(d: Draw, s: Settings, x: float, y: float) -> None:
    w = s.fine_weight
    d.line(x - CROSS_ARM, y, x + CROSS_ARM, y, w)
    d.line(x, y - CROSS_ARM, x, y + CROSS_ARM, w)
    for i in range(-CROSS_ARM, CROSS_ARM + 1):
        tick = 0.8 if i % 5 == 0 else 0.4
        d.line(x + i, y - tick, x + i, y + tick, w)
        d.line(x - tick, y + i, x + tick, y + i, w)
    d.circle(x, y, 2, width=w)


def draw_side(d: Draw, s: Settings, side: str) -> None:
    W, H, fold = s.sheet_w, s.sheet_h, s.fold_x
    sw = s.structure_weight

    # fold line and trim lines, identical on both sides
    d.line(fold, 0, fold, H, sw, dash=(2, 1))
    for x in (fold - s.page_w, fold + s.page_w):
        d.line(x, 0, x, H, sw)
    d.text(fold + 1.5, H - 8, "fold", s.font_label)
    d.text(fold - s.page_w + 1.5, H - 8, "trim", s.font_label)
    d.text(fold + s.page_w - 1.5, H - 8, "trim", s.font_label, anchor="r")

    # (a) edge rulers
    for edge, length in (("left", H), ("right", H), ("bottom", W), ("top", W)):
        for frac in RULER_POSITIONS:
            _ruler(d, s, edge, length * frac)

    # (b) matching crosshairs: symmetric about the fold, plus the center
    cx, cy = CROSS_OFFSET
    for x in (fold - cx, fold + cx):
        for y in (H / 2 - cy, H / 2 + cy):
            _crosshair(d, s, x, y)
    _crosshair(d, s, fold, H / 2)

    # labels
    name = "FRONT  print-first.pdf" if side == "front" else "BACK  print-second.pdf"
    d.text(fold - 4, H / 2 + 30, name, s.font_heading - 1, bold=True, anchor="r")
    notes = ["Edge rulers: the first line that prints is the",
             "printer's reach, in mm from the paper edge.",
             "Hold to the light: front and back crosshairs",
             "should coincide. Read any gap off the ticks."]
    for i, line in enumerate(notes):
        d.text(fold - 4, H / 2 + 24 - i * 3.2, line, s.font_label, gray=0.3, anchor="r")


def write_calibration(out_dir: Path, s: Settings) -> tuple[Path, Path]:
    """print-first (the front) and print-second (the back, with the back
    offset applied) for one sheet."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for side in ("front", "back"):
        path = out_dir / f"calibration-print-{'first' if side == 'front' else 'second'}.pdf"
        d = Draw(path, s.sheet_w, s.sheet_h, s)
        dx, dy = (s.back_offset_x, s.back_offset_y) if side == "back" else (0, 0)
        with d.shifted(dx, dy):
            draw_side(d, s, side)
        d.save()
        paths.append(path)
    return paths[0], paths[1]
