# Pocket Journal System

Print-ready PDFs for a hand-bound pocket notebook system. See `CLAUDE.md` for
the physical process and design system.

## Building books

    pip install -e '.[dev]'
    python -m pocketjournal                         # asks questions, then builds
    python -m pocketjournal build lined dots        # same choices as flags
    python -m pocketjournal build all --year 2027   # every book: plain, year, and 12 monthly
    python -m pocketjournal build monthly --year 2027 --month 3
    python -m pocketjournal build monthly --year 2027 --all-months
    python -m pocketjournal calibrate
    python -m pocketjournal previews                # regenerate everything in previews/

With no arguments the builder asks which book, the year and month (only for
books that need them; `all` builds all 12 months), how many signatures and the
paper thickness, shows a summary and waits for a yes. Flags answer the same
questions: `--year`, `--month`, `--all-months`, `--signatures`, `--thickness`,
`--out`. Flags are never discarded: if something is missing (say the book name
in `build --year 2027 --all-months`), only that is asked. Without a keyboard, or
when flags conflict, you get one sentence saying what to add or remove.
`build all` needs `--year` for the dated books and makes all 12 months unless
`--month` says otherwise.

`previews` rewrites the PNGs in `previews/`: every page type at final size
(`page-<type>.png`), and a contact sheet and cover spread per book.

Each book gets its own folder under `build/` with `print-first.pdf`,
`print-second.pdf`, `cover.pdf`, `pages.pdf`, a `preview.png` contact sheet,
`cover.png` and a `summary.txt`.

## Writing a recipe

A recipe is a YAML file in `recipes/`. Its file name is the book's name on the
command line. Nothing else needs code, as long as the page types exist
(`blank`, `lined` (optional `params: {label: ...}` for the header), `dots`, `index`, the year journal's `week`, `year_goals`,
`year_index`, and the monthly journal's `daily`, `week_reflection`,
`month_review`, `someday`, `monthly_tracker`, `quick_reference`; see `pocketjournal/pagetypes.py`).

```yaml
name: sampler                # used for the output folder
title: Sampler notebook      # shown in summary.txt
page_numbers: true           # number every interior page (top outer corner)

cover:                       # the two inside covers (default: blank)
  front: blank
  back: index                # a page type name, or {type: ..., params: {...}}

pages:                       # fixed pages, in order
  - type: dots
    repeat: 4                # 4 pages in a row
  - type: lined
    params: {}               # passed to the page type
  - type: lined
    each: day                # one page per day of the chosen month
                             # (`each: week`: one per week of the chosen year)
    after_saturday:          # with `each: day`: one extra page after every
      type: lined            # Saturday (its date is that week's Sunday)

fill:                        # pad with this type until the book has 52 pages
  type: lined
```

Rules:

- `repeat` makes that many pages per entry; with `each` it is that many per day
  or week.
- `each: day` makes the build ask for a year and month, `each: week` for a year.
  The page type sees them as `ctx.date`, `ctx.week` (1-52, weeks run Sunday to
  Saturday), `ctx.year` and `ctx.month`.
- A book always has 52 interior pages. If the entries make fewer, add a `fill`;
  more is an error.
- Typos (unknown keys or page types) fail with a message naming the file.

To add a page type, register a function with `@page_type("name")` in
`pocketjournal/pagetypes.py`, then use it in a recipe.

## The year journal

    python -m pocketjournal build year --year 2027

`recipes/year.yaml`: 52 numbered weekly pages (Sunday to Saturday), the year's
goals and all 52 weeks on the inside front cover, and a month-divided index on
the inside back cover. The `week` page has a one-row header (page number, which
is the week number, at the outer corner; the month, or "Jun / Jul", by the
spine), a goal area, seven days with their dates in a 6 mm rail at the outer
edge (so a 3" post-it can cover the page and the dates still show), and an
outcome area. The covers are meant to be read with the book turned a quarter
turn clockwise.

## The monthly journal

    python -m pocketjournal build monthly --year 2027 --month 3
    python -m pocketjournal build monthly --year 2027 --all-months   # 12 books

`recipes/monthly.yaml`, for one month of one year (folder `monthly-2027-03`):

- Inside front cover: the tracker. Day rows (date and weekday letter), 12 habit
  columns with room above for vertical names and below for vertical times,
  appointment lines on the right, and a half-row-offset column on the left for
  hours of sleep; vertical `hrs sleep`, `habits` and `times` labels; weekends
  have a very faint tint (`WEEKEND_TINT`, `None` turns it off). Rows are always laid out for 31 days from the top; a shorter
  month has fewer rows. Settings are at the top of `monthlypages.py`.
- Every interior page has the one-row header: page number at the outer corner,
  the page's identity by the spine (the date, `WEEK 45`, ...).
- One dated `daily` page per day: three entries, each with a writing area
  (labeled `Activity:` and `Reflections:`), an Engagement dial (LO to HI, Flow checkbox) and an Energy dial (NEG, 0, POS;
  negative half shaded), then 3 mm journal lines.
- A `week_reflection` page after every Saturday of the month, numbered like the
  year journal's weeks. The days after the month's last Saturday are reflected
  on in next month's book, where that Saturday falls.
- `month_review` (patterns, takeaways) and `someday` (notes list), then lined
  pages up to 52.
- Inside back cover: `quick_reference`, a first draft (edit `QUICK_REFERENCE`
  in `monthlypages.py`).
