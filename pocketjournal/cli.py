"""One entry point, two ways to use it.

    python -m pocketjournal                       ask questions, then build
    python -m pocketjournal build lined dots      same choices as flags
    python -m pocketjournal build monthly --year 2027 --all-months
    python -m pocketjournal build all --year 2027   year + all 12 months + plain books
    python -m pocketjournal calibrate
    python -m pocketjournal previews                regenerate previews/

Flags are never thrown away: if one thing is missing (say the book name), only
that is asked, with the flags you gave already filled in.
"""
import argparse
import datetime as dt
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

from . import book as books
from . import recipe as recipes
from .calibration import write_calibration
from .config import DEFAULT, RECIPE_DIR, ROOT, Settings
from .gallery import write_previews
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


class UsageError(ValueError):
    """The flags are missing something or contradict each other; the message
    is one sentence saying what to change."""


@dataclass
class Given:
    """What the flags already said. `books` holds recipe names, or the single
    word 'all' for every recipe."""
    books: list[str]
    year: int | None = None
    months: list[int] | None = None
    month_flag: bool = False              # --month or --all-months was used
    signatures: int | None = None
    out: Path | None = None

    @property
    def nothing(self) -> bool:
        return not (self.books or self.year or self.months or
                    self.signatures or self.out)


def _books_phrase(recipe_dir: Path) -> str:
    return ", ".join([*recipes.list_recipes(recipe_dir), "all"])


def _expand(names: list[str], recipe_dir: Path) -> list[str]:
    """'all' means every recipe; anything else must be a recipe."""
    available = recipes.list_recipes(recipe_dir)
    if "all" in names:
        return list(available)
    for n in names:
        if n not in available and not Path(n).suffix:
            raise UsageError(f"There is no book called {n!r}; choose from "
                             f"{_books_phrase(recipe_dir)}.")
    return names


def resolve(given: Given, s: Settings, recipe_dir: Path = RECIPE_DIR, ask=None,
            say=print, today: dt.date | None = None):
    """Turn the flags into a BuildRequest, asking only for what is missing.

    With nothing given at all, ask every question and confirm (the full
    interview). With `ask=None` nothing is asked: a missing choice raises a
    UsageError naming what to add. Returns (BuildRequest, Settings), or None
    if the owner declines at the final question."""
    today = today or dt.date.today()
    available = recipes.list_recipes(recipe_dir)
    full = given.nothing
    if ask is None and not given.books:
        raise UsageError(f"Add a book name to build: one of {_books_phrase(recipe_dir)}.")
    all_books = "all" in given.books
    chosen = _expand(given.books, recipe_dir) if given.books else None
    if chosen is None:
        say("Pocket journal builder\n")
        for i, n in enumerate(available, 1):
            dated = f" (needs {' and '.join(available[n].needs)})" if available[n].needs else ""
            say(f"  {i}. {n} - {available[n].title}{dated}")
        say("  or several, separated by commas; 'all' for every book\n")
        names = list(available)
        while True:
            reply = _ask("Which book", names[0], ask)
            parts = [p.strip() for p in reply.split(",")]
            parts = [names[int(p) - 1] if p.isdigit() and 0 < int(p) <= len(names) else p
                     for p in parts]
            try:
                chosen, all_books = _expand(parts, recipe_dir), "all" in parts
                break
            except UsageError:
                say("  not a book I know")
    loaded = [recipes.load_recipe(n, recipe_dir) for n in chosen]
    needs = {n for r in loaded for n in r.needs}

    # flags that no chosen book can use are conflicts, not something to drop
    for need, flag in (("year", given.year is not None), ("month", given.month_flag)):
        if flag and need not in needs:
            names = ", ".join(r.name for r in loaded)
            flag_name = "--year" if need == "year" else "--month/--all-months"
            raise UsageError(f"{names} has no {need} to set, so remove {flag_name} or "
                             f"add a book that uses it, such as "
                             f"{_first_needing(available, need)}.")

    year, months = given.year, given.months
    wanted = []
    if "year" in needs and year is None:
        wanted.append("--year YYYY")
    if "month" in needs and months is None and not all_books:
        wanted.append("--month 1-12 or --all-months")
    if wanted and ask is None:
        raise UsageError(f"To build {', '.join(r.name for r in loaded)}, add "
                         f"{' and '.join(wanted)}.")
    if "year" in needs and year is None:
        year = _ask("Year", today.year, ask, int)
    if "month" in needs and months is None:
        if all_books:
            months = list(range(1, 13))
        while months is None:
            reply = _ask("Month (1-12, or 'all' for all 12)", today.month, ask, str)
            if str(reply).lower() == "all":
                months = list(range(1, 13))
            elif str(reply).isdigit() and 1 <= int(reply) <= 12:
                months = [int(reply)]
            else:
                say("  enter 1-12 or 'all'")

    signatures = given.signatures or 1
    out = given.out or Path("build")
    if full:
        signatures = _ask("Signatures", 1, ask, int)
        thickness = _ask("Paper thickness in mm", s.paper_thickness, ask, float)
        out = Path(_ask("Output folder", "build", ask))
        s = replace(s, paper_thickness=thickness)
    req = BuildRequest(chosen, year, months, signatures, out)
    if not full:
        return req, s
    say("\nSummary")
    say(f"  books:      {', '.join(chosen)}")
    if year:
        say(f"  year:       {year}")
    if months:
        say("  months:     " + ("all 12" if len(months) == 12 else MONTHS[months[0] - 1]))
    say(f"  signatures: {signatures}")
    say(f"  thickness:  {s.paper_thickness} mm")
    say(f"  output:     {out}/ ({len(build_folders(req, s, recipe_dir))} book folder(s))")
    if _ask("Build now? (y/n)", "y", ask).lower().startswith("y"):
        return req, s
    return None


def _first_needing(available: dict, need: str) -> str:
    return next((n for n, r in available.items() if need in r.needs), "year")


# ---- Questions --------------------------------------------------------------

def _ask(prompt: str, default, ask: Callable[[str], str], cast=str):
    while True:
        reply = ask(f"{prompt} [{default}]: ").strip()
        try:
            return cast(reply) if reply else default
        except ValueError:
            print("  please enter a valid value")


def interview(s: Settings, recipe_dir: Path = RECIPE_DIR, ask=input,
              say=print, today: dt.date | None = None, given: Given | None = None):
    """Ask the questions. With nothing `given`, all of them; otherwise only
    what the flags left out. Returns (BuildRequest, Settings) or None."""
    return resolve(given or Given([]), s, recipe_dir, ask, say, today)


# ---- Command line -----------------------------------------------------------

def _add_settings_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--out", type=Path, help="output folder (default: build)")
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
                   help="recipe names or .yaml paths; 'all' = every recipe "
                        "(dated ones need --year); none = ask")
    b.add_argument("--year", type=int, help="for recipes that are dated")
    b.add_argument("--month", type=int, help="1-12, for monthly recipes")
    b.add_argument("--all-months", action="store_true", help="build all 12 months")
    b.add_argument("--signatures", type=int)
    b.add_argument("--recipes", type=Path, default=RECIPE_DIR, help="recipe folder")
    _add_settings_flags(b)
    c = sub.add_parser("calibrate", help="build the calibration sheet")
    _add_settings_flags(c)
    v = sub.add_parser("previews", help="regenerate everything in previews/")
    v.add_argument("--dir", type=Path, default=ROOT / "previews", help="output folder")
    _add_settings_flags(v)
    return ap


def _given(args) -> Given:
    if args.month is not None and args.all_months:
        raise UsageError("Use either --month or --all-months, not both.")
    if args.month is not None and not 1 <= args.month <= 12:
        raise UsageError(f"--month must be a number from 1 to 12, not {args.month}.")
    months = list(range(1, 13)) if args.all_months else (
        [args.month] if args.month is not None else None)
    given = Given(args.books, args.year, months,
                  args.month is not None or args.all_months, args.signatures, args.out)
    if given.signatures is not None and given.signatures < 1:
        raise UsageError("--signatures must be 1 or more.")
    return given


def main(argv=None, ask=None) -> None:
    """`ask` answers questions; by default the keyboard, if there is one."""
    ap = _parser()
    args = ap.parse_args(argv)
    if ask is None and sys.stdin is not None and sys.stdin.isatty():
        ask = input

    if args.command == "calibrate":
        s, out = _settings(args), (args.out or Path("build")) / "calibration"
        first, second = write_calibration(out, s)
        for pdf in (first, second):
            save_pages(pdf, out, pdf.stem, dpi=200)
        print(f"calibration: {first}, {second}")
        return

    if args.command == "previews":
        for path in write_previews(args.dir, _settings(args)):
            print(path)
        return

    if args.command is None:                        # bare: ask everything
        args = ap.parse_args(["build"])
    try:
        given = _given(args)
        answered = resolve(given, _settings(args), args.recipes, ask)
    except (UsageError, recipes.RecipeError) as e:
        ap.exit(2, f"{ap.prog}: error: {e}\n")
    if answered is None:
        print("Nothing built.")
        return
    req, s = answered
    try:
        run(req, s, args.recipes)
    except (recipes.RecipeError, ValueError) as e:
        ap.exit(1, f"error: {e}\n")
