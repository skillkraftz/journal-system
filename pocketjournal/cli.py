"""One entry point, two ways to use it.

    python -m pocketjournal                       ask questions, then build
    python -m pocketjournal build lined dots      same choices as flags
    python -m pocketjournal build monthly --year 2027 --all-months
    python -m pocketjournal calibrate
"""
import argparse
import datetime as dt
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

from . import book as books
from . import recipe as recipes
from .calibration import write_calibration
from .config import DEFAULT, RECIPE_DIR, Settings
from .preview import save_pages

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


@dataclass
class BuildRequest:
    """Everything a build needs; the questions and the flags both fill it in."""
    recipes: list[str]
    year: int | None = None
    months: list[int] | None = None      # None when no recipe needs a month
    signatures: int = 1
    out: Path = Path("build")


def build_folders(req: BuildRequest, s: Settings, recipe_dir: Path = RECIPE_DIR):
    """[(recipe, year, month, output folder)] for every book the request makes."""
    jobs = []
    for name in req.recipes:
        r = recipes.load_recipe(name, recipe_dir)
        for m in (req.months or [None]) if "month" in r.needs else [None]:
            label = r.name
            if "year" in r.needs:
                label += f"-{req.year}"
            if m:
                label += f"-{m:02d}"
            jobs.append((r, req.year if "year" in r.needs else None, m, req.out / label))
    return jobs


def run(req: BuildRequest, s: Settings, recipe_dir: Path = RECIPE_DIR,
        say: Callable[[str], None] = print) -> list[Path]:
    done = []
    for r, year, month, folder in build_folders(req, s, recipe_dir):
        book = recipes.build_book(r, s, year, month)
        result = books.build_book(book, folder, s, req.signatures)
        say(f"{folder}/  ({', '.join(result['files'])})")
        done.append(folder)
    return done


def undated(recipe_dir: Path = RECIPE_DIR) -> list[str]:
    return [n for n, r in recipes.list_recipes(recipe_dir).items() if not r.needs]


# ---- Questions --------------------------------------------------------------

def _ask(prompt: str, default, ask: Callable[[str], str], cast=str):
    while True:
        reply = ask(f"{prompt} [{default}]: ").strip()
        try:
            return cast(reply) if reply else default
        except ValueError:
            print("  please enter a valid value")


def interview(s: Settings, recipe_dir: Path = RECIPE_DIR, ask=input,
              say=print, today: dt.date | None = None):
    """Ask the questions. Returns (BuildRequest, Settings) or None if declined."""
    today = today or dt.date.today()
    available = recipes.list_recipes(recipe_dir)
    names = list(available)
    say("Pocket journal builder\n")
    for i, n in enumerate(names, 1):
        dated = f" (needs {' and '.join(available[n].needs)})" if available[n].needs else ""
        say(f"  {i}. {n} - {available[n].title}{dated}")
    say("  or several, separated by commas; 'all' for every undated book\n")
    while True:
        reply = _ask("Which book", names[0], ask)
        if reply == "all":
            chosen = undated(recipe_dir)
        else:
            parts = [p.strip() for p in reply.split(",")]
            chosen = [names[int(p) - 1] if p.isdigit() and 0 < int(p) <= len(names) else p
                      for p in parts]
        if chosen and all(c in available for c in chosen):
            break
        say("  not a book I know")
    needs = {n for c in chosen for n in available[c].needs}

    year, months = None, None
    if needs:
        year = _ask("Year", today.year, ask, int)
    if "month" in needs:
        while True:
            reply = _ask("Month (1-12, or 'all' for all 12)", today.month, ask, str)
            if str(reply).lower() == "all":
                months = list(range(1, 13))
                break
            if str(reply).isdigit() and 1 <= int(reply) <= 12:
                months = [int(reply)]
                break
            say("  enter 1-12 or 'all'")
    signatures = _ask("Signatures", 1, ask, int)
    thickness = _ask("Paper thickness in mm", s.paper_thickness, ask, float)
    out = Path(_ask("Output folder", "build", ask))

    s = replace(s, paper_thickness=thickness)
    req = BuildRequest(chosen, year, months, signatures, out)
    say("\nSummary")
    say(f"  books:      {', '.join(chosen)}")
    if year:
        say(f"  year:       {year}")
    if months:
        say("  months:     " + ("all 12" if len(months) == 12 else MONTHS[months[0] - 1]))
    say(f"  signatures: {signatures}")
    say(f"  thickness:  {thickness} mm")
    say(f"  output:     {out}/ ({len(build_folders(req, s, recipe_dir))} book folder(s))")
    if _ask("Build now? (y/n)", "y", ask).lower().startswith("y"):
        return req, s
    return None


# ---- Command line -----------------------------------------------------------

def _add_settings_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--out", type=Path, default=Path("build"), help="output folder")
    p.add_argument("--thickness", type=float, help="paper thickness in mm (creep)")
    p.add_argument("--back-dx", type=float, help="back-side x offset in mm")
    p.add_argument("--back-dy", type=float, help="back-side y offset in mm")


def _settings(args) -> Settings:
    changes = {k: v for k, v in (("paper_thickness", args.thickness),
                                 ("back_offset_x", args.back_dx),
                                 ("back_offset_y", args.back_dy)) if v is not None}
    return replace(DEFAULT, **changes)


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="pocketjournal",
        description="Run with no arguments to be asked questions instead.")
    sub = ap.add_subparsers(dest="command")
    b = sub.add_parser("build", help="build books from recipes")
    b.add_argument("books", nargs="*", metavar="BOOK",
                   help="recipe names or .yaml paths; 'all' = every undated recipe; "
                        "none = ask questions")
    b.add_argument("--year", type=int, help="for recipes that are dated")
    b.add_argument("--month", type=int, help="1-12, for monthly recipes")
    b.add_argument("--all-months", action="store_true", help="build all 12 months")
    b.add_argument("--signatures", type=int, default=1)
    b.add_argument("--recipes", type=Path, default=RECIPE_DIR, help="recipe folder")
    _add_settings_flags(b)
    c = sub.add_parser("calibrate", help="build the calibration sheet")
    _add_settings_flags(c)
    return ap


def main(argv=None) -> None:
    ap = _parser()
    args = ap.parse_args(argv)

    if args.command == "calibrate":
        s, out = _settings(args), args.out / "calibration"
        first, second = write_calibration(out, s)
        for pdf in (first, second):
            save_pages(pdf, out, pdf.stem, dpi=200)
        print(f"calibration: {first}, {second}")
        return

    if args.command is None or not args.books:      # no choices given: ask
        answered = interview(DEFAULT)
        if answered is None:
            print("Nothing built.")
            return
        req, s = answered
        run(req, s)
        return

    s, recipe_dir = _settings(args), args.recipes
    chosen = undated(recipe_dir) if args.books == ["all"] else args.books
    months = list(range(1, 13)) if args.all_months else [args.month] if args.month else None
    try:
        loaded = [recipes.load_recipe(n, recipe_dir) for n in chosen]
        for r in loaded:
            for need, value in (("year", args.year),
                                ("month", months)):
                if need in r.needs and not value:
                    ap.error(f"{r.name} needs --{need}" + (" or --all-months" if need == "month" else ""))
        run(BuildRequest(chosen, args.year, months, args.signatures, args.out), s, recipe_dir)
    except (recipes.RecipeError, ValueError) as e:
        ap.exit(1, f"error: {e}\n")
