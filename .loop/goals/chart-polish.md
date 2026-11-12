# the play-along chart PDF gets the owner's nine review fixes (owner, 2026-11-12: "All 9"): (1) a missing bar is drawn full width as an empty bar marked "missing", never squeezed; (2) estimated bars are marked in place (e.g. a "≈" over the bar); (3) bar numbers print on the chart; (4) each section label carries its start time when the song has one; (5) a section starts on a new line, or a short section stays on one line, instead of wrapping its last bars onto the next section's line; (6) the repeat count sits above the closing repeat sign, never crowding the next chord name; (7) a song that fits one page uses larger tab digits (the fitting ladder grows as well as shrinks, still within 2 pages); (8) a section that repeats an earlier one collapses to its reference line by default (an option keeps it expanded); (9) header fields with no value and an all-"not shown" source report are left out instead of printing "not shown"

- Slug: chart-polish
- Touches: skills/bass-tab, tests/bass-tab, .loop/regression.tsv, docs/wiki/Bass-tab.md, docs/wiki/Tests.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. each of the nine shows in a rendered fixture chart and a test proves it, seen failing first
2. the 2-page limit, the 9 pt floor and the existing refusals still hold; chart-format.json stays the one layout file
3. the Bass-tab page and Tests table are current; land lane passes; no private name or path in commits

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
