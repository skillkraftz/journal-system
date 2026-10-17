# Pocket Journal System

A generator for a hand-bound pocket notebook system: 3-4 small journals carried
together in a hardcover case. It builds print-ready PDFs on half-letter paper
that the owner prints at home, folds, sews and trims by hand.

This is a personal tool first. It may become a product later, so keep the code
clean and the designs consistent enough to look like a finished product.

`reference/` holds earlier prototypes (an older template script, the original
`booklet` imposition script, old PDFs and photos of sketches). They show intent
and hard-won lessons, not code to preserve. The old pipeline (PNG pages in a
Word document, trimmed and stretched by `booklet`) distorted pages and is being
replaced. Everything here is now drawn at final size, built for this one
physical process.

## The physical process (everything serves this)

1. Paper is letter copy paper cut in half: **5.5" x 8.5" sheets**, always.
2. Each sheet is printed on both sides with a two-page spread, landscape,
   using **manual duplex**. Keep this exactly:
   - `print-first.pdf`: the front of every sheet, in **reverse** sheet order.
   - The owner puts the printed stack back in the tray the same way.
   - `print-second.pdf`: the back of every sheet, in **forward** sheet order.
3. The sheets nest into **one signature** (usually; multiple signatures should
   remain possible), are folded in half, sewn through 5 holes in the fold, and
   wrapped in a scrapbook-paper cover.
4. The folded book is 4.25" x 5.5". The owner measures **3.5" from the fold**
   and cuts off the excess fore-edge with a razor.

So the final page is **3.5" x 5.5" (88.9 x 139.7 mm)**, and on the sheet:

- The spread is centered on the sheet's fold line (the vertical center line of
  the 8.5" side). Each page's content sits in the 3.5" next to the fold. The
  outer 0.75" on each side is trimmed away and must stay empty.
- **Creep**: in one nested signature, inner sheets are pushed outward by the
  sheets wrapped around them, so their content drifts toward the trim line.
  Compensate by shifting each sheet's pages toward the fold by about
  (sheets outside it) x (paper thickness). Paper thickness is a setting
  (default 0.1 mm for 20 lb copy paper).
- The printer can't print right to the paper edge, and the page is the full
  5.5" sheet height, so top and bottom content near the edge may be clipped.
  The calibration sheet (see below) measures this. Margins must be settings,
  not constants.

## Design system

- **Margins**: 3 mm on all sides of the page, as separate top, bottom,
  fore-edge and gutter settings.
- **Grid**: 3 mm. The owner writes with a uni-ball 0.38 mm pen, and 3 mm is the
  smallest comfortable line spacing. Every writing line, dot grid and row
  snaps to 3 mm, so all books share one rhythm. The content area is about
  27.6 x 44.6 cells; center the grid within it.
- **Font**: Courier Prime (bundled in `fonts/`, OFL). Labels around 6-7 pt so
  they fit inside one 3 mm row; headings around 9-11 pt; nothing below 5.5 pt.
- **Ink**: black and grays only. The owner writes in black pen out in the
  world and adds color with pens at the desk. Writing rules and dots are light
  gray and thin so handwriting stands out; structure (outlines, separators) is
  black. Avoid heavy boxes: labels are small text in a corner or margin, not
  boxed blocks. The look should be quiet and clean, not blocky.
- **Page numbers** on every interior page of template books, small, in the
  bottom outer corner, inside the margin.
- Draw vector output directly (reportlab) at final size in millimeters. PNGs
  are for previews only.

## The books

Every book has **52 interior pages** (13 sheets, one signature) so all books
in the case are the same thickness. Each book also has a **cover spread**: the
inside front cover and inside back cover, printed single-sided on the cover
paper and centered the same way.

- **Year journal**: 52 weekly pages, weeks Sunday to Saturday. Each week has a
  goal at the top, seven days, and an outcome at the bottom. The owner plans
  one quarter at a time with full-size post-it notes stuck on future weeks.
  Inside front cover: the year's goals plus all 52 weeks in two sideways
  columns, with Q1-Q4 heading rows and one line per week for "how it went"
  (week numbers get colored by outcome later). Inside back cover: an index
  with week boxes in two columns, where the open space is divided only at
  month boundaries.
- **Monthly journal**: one per month, generated for a specific month and
  year, and must work as the **only** book carried on a light day. Inside
  front cover: the monthly tracker grid (day rows, about 12 habit columns with
  names written vertically above, appointment lines to the right, an offset
  half-row column on the left for hours of sleep, times along the bottom).
  Interior: a dated daily Good Time Journal page per day (three activity
  entries with Engagement + Flow and Energy dials, then journal lines), weekly
  reflections that line up with the year journal's Sunday-Saturday weeks,
  month-end review pages, then notes pages to fill out 52. The inside back
  cover is not decided yet.
- **Book notes**: a setup page per book (title; the question I want answered;
  sections I'm reading or ALL; what improves if I find the answer; what stays
  unsolved if I don't; what success looks like) followed by note pages
  (chapter/section, page, what I found).
- **Plain books**: 3 mm lined, 3 mm dot grid, blank, and later mixes of these.
  Plain books get a universal index (page number + topic) on the inside back
  cover.

## Calendar conventions

- Weeks run Sunday to Saturday. Week 1 is the week containing January 1.
  Every year has exactly 52 weeks; December days past week 52 are dropped on
  purpose, since the end of the year is for planning the next one.
- On the year index, month boundaries snap to half weeks: a month starting on
  a week's 1st-2nd day snaps to that week's top, 3rd-5th day to its middle,
  6th-7th day to the next week.

## Architecture

- A page-type registry: each page type is a function that draws into a page
  box given a context (date, year, month, page number, params). Page types are
  small and composable.
- Books are described by recipes (YAML), so new books need no code: an
  ordered list of page types with params, repeats, per-day/per-week expansion,
  and fill-to-52 rules, plus cover pages.
- One imposition module for saddle-stitch order, centering, creep and the
  manual duplex files.
- One entry point that asks questions interactively (book type, year, month,
  whether to build all 12 months, signatures, paper thickness) and also
  accepts the same choices as flags. Output goes to a folder per build with
  `print-first.pdf`, `print-second.pdf`, `cover.pdf`, a preview contact sheet
  of the pages at final size, and a short summary (pages, sheets, settings).
- Settings live in one config file with comments.
- Tests cover week math, page counts, imposition order and the duplex split,
  and sheet geometry (centering, creep, nothing in the trim zone).

## Working rules

- Page designs come from the owner's descriptions and sketches. Don't invent
  new page types beyond the task. When a choice is unclear, take the simplest
  version and list the question in the PR description.
- Keep code readable with settings at the top; the owner reads and tweaks it.
- Include preview PNGs of new or changed pages in every PR that changes a
  design.

## Commands

Setup: `pip install -e '.[dev]'` (reportlab, pypdfium2, pillow; pytest and pypdf for tests).

    python -m pocketjournal                          # asks questions, then builds
    python -m pocketjournal build [lined|dots|all]   # recipes/*.yaml -> build/<book>/
    python -m pocketjournal build lined --signatures 2 --thickness 0.12
    python -m pocketjournal calibrate                # -> build/calibration/
    python -m pytest                                 # tests

Flags on both commands: `--out DIR`, `--thickness MM`, `--back-dx MM`, `--back-dy MM`.
All defaults live in `pocketjournal/config.py` (`Settings`).

Each book folder holds `print-first.pdf`, `print-second.pdf` (with several
signatures: `sigN-print-first.pdf` / `sigN-print-second.pdf`, one pair per
signature), `cover.pdf`, `pages.pdf` (pages at final size), `preview.png`
(contact sheet) and `summary.txt`.

Calibration: print `calibration-print-first.pdf`, reload as for a book, print
`calibration-print-second.pdf`. Read the edge rulers for printer reach (raise
`margin_top`/`margin_bottom` if needed) and hold to the light to read front/back
misalignment; enter it as `back_offset_x`/`back_offset_y`.

Layout of the package: `config` (design system), `recipe` (YAML recipes -> books), `calendars` (weeks), `draw` (mm vector wrapper),
`page` (PageBox, grid), `pagetypes` (registry), `imposition` (order, centering,
creep, duplex), `calibration`, `preview`, `book` (build a folder), `cli` (questions and flags). Recipes live in `recipes/`; the README explains how to write one.
Previews of current designs are in `previews/`.
