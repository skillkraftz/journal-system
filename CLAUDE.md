# Journal System

Generators for a hand-bound pocket notebook system. Python scripts draw page
templates; the output becomes letter-size PDFs; the `booklet` script imposes
those PDFs into signatures that are printed, folded, sewn or stapled, and
carried in a hardcover case that holds 3-4 booklets on elastic bands.

The owner fills pages with a black pen while out, then adds color with colored
pens at the desk. Templates are therefore black and gray only, never color.

## Pipeline

1. **Page generators** (`pocket_templates.py`, Python + Pillow) draw each page as
   a PNG that is exactly 7.5" x 10" at 600 DPI, with no white border. Font is
   Courier Prime Bold.
2. **PDF assembly** places each image on a letter page (8.5" x 11") at 0.5"
   margins, one image per page, at actual size.
3. **`booklet`** (bash: pdfjam + qpdf) trims each letter page, stretches it to
   the pocket page size, and imposes signatures for printing. **Do not modify
   `booklet` unless a task explicitly asks for it.** Generator output must fit
   what it already does.

### What `booklet` does to a page (defaults)

- Trims 0.25" off every edge of the letter page, leaving 8.0" x 10.5".
- Stretches that, without keeping aspect ratio, to 3.5" x 5.25".
- So the content is scaled about 0.4375 horizontally and 0.5 vertically. Drawn
  shapes come out about 12.5% narrower than they are tall (circles become
  slight ovals). Text shrinks to roughly 45-50% of its drawn size, and lines
  to about half their weight.
- Practical minimums on the 7.5" x 10" canvas: text 9pt or larger, line
  weights 0.5pt or heavier.

`booklet` is interactive. To run it unattended (needs pdfjam and qpdf), pipe the
answers in order: paper (1 letter, 2 half-letter), page width, page height,
trim, stretch, signatures, confirm.

```bash
printf '2\n3.5\n5.25\n0.25\ny\n1\ny\n' | ./booklet out/some-book.pdf
```

## The books

- **Year book**: one page per week, 52 weeks, planned one quarter at a time
  with post-it notes. Inside front cover: year goals plus a sideways two-column
  week list (Q1-Q4 heading rows, one line per week, week numbers colored by
  outcome). Inside back cover: an index, with week boxes in two columns and the
  open space divided only where months change.
- **Month book**: the monthly tracker grid on the inside front cover (habit
  columns, appointment lines on the right, sleep hours in the offset column on
  the left, times along the bottom). Inside is a daily Good Time Journal page:
  three activity boxes with Engagement (with Flow) and Energy dials, then
  journal lines. The month book is still being redesigned through use.
- **Catch-all books**: lined and blank notebooks, plus a book-notes layout
  (left page: title, question, sections read, what happens if answered or not,
  what success looks like; right page: chapter/section, page, finding).
- Covers are scrapbook paper, printed separately from the interior pages, so
  inside-cover designs are their own outputs, not book pages.

## Conventions

- Units are inches; line weights and font sizes are points.
- Week rules (configurable with `WEEK_START`): weeks run Sunday to Saturday, and
  week 1 is the week containing January 1. Every year has exactly 52 weeks; the
  last days of December past week 52 are intentionally dropped, because the end
  of the year is for planning next year.
- Index month boundaries snap to half weeks: a month starting on a week's 1st or
  2nd day snaps to that week's top, the 3rd-5th day to its middle, the 6th or 7th
  day to the next week.
- Labels stay small and in a corner of their box, so writing space stays open.
- Keep the visual language consistent across pages: small outlined label boxes,
  thin 0.5pt rules, 1.5pt for outlines and emphasis, Courier Prime Bold.
- Page designs come from the owner's sketches. Don't invent new page types or
  change an existing layout beyond what the task asks. If something is
  ambiguous, choose the simplest version and list the question in the PR
  description.
- Keep scripts small and readable, with settings at the top of each file.
