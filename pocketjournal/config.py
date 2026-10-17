"""The design system and every tweakable setting, in one place.

All lengths are millimeters unless a name says otherwise. Edit the defaults
here, or override single values from the command line (see cli.py).
"""
from dataclasses import dataclass
from pathlib import Path

INCH = 25.4
ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "fonts"
RECIPE_DIR = ROOT / "recipes"      # one YAML file per book


@dataclass(frozen=True)
class Settings:
    # ---- Paper: letter cut in half, printed landscape -------------------
    sheet_w: float = 8.5 * INCH      # 215.9; the fold is the vertical center line
    sheet_h: float = 5.5 * INCH      # 139.7

    # ---- Page: what is left after the fore-edge is trimmed --------------
    # The book is folded to 4.25" and trimmed 3.5" from the fold. The outer
    # (sheet_w / 2 - page_w) on each side of the sheet is cut away.
    page_w: float = 3.5 * INCH       # 88.9
    page_h: float = 5.5 * INCH       # 139.7 (centered vertically if smaller)
    book_pages: int = 52             # interior pages per book (13 sheets)

    # ---- Margins (keep content this far from each page edge) ------------
    # The printer clips the top and bottom of the sheet; measure it with the
    # calibration sheet and raise margin_top / margin_bottom if needed.
    margin_top: float = 3.0
    margin_bottom: float = 3.0
    margin_fore: float = 3.0         # the trimmed outer edge
    margin_gutter: float = 3.0       # the fold side (must exceed max creep)

    # ---- Grid ------------------------------------------------------------
    # Smallest comfortable line spacing for a 0.38 mm pen. Every ruled line,
    # dot and row snaps to this.
    grid: float = 3.0

    # ---- Line weights (mm) and grays (0 = black, 1 = white) --------------
    structure_weight: float = 0.2    # outlines, separators: black
    rule_weight: float = 0.1         # writing lines: light gray, thin
    rule_gray: float = 0.70
    separator_gray: float = 0.45     # lines between days: darker than writing rules
    tint_gray: float = 0.93          # faint fill that marks weekends
    dot_radius: float = 0.16
    dot_gray: float = 0.55
    fine_weight: float = 0.08        # calibration rulers and crosshairs

    # ---- Fonts: Courier Prime (OFL), sizes in points ---------------------
    font_regular: str = "CourierPrime"
    font_bold: str = "CourierPrime-Bold"
    font_regular_file: Path = FONT_DIR / "CourierPrime-Regular.ttf"
    font_bold_file: Path = FONT_DIR / "CourierPrime-Bold.ttf"
    font_label: float = 6.5          # fits inside one 3 mm row
    font_heading: float = 10.0
    font_page_number: float = 6.0
    font_min: float = 5.5            # nothing smaller than this

    # ---- Binding ----------------------------------------------------------
    # Creep: each sheet is pushed outward by the sheets wrapped around it.
    # Pages shift toward the fold by (sheets outside) x paper_thickness.
    paper_thickness: float = 0.1     # 20 lb copy paper

    # ---- Manual duplex alignment -----------------------------------------
    # Added to everything printed on the back side (print-second.pdf).
    # +x moves the back print right, +y moves it up, as seen on the back.
    # Measure it with the calibration sheet.
    back_offset_x: float = 0.0
    back_offset_y: float = 0.0

    # ---- Derived geometry ---------------------------------------------------
    @property
    def fold_x(self) -> float:
        return self.sheet_w / 2

    @property
    def trim_zone(self) -> float:
        """Width of the strip at each side of the sheet that is cut away."""
        return self.sheet_w / 2 - self.page_w

    @property
    def sheets_per_book(self) -> int:
        return self.book_pages // 4

    def max_creep(self, sheets: int) -> float:
        return (sheets - 1) * self.paper_thickness

    def validate(self, sheets: int | None = None) -> None:
        if self.trim_zone < 0:
            raise ValueError("two pages are wider than the sheet")
        if self.page_h > self.sheet_h:
            raise ValueError("page is taller than the sheet")
        if self.book_pages % 4:
            raise ValueError("book_pages must be a multiple of 4")
        for name in ("font_label", "font_heading", "font_page_number"):
            if getattr(self, name) < self.font_min:
                raise ValueError(f"{name} is below the {self.font_min} pt minimum")
        creep = self.max_creep(sheets or self.sheets_per_book)
        if creep >= self.margin_gutter:
            raise ValueError(
                f"creep of {creep:.2f} mm would push content past the fold; "
                f"raise margin_gutter or lower paper_thickness")


DEFAULT = Settings()
