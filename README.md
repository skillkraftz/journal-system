# Pocket Journal System

Print-ready PDFs for a hand-bound pocket notebook system. See `CLAUDE.md` for
the physical process and design system.

## Building books

    pip install -e '.[dev]'
    python -m pocketjournal                         # asks questions, then builds
    python -m pocketjournal build lined dots        # same choices as flags
    python -m pocketjournal build all               # every recipe that needs no date
    python -m pocketjournal build monthly --year 2027 --month 3
    python -m pocketjournal build monthly --year 2027 --all-months
    python -m pocketjournal calibrate

With no arguments the builder asks which book, the year and month (only for
books that need them; `all` builds all 12 months), how many signatures and the
paper thickness, shows a summary and waits for a yes. Flags answer the same
questions: `--year`, `--month`, `--all-months`, `--signatures`, `--thickness`,
`--out`.

Each book gets its own folder under `build/` with `print-first.pdf`,
`print-second.pdf`, `cover.pdf`, `pages.pdf`, a `preview.png` contact sheet,
`cover.png` and a `summary.txt`.

## Writing a recipe

A recipe is a YAML file in `recipes/`. Its file name is the book's name on the
command line. Nothing else needs code, as long as the page types exist
(`blank`, `lined`, `dots`, `index`, the year journal's `week`, `year_goals`,
`year_index`, and the monthly journal's `daily`, `week_reflection`,
`month_review`, `questions`, `idea`, `monthly_tracker`, `page_index`; see `pocketjournal/pagetypes.py`).

```yaml
name: sampler                # used for the output folder
title: Sampler notebook      # shown in summary.txt
page_numbers: true           # number every interior page (bottom outer corner)

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
      type: lined            # Saturday, and after the month's last day if it
                             # is not one (its date is that week's Sunday)

fill:                        # pad with this type until the book has 52 pages
  type: lined
```

`fill` can also repeat a spread, so a book can end with spreads that always
start on a left (even) page:

```yaml
fill:
  spread: [idea, dots]       # pages of one spread, left page first (even count)
  align: lined               # added if the next page would be a right-hand one
  end:
    type: lined              # closing pages ...
    repeat: 3                # ... this many, plus one if a page is left over
```

The spreads fill whatever room is left after the fixed pages and the end pages.

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
the inside back cover. The `week` page takes `params: {style: ...}`, which only
changes how days are labeled so a 3" post-it can cover the page and the dates
still show: `rail` (default; dates in a 6 mm rail at the outer edge), `corner`
(small label at the start of each day) or `strip` (all seven dates under the
header). The covers are meant to be read with the book turned a quarter turn
clockwise.

## The monthly journal

    python -m pocketjournal build monthly --year 2027 --month 3
    python -m pocketjournal build monthly --year 2027 --all-months   # 12 books

`recipes/monthly.yaml`, for one month of one year (folder `monthly-2027-03`):

- Inside front cover: the tracker. Day rows (date and weekday letter), 12 habit
  columns with room above for vertical names and below for vertical times,
  appointment lines on the right, and a half-row-offset column on the left for
  hours of sleep. Rows are always laid out for 31 days from the top; a shorter
  month has fewer rows. Settings are at the top of `monthlypages.py`.
- One dated `daily` page per day: three entries, each with a writing area, an
  Engagement dial (LO to HI, Flow checkbox) and an Energy dial (NEG, 0, POS;
  negative half shaded), then 3 mm journal lines.
- A `week_reflection` page after every Saturday of the month, numbered like the
  year journal's weeks, plus one more after the last day if the month does not
  end on a Saturday. Its header shows only the week's dates inside the month
  (the first and last weeks can be partial). Nothing comes from neighboring
  months.
- Month end: `month_review` (patterns & takeaways), then `questions`: two
  writing rows per question and a tiny box in the margin column to tick when
  the question has moved into a book-notes journal.
- Ideas spreads fill the rest: an `idea` helper page on the left (Idea, Problem
  it solves, Who it's for, Smallest test, Next step, free lines; edit
  `IDEA_PROMPTS` in `monthlypages.py`) facing a `dots` page. Spreads start on a
  left page (a lined page is added if needed), and the book ends with 3-4 lined
  pages. See the `fill` rule in `recipes/monthly.yaml`.
- Inside back cover: `page_index`, all 52 pages in two sideways columns of 26
  strips with a page number zone and room to write. Known pages carry a small
  gray label (`SUN 1`, `wk 45`, `patterns`, `questions`, `idea:`); lined and
  dot pages stay blank. A page type gets a label with `@index_label("name")`.

## Plain books

`lined` and `dots` end with the `index` page type: the same sideways two-column
style as the year journal's covers, 26 pages per column plus a date field
("goal post") after pages 13, 26, 39 and 52 for when you reached that point.
Page 26, the center spread at the stitches, is tinted and its number bold.
