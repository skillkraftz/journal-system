"""A thin reportlab wrapper: vector drawing in millimeters, y up, origin at
the bottom-left of the current page. One Draw object is one PDF file."""
from contextlib import contextmanager
from pathlib import Path

from reportlab.lib.units import mm as MM
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from .config import Settings


def register_fonts(s: Settings) -> None:
    for name, path in ((s.font_regular, s.font_regular_file),
                       (s.font_bold, s.font_bold_file)):
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(path)))


class Draw:
    def __init__(self, path: Path | str, w: float, h: float, settings: Settings):
        register_fonts(settings)
        self.s = settings
        self.w, self.h = w, h
        # invariant=1 keeps the output byte-identical between runs
        self.c = canvas.Canvas(str(path), pagesize=(w * MM, h * MM),
                               pageCompression=1, invariant=1)

    # -- document ------------------------------------------------------
    def next_page(self) -> None:
        self.c.showPage()

    def save(self) -> None:
        self.c.save()

    # -- state ----------------------------------------------------------
    @contextmanager
    def saved(self):
        self.c.saveState()
        try:
            yield
        finally:
            self.c.restoreState()

    @contextmanager
    def shifted(self, dx: float, dy: float):
        with self.saved():
            self.c.translate(dx * MM, dy * MM)
            yield

    def clip(self, x: float, y: float, w: float, h: float) -> None:
        """Clip everything after this call (use inside `saved`)."""
        p = self.c.beginPath()
        p.rect(x * MM, y * MM, w * MM, h * MM)
        self.c.clipPath(p, stroke=0, fill=0)

    # -- shapes -----------------------------------------------------------
    def _stroke(self, width: float, gray: float, dash=None) -> None:
        self.c.setStrokeGray(gray)
        self.c.setLineWidth(width * MM)
        self.c.setDash(*( (dash[0] * MM, dash[1] * MM) if dash else ([], 0) ))

    def line(self, x1, y1, x2, y2, width: float, gray: float = 0.0, dash=None):
        with self.saved():
            self._stroke(width, gray, dash)
            self.c.line(x1 * MM, y1 * MM, x2 * MM, y2 * MM)

    def rect(self, x, y, w, h, width: float, gray: float = 0.0):
        with self.saved():
            self._stroke(width, gray)
            self.c.rect(x * MM, y * MM, w * MM, h * MM, stroke=1, fill=0)

    def circle(self, x, y, r, gray: float = 0.0, width: float | None = None):
        """Filled dot when width is None, otherwise an outline."""
        with self.saved():
            if width is None:
                self.c.setFillGray(gray)
                self.c.circle(x * MM, y * MM, r * MM, stroke=0, fill=1)
            else:
                self._stroke(width, gray)
                self.c.circle(x * MM, y * MM, r * MM, stroke=1, fill=0)

    def text(self, x, y, string: str, size: float, bold=False, gray=0.0,
             anchor: str = "l"):
        """Text at baseline (x, y). anchor: l(eft), c(enter) or r(ight)."""
        size = max(size, self.s.font_min)
        with self.saved():
            self.c.setFillGray(gray)
            self.c.setFont(self.s.font_bold if bold else self.s.font_regular, size)
            draw = {"l": self.c.drawString, "c": self.c.drawCentredString,
                    "r": self.c.drawRightString}[anchor]
            draw(x * MM, y * MM, string)
