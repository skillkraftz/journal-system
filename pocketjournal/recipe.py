"""Recipes: a book described in YAML, expanded into an ordered list of pages.

A recipe is a mapping with these keys (see the README for examples):

    name           short name, used for the output folder
    title          human-readable title (optional)
    page_numbers   draw page numbers in the bottom outer corner (default false)
    cover          front: and back: page types for the inside covers
    pages          ordered list of entries: type, params, repeat, each
    fill           type (and params) used to fill the book to its page count
"""
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
_ENTRY_KEYS = {"type", "params", "repeat", "each"}


class RecipeError(ValueError):
    pass


@dataclass(frozen=True)
class Entry:
    type: str
    params: Mapping[str, Any] = field(default_factory=dict)
    repeat: int = 1
    each: str | None = None            # "day" (of the month) or "week" (of the year)


@dataclass(frozen=True)
class Recipe:
    name: str
    title: str
    page_numbers: bool
    front: Entry
    back: Entry
    pages: tuple[Entry, ...]
    fill: Entry | None

    @property
    def needs(self) -> tuple[str, ...]:
        """What a build must be told: "year" and/or "month" (empty = undated)."""
        wanted = {n for e in self.pages if e.each for n in EACH[e.each]}
        return tuple(n for n in ("year", "month") if n in wanted)


def _entry(raw: Any, where: str, allow_each: bool = False) -> Entry:
    if isinstance(raw, str):
        raw = {"type": raw}
    if not isinstance(raw, dict) or "type" not in raw:
        raise RecipeError(f"{where}: needs a page type (e.g. `type: lined`)")
    extra = set(raw) - _ENTRY_KEYS
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
    return Entry(raw["type"], raw.get("params") or {}, repeat, each)


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
        pages=tuple(_entry(e, f"{source} pages[{i}]", allow_each=True)
                    for i, e in enumerate(data.get("pages") or [])),
        fill=_entry(data["fill"], f"{source} fill") if data.get("fill") else None)


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
        pages += [spec(e, **ctx) for ctx in items for _ in range(e.repeat)]

    if len(pages) > s.book_pages:
        raise RecipeError(f"recipe {recipe.name!r} makes {len(pages)} pages, "
                          f"more than the {s.book_pages} a book holds")
    if len(pages) < s.book_pages:
        if recipe.fill is None:
            raise RecipeError(f"recipe {recipe.name!r} makes {len(pages)} pages; "
                              f"add a `fill:` rule to reach {s.book_pages}")
        pages += [spec(recipe.fill)] * (s.book_pages - len(pages))

    return Book(recipe.name, tuple(pages), (spec(recipe.front), spec(recipe.back)),
                page_numbers=recipe.page_numbers, title=_title(recipe, year, month))


def _title(recipe: Recipe, year: int | None, month: int | None) -> str:
    when = "-".join(f"{v:02d}" if n == "month" else str(v)
                    for n, v in (("year", year), ("month", month))
                    if n in recipe.needs)
    return f"{recipe.title} {when}".strip()
