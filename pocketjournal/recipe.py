"""Recipes: a book described in YAML, expanded into an ordered list of pages.

A recipe is a mapping with these keys (see the README for examples):

    name           short name, used for the output folder
    title          human-readable title (optional)
    page_numbers   draw page numbers in the bottom outer corner (default false)
    cover          front: and back: page types for the inside covers
    pages          ordered list of entries: type, params, repeat, each,
                   after_saturday
    fill           how to fill the book to its page count: one page type
                   (type, params), or a repeating spread (spread, align, end)
"""
import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml

from . import calendars
from .book import Book, PageSpec
from .config import RECIPE_DIR, Settings
from .pagetypes import PAGE_TYPES

EACH = {"day": ("year", "month"), "week": ("year",)}
_RECIPE_KEYS = {"name", "title", "page_numbers", "cover", "pages", "fill"}
_ENTRY_KEYS = {"type", "params", "repeat", "each", "after_saturday"}
_SPREAD_KEYS = {"spread", "align", "end"}


class RecipeError(ValueError):
    pass


@dataclass(frozen=True)
class Entry:
    type: str
    params: Mapping[str, Any] = field(default_factory=dict)
    repeat: int = 1
    each: str | None = None            # "day" (of the month) or "week" (of the year)
    after_saturday: "Entry | None" = None   # one extra page after every Saturday (`each: day`),
                                            # and after the month's last day if it is not one


@dataclass(frozen=True)
class SpreadFill:
    """Fill with a repeating spread that always starts on a left (even) page,
    then close the book with `end` (its `repeat` pages, plus one more if the
    spreads leave a page over). `align` is the page added when the next page
    would be a right-hand one."""
    spread: tuple[Entry, ...]       # the pages of one spread, left page first
    align: Entry
    end: Entry


@dataclass(frozen=True)
class Recipe:
    name: str
    title: str
    page_numbers: bool
    front: Entry
    back: Entry
    pages: tuple[Entry, ...]
    fill: Entry | SpreadFill | None

    @property
    def needs(self) -> tuple[str, ...]:
        """What a build must be told: "year" and/or "month" (empty = undated)."""
        wanted = {n for e in self.pages if e.each for n in EACH[e.each]}
        return tuple(n for n in ("year", "month") if n in wanted)


def _entry(raw: Any, where: str, allow_each: bool = False,
           allow_after: bool = False) -> Entry:
    if isinstance(raw, str):
        raw = {"type": raw}
    if not isinstance(raw, dict) or "type" not in raw:
        raise RecipeError(f"{where}: needs a page type (e.g. `type: lined`)")
    extra = set(raw) - _ENTRY_KEYS
    if "after_saturday" in raw and not allow_after:
        raise RecipeError(f"{where}: after_saturday is only allowed in `pages`")
    if extra:
        raise RecipeError(f"{where}: unknown key(s) {sorted(extra)}")
    if raw["type"] not in PAGE_TYPES:
        raise RecipeError(f"{where}: unknown page type {raw['type']!r}; "
                          f"known: {', '.join(sorted(PAGE_TYPES))}")
    repeat, each = raw.get("repeat", 1), raw.get("each")
    if not isinstance(repeat, int) or repeat < 1:
        raise RecipeError(f"{where}: repeat must be a whole number, 1 or more")
    if each is not None and (each not in EACH or not allow_each):
        raise RecipeError(f"{where}: each must be one of {sorted(EACH)} "
                          f"(and is only allowed in `pages`)")
    after = raw.get("after_saturday")
    if after is not None and each != "day":
        raise RecipeError(f"{where}: after_saturday needs `each: day`")
    return Entry(raw["type"], raw.get("params") or {}, repeat, each,
                 _entry(after, f"{where} after_saturday") if after is not None else None)


def _fill(raw: Any, where: str) -> Entry | SpreadFill:
    if not isinstance(raw, dict) or not (set(raw) & _SPREAD_KEYS):
        return _entry(raw, where)
    if set(raw) - _SPREAD_KEYS or not _SPREAD_KEYS <= set(raw):
        raise RecipeError(f"{where}: a spread fill takes exactly {sorted(_SPREAD_KEYS)}")
    if not isinstance(raw["spread"], list):
        raise RecipeError(f"{where}: spread must be a list of page types")
    spread = tuple(_entry(e, f"{where} spread[{i}]") for i, e in enumerate(raw["spread"]))
    if not spread or sum(e.repeat for e in spread) % 2:
        raise RecipeError(f"{where}: a spread needs an even number of pages")
    return SpreadFill(spread, _entry(raw["align"], f"{where} align"),
                      _entry(raw["end"], f"{where} end"))


def parse_recipe(data: Any, source: str = "recipe") -> Recipe:
    if not isinstance(data, dict):
        raise RecipeError(f"{source}: must be a YAML mapping")
    extra = set(data) - _RECIPE_KEYS
    if extra:
        raise RecipeError(f"{source}: unknown key(s) {sorted(extra)}")
    if "name" not in data:
        raise RecipeError(f"{source}: missing `name`")
    cover = data.get("cover") or {}
    if set(cover) - {"front", "back"}:
        raise RecipeError(f"{source}: cover takes only `front` and `back`")
    return Recipe(
        name=str(data["name"]),
        title=str(data.get("title", data["name"])),
        page_numbers=bool(data.get("page_numbers", False)),
        front=_entry(cover.get("front", "blank"), f"{source} cover.front"),
        back=_entry(cover.get("back", "blank"), f"{source} cover.back"),
        pages=tuple(_entry(e, f"{source} pages[{i}]", allow_each=True, allow_after=True)
                    for i, e in enumerate(data.get("pages") or [])),
        fill=_fill(data["fill"], f"{source} fill") if data.get("fill") else None)


def load_recipe(name_or_path: str | Path, recipe_dir: Path = RECIPE_DIR) -> Recipe:
    path = Path(name_or_path)
    if not path.suffix:
        path = recipe_dir / f"{name_or_path}.yaml"
    if not path.is_file():
        raise RecipeError(f"no recipe {str(name_or_path)!r} (looked for {path})")
    return parse_recipe(yaml.safe_load(path.read_text()), path.name)


def list_recipes(recipe_dir: Path = RECIPE_DIR) -> dict[str, Recipe]:
    return {p.stem: load_recipe(p) for p in sorted(recipe_dir.glob("*.yaml"))}


def build_book(recipe: Recipe, s: Settings, year: int | None = None,
               month: int | None = None) -> Book:
    """Expand a recipe into a Book of exactly `s.book_pages` pages."""
    given = {"year": year, "month": month}
    for need in recipe.needs:
        if given[need] is None:
            raise RecipeError(f"recipe {recipe.name!r} needs a {need}")
    when = {"year": year, "month": month}

    def spec(e: Entry, **ctx) -> PageSpec:
        return PageSpec(e.type, e.params, **when, **ctx)

    pages: list[PageSpec] = []
    for e in recipe.pages:
        if e.each == "day":
            items = [dict(date=d) for d in calendars.days_of_month(year, month)]
        elif e.each == "week":
            items = [dict(date=d, week=w) for w, d in calendars.weeks_of_year(year)]
        else:
            items = [{}]
        for ctx in items:
            pages += [spec(e, **ctx) for _ in range(e.repeat)]
            if e.after_saturday and (ctx["date"].weekday() == 5 or ctx is items[-1]):
                # the page covers the week that ends here (or ends with the
                # month), like `each: week`; its date is that week's Sunday
                sunday = ctx["date"] - dt.timedelta(days=(ctx["date"].weekday() + 1) % 7)
                pages.append(spec(e.after_saturday, date=sunday,
                                  week=calendars.week_number(ctx["date"])))

    if len(pages) > s.book_pages:
        raise RecipeError(f"recipe {recipe.name!r} makes {len(pages)} pages, "
                          f"more than the {s.book_pages} a book holds")
    if len(pages) < s.book_pages:
        if recipe.fill is None:
            raise RecipeError(f"recipe {recipe.name!r} makes {len(pages)} pages; "
                              f"add a `fill:` rule to reach {s.book_pages}")
        if isinstance(recipe.fill, SpreadFill):
            pages += _spread_fill(recipe, recipe.fill, len(pages), s.book_pages, spec)
        else:
            pages += [spec(recipe.fill)] * (s.book_pages - len(pages))

    return Book(recipe.name, tuple(pages), (spec(recipe.front), spec(recipe.back)),
                page_numbers=recipe.page_numbers, title=_title(recipe, year, month))


def _spread_fill(recipe: Recipe, fill: SpreadFill, have: int, total: int,
                 spec) -> list[PageSpec]:
    """Pages to add after the `have` fixed ones: an `align` page if the next
    page (number have + 1) is a right-hand one, as many whole spreads as leave
    room for `end`, then the end pages."""
    per_spread = sum(e.repeat for e in fill.spread)
    out = [spec(fill.align)] if (have + 1) % 2 else []
    room = total - have - len(out) - fill.end.repeat
    if room < 0:
        raise RecipeError(f"recipe {recipe.name!r}: no room for the end pages of its fill")
    out += [spec(e) for _spread in range(room // per_spread)
            for e in fill.spread for _page in range(e.repeat)]
    spare = room % per_spread                      # leftover pages join the end
    return out + [spec(fill.end)] * (fill.end.repeat + spare)


def _title(recipe: Recipe, year: int | None, month: int | None) -> str:
    when = "-".join(f"{v:02d}" if n == "month" else str(v)
                    for n, v in (("year", year), ("month", month))
                    if n in recipe.needs)
    return f"{recipe.title} {when}".strip()
