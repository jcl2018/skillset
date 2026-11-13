# lyrics never overlap the tab: lyric text is drawn in its own band below the lowest string and below any rhythm marks, never on or over string lines or fret digits; a lyric wider than its bar widens that bar, wraps onto a second lyric line, or shrinks to the template's lyric minimum, in that order, and never runs into the next bar's lyric; the estimate mark and the repeat count never collide with lyrics or digits; the 2-page limit and the 9 pt digit floor still hold

- Slug: lyric-layout
- Touches: skills/bass-tab, tests/bass-tab, .loop/regression.tsv, docs/wiki/Bass-tab.md, docs/wiki/Tests.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. a fixture with long Chinese lyric lines on dense bars renders with no lyric glyph box intersecting a string line, digit or another lyric, checked by a test on the drawn boxes, seen failing first on the current main
2. the owner's case (one lyric line per bar on 4-5 digit bars) renders clean; existing chart tests still pass; Bass-tab and Tests current; land lane passes; no lyrics text from any real song in the repo

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
