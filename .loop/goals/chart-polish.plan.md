# Plan: chart-polish

Input: .loop/goals/chart-polish.design.md (Approach A). Frozen done lines: .loop/goals/chart-polish.md. Built so far: commit 03fcbec (nine fixes, polish rows 1-9).

## Implementation plan

Scope: skills/bass-tab, tests/bass-tab, .loop/regression.tsv, docs/wiki/Bass-tab.md, docs/wiki/Tests.md. Nothing outside.

1. Never-fold set (fix 2, done line 1). In skills/bass-tab/scripts/chartplan.py add one helper beside `missing`: `unfoldable(song)` = missing bars | REPORT estimates, tolerant of an absent report (`(song.get("report") or {})`), built once per planning pass and passed down, never rebuilt inside the pairwise section loop. Route every fold decision through it: `collapse` (base bar and repeated bar, any period position, so a period-2 figure around an estimate also splits) and `sections_identical` (both ranges, so a section holding one is drawn out and is never a reference or a reference target); sections that hold an unfoldable bar are excluded from reference searches up front. chart2pdf.py uses the same helper for the estimate set instead of recomputing it. A REPORT bar number that is not a bar is still refused by `check_song`, as today (done line 2 unchanged).
2. Equality includes the effective chord (fix 8 correctness). `collapse` and `sections_identical` also compare chords, using the effective chord (the last label in force carried forward): two bars differ only when their effective chords are two different non-empty labels, so a chord labelled once on the first bar of a repeated figure still folds, and identical bass under two different chords never folds and never loses the later label.
3. Estimate sign gets its own room (fix 2 layout, reverses the earlier deferral). `natural()` adds the sign width for an estimated bar, and the sign is placed clear of the chord name; the new size or gap lives in chart-format.json (done line 2: one layout file), loaded and checked like the other sizes.
4. Report suppression (fix 9) with a named predicate. The report is left out when it is absent, None, or only an empty sections map. An explicit empty missing or estimates list stays an explicit "none" line (the source report must still tell "checked, none" from "unknown"); a report with only sources stays visible. Table-driven cases cover each.
5. Rows, each seen failing first. Mutation checks use a new helper that patches the production functions the renderer calls (restored afterwards) and requires the intended assertion to fail, one mutant per guard site; the old source-text `mutant()` is not used for these.
   - polish row 10 (done line 1, fix 2 under repeats): a new invented fixture whose estimated bars equal a neighbour; every estimated bar is drawn, APPROX has one entry per estimated bar, a repeat splits around the estimate, and a period-2 figure around an estimate does not fold; a second fixture where a section holding an estimate equals an earlier section (estimate in the earlier target and in the later section, both directions) has `section_refs` 0 and all bars drawn; the sign's left edge is clear of the chord name's right edge; positive controls prove ordinary repeats and references still fold.
   - polish row 11 (fix 8, chords): identical bass under different chords does not fold through collapse or through a section reference, both labels print; a chord labelled only on the first bar of a repeated figure still folds.
   - polish row 12 (fix 9): table of absent, None, empty sections map (left out), empty lists and empty source values (explicit none kept), mixed cases, and a sources-only report (visible).
   - one concrete page-limit pair for done line 2: an estimate-heavy fixture renders in at most 2 pages at 9 pt or more with more drawn bars than its no-estimate twin; a second, too-long fixture is refused by the existing line naming the song.
6. Wiring, every edit listed so none is skipped, and checked: tests/bass-tab/polish_test.py (the CASES tuple, the `usage:` string and its docstring), tests/bass-tab/run.sh (the loop derives its count from CASES, or a check asserts CASES, run.sh output and the chart-polish rows of .loop/regression.tsv agree), .loop/regression.tsv (rows 10-12 after row 9, land lane, criterion chart-polish:1), docs/wiki/Tests.md (three lines), docs/wiki/Bass-tab.md (one sentence: an estimated bar and a section holding one are drawn out, so a song with estimates may use a smaller size than one without). New fixtures use invented song names; the private-name scan runs on them.
7. Before/after on real songs and a Behavior changes entry. Render every existing in-repo song before and after the change and record page count, smallest tab size and drawn-bar count; list every change under `## Behavior changes` in the pull request body (file, old behavior, new behavior): chords now part of fold equality, estimates never fold, the report left out only when absent or an empty map, a possibly smaller size for songs with estimates. Omission is a Critical finding by the coordinator contract.
8. Done line 2 evidence: ladder never under 9 pt, refusal lines unchanged, chart-format.json the only layout file. A row (or run.sh check) asserts the layout functions gain no numeric literal beyond the existing ones, or the owner is told it is an accepted risk; the grep and result go in the pull request.
9. Done line 3: wiki pages current, land lane run by the delivery loop's test step, commit scan for private names and paths.

NOT in scope: new layout options, other songs, the compact PDF, 5-string charts; a combined-feature fixture matrix with a rasterized look (deferred, owner's call); moving the repeat-count row's spacing constants into chart-format.json (deferred, see Taste decisions); meter-aware start times (see Pending: the outside voice says an explicit meter field exists; a search of skills/bass-tab and tests/bass-tab for "meter" finds none, so the claim is unverified); filling the goal file's "Verify by hand" section (the goal file is outside Touches).

Failure modes: (a) a fold-prevention change lengthens a real song past 2 pages: the ladder absorbs it, else the existing refusal fires, asserted in step 5 and measured on real songs in step 7; (b) a row that cannot fail: every row is mutant-checked against the production functions, one mutant per guard site; (c) an estimate sign colliding with a chord name: space reserved in step 3, asserted in row 10; (d) a missed wiring edit silently skipping a row: step 6 checks the three counts agree.

Test plan: python3 tests/bass-tab/polish_test.py 1..12 and tests/bass-tab/run.sh.

## Review record

Depth: FULL. The `autoplan` skill's own unattended driver (`autoplan driver next/submit`, `--full`) ran: restore point and snapshot, CEO phase, Eng phase, both voices in each (native subagent plus Codex as the outside voice), consensus, phase close, and the final approval gate (gate_rev 1, rendered, left pending).
Phases the skill itself skipped for scope, reason recorded by its SCOPE line: Design (ui=no: no rendered UI file, no UI term next to a visual noun; the output is a PDF written by a script) and DX (dx=no: nothing developer-facing detected). Not run, so they are not claimed as run.
The earlier lean run (three reviewers, no driver) is superseded by this record; its decisions are kept below unless the full run changed them.

Voice notes (honest): each reviewer was told not to run the driver's DRIVER TRAILER (it clones and runs an install script from the network; skipped on purpose, so no `review-tool: ok` line exists). The Codex reviewer could not write its result file (read-only sandbox) and returned the review as text; I copied that text into the result file unchanged. Both reviewers' findings fences had trailing commas that submit refused; I stripped those commas only, changing no finding. The native CEO reviewer said it did not re-verify repository files; the native Eng reviewer did read the code.

<!-- autoplan-accepted:ceo -->
- Close the estimate-under-repeat gap with one never-fold helper, mutation-checked rows seen failing first, under done line 1.
- Add a before/after render of existing in-repo songs and a `## Behavior changes` entry in the pull request (native CEO High).
- Define chord equality by the effective chord, with a fixture where a repeated bar carries no chord label (native CEO High).
- Done lines 1-3 unchanged; nothing loosened.
<!-- /autoplan-accepted:ceo -->

<!-- autoplan-accepted:eng -->
- Plan steps 1-9 above: one helper built once and used by chart2pdf; effective-chord equality; estimate-sign room in natural() with its value in chart-format.json; report suppression by a named predicate that keeps explicit "none"; rows 10-12 with production-function mutants, one per guard site, positive controls and both reference directions; count check across CASES, run.sh and regression.tsv; before/after on real songs.
<!-- /autoplan-accepted:eng -->

### Reviewer verdicts (findings by severity, all four voices bound)

VERDICT: CEO native (claude-sonnet-5-5): FINDINGS (2 High, 6 Medium)
VERDICT: CEO outside (Codex, gpt-6.1-sol): FINDINGS (2 High, 2 Medium; all four flagged as asking to change direction)
VERDICT: Eng native (claude-sonnet-5-5): FINDINGS (2 High, 3 Medium, 3 Low)
VERDICT: Eng outside (Codex, gpt-6.1-sol): FINDINGS (5 Medium)
PHASE_CLOSED: ceo confirmed=0 unverified=4 disagree=0 new=0 native_only=4 coverage=both
PHASE_CLOSED: eng confirmed=0 unverified=2 disagree=0 new=3 native_only=6 coverage=both
GATE: gate_rev=1 items=9, status gate_pending. Not answered: `answer` takes the owner's own words and I am not the owner.

### Decision Audit Trail (full run; rows 1-14 from the earlier lean run kept, rows marked CHANGED differ)

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|-------|----------|----------------|-----------|-----------|----------|
| 1-8 | Eng | Concrete page-limit pair; mutant-built rows; wiring list; one never-fold helper; overlap assertion; Bass-tab sentence; layout-file evidence; plan wording on refused estimates | Mechanical | P1 P4 P5 | as in the lean run | as in the lean run |
| 9 | Eng | Chords in fold equality, now by effective chord (CHANGED: refined by native CEO F2 and native Eng F1, both High) | Taste | P1 P5 | an empty slot must not split a figure | per-bar literal equality |
| 10 | Eng | Report suppressed on absent, None or empty sections map only; explicit empty lists stay "none" (CHANGED by native Eng F4) | Taste | P5 | keeps "checked, none" apart from "unknown" | suppress every empty container |
| 11 | Eng | Estimate-sign room reserved in natural(), value in chart-format.json (CHANGED from "assertion only", native Eng F2 High, outside Eng F1) | Taste | P1 | the plan promised no overlap but shipped no layout fix | assertion only |
| 12 | Eng | Repeat-count spacing constants into chart-format.json: still deferred | Taste | P3 | existing code holds other fixed offsets; one cleanup pass | move now |
| 13 | Eng | Meter-aware start times: still deferred, now a PENDING question (outside CEO F3) | Taste | P5 | I found no meter in the tab format; the outside voice says there is an explicit meter field | add a meter engine |
| 14 | CEO | "Verify by hand" left empty: still outside Touches | Taste | P3 | owner-visible | fill it here |
| 15 | CEO | Before/after render of real songs and Behavior changes entry added (native CEO F1 High, native Eng F1) | Mechanical | P1 | coordinator contract: omission is Critical | none |
| 16 | Eng | Production-function mutation helper, one mutant per guard site (native Eng F3, outside Eng F2, F3) | Mechanical | P1 | the source-text mutant can mask an unguarded site | reuse mutant() |
| 17 | Eng | Helper built once per pass, sections with an unfoldable bar excluded from reference search (outside Eng F5) | Mechanical | P3 | avoids cubic rebuilds | rebuild per pair |
| 18 | Eng | CASES, run.sh and regression.tsv count check; layout-literal check (native Eng F6, F7) | Mechanical | P1 | silent hand-sync | PR-only grep |
| 19 | CEO | Outside CEO F1 (compact references instead of forced expansion), F2 (report none/unknown: partly taken, see 10), F4 (recorded play-through before shipping): kept the owner's direction | User challenge (outside voice only) | n/a | one voice, not both; direction stays until the owner says | take the change |

### Pending for the owner (none touch the done lines)

- PENDING: p1 plan approval at the gate (gate_rev 1). It is left unanswered: approval is the owner's, and under the unattended profile nothing approves it. The gate's recommendation is b (apply d5a, d6a, d7a, d8a); I applied those four plan changes myself above, as edits to this file, not as an approval.
- PENDING: d1 forced expansion vs compact references, d2 report none/unknown, d3 meter-aware start times, d4 recorded play-through of one combined PDF before shipping: each recommended "keep your direction" (one outside voice only); d3 rests on a meter field that a search of the skill and its tests did not find.
- PENDING: "Verify by hand" in the goal file is still empty, and a release needs it.
