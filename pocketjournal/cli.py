"""Command line entry point:

    python -m pocketjournal build [lined|dots|all]
    python -m pocketjournal calibrate
"""
import argparse
from dataclasses import replace
from pathlib import Path

from . import book as books
from .calibration import write_calibration
from .config import DEFAULT
from .preview import save_pages


def _add_settings_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--out", type=Path, default=Path("build"), help="output folder")
    p.add_argument("--thickness", type=float, help="paper thickness in mm (creep)")
    p.add_argument("--back-dx", type=float, help="back-side x offset in mm")
    p.add_argument("--back-dy", type=float, help="back-side y offset in mm")


def _settings(args):
    changes = {k: v for k, v in (("paper_thickness", args.thickness),
                                 ("back_offset_x", args.back_dx),
                                 ("back_offset_y", args.back_dy)) if v is not None}
    return replace(DEFAULT, **changes)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="pocketjournal")
    sub = ap.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build", help="build a 52-page notebook")
    b.add_argument("book", nargs="?", default="all", choices=["lined", "dots", "all"])
    b.add_argument("--signatures", type=int, default=1)
    _add_settings_flags(b)
    c = sub.add_parser("calibrate", help="build the calibration sheet")
    _add_settings_flags(c)
    args = ap.parse_args(argv)
    s = _settings(args)

    if args.command == "build":
        library = books.library(s)
        for name in (library if args.book == "all" else [args.book]):
            result = books.build_book(library[name], args.out / name, s, args.signatures)
            print(f"{name}: {result['dir']}/ ({', '.join(result['files'])})")
    else:
        out = args.out / "calibration"
        first, second = write_calibration(out, s)
        for pdf in (first, second):
            save_pages(pdf, out, pdf.stem, dpi=200)
        print(f"calibration: {first}, {second}")
