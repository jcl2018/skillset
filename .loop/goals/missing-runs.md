# a run of consecutive missing bars prints as one full-width line ("bars 16-111 missing") instead of one row per bar, so a partial song does not fill pages with empty rows (owner, 2026-11-12: "All recommended" after a partial song's chart printed 96 missing rows); a single missing bar still draws full width as today; also the README sentence now says an empty header field is left out (left uncommitted by chart-polish)

- Slug: missing-runs
- Touches: skills/bass-tab, tests/bass-tab, .loop/regression.tsv, docs/wiki/Bass-tab.md, docs/wiki/Tests.md, README.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. a fixture with a long missing run renders it as one line with its range and a test proves it, seen failing first; a single missing bar is unchanged
2. README matches the left-out rule; Bass-tab and Tests current; land lane passes; no private name or path in commits

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
