"""PNG previews at final size, rendered from the PDFs with pypdfium2."""
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFont

from .config import Settings


def render_pdf(path: Path | str, dpi: int = 200) -> list[Image.Image]:
    pdf = pdfium.PdfDocument(str(path))
    try:
        return [pdf[i].render(scale=dpi / 72).to_pil().convert("RGB")
                for i in range(len(pdf))]
    finally:
        pdf.close()


def save_pages(pdf_path: Path | str, out_dir: Path, stem: str, dpi: int = 200) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, img in enumerate(render_pdf(pdf_path, dpi), 1):
        p = out_dir / f"{stem}-{i:02d}.png"
        img.save(p, dpi=(dpi, dpi))
        paths.append(p)
    return paths


def contact_sheet(pdf_path: Path | str, out_path: Path, s: Settings,
                  columns: int = 8, dpi: int = 60) -> Path:
    """Every page at final size (scaled by dpi), numbered, on a gray table."""
    pages = render_pdf(pdf_path, dpi)
    pad, label_h = 14, 16
    cell_w, cell_h = pages[0].width, pages[0].height
    rows = -(-len(pages) // columns)
    sheet = Image.new("RGB", (columns * (cell_w + pad) + pad,
                              rows * (cell_h + label_h + pad) + pad), (222, 222, 222))
    font = ImageFont.truetype(str(s.font_regular_file), 11)
    draw = ImageDraw.Draw(sheet)
    for i, img in enumerate(pages):
        x = pad + (i % columns) * (cell_w + pad)
        y = pad + (i // columns) * (cell_h + label_h + pad)
        sheet.paste(img, (x, y))
        draw.rectangle([x - 1, y - 1, x + cell_w, y + cell_h], outline=(150, 150, 150))
        draw.text((x + cell_w // 2, y + cell_h + 3), str(i + 1), fill=(60, 60, 60),
                  font=font, anchor="mt")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, dpi=(dpi, dpi))
    return out_path
