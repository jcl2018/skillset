<!-- workflow-docs -->
# Bass-tab

Review: **Unreviewed**

## Problem

Bass players who learn songs from tab screenshots, PDFs and notes need one compact tab they can trust and a chart they can print and play along with.

The skill turns what the sources actually show into one song file, then renders a fixed-format text tab and a one-or-two-page chart PDF with section labels, collapsed repeats, chords and lyrics, without inventing bars or words.

## Usage

- "Make a bass tab of this song from these screenshots" writes the song file from the sources and renders the tab and the chart PDF.
- "Fix bar 12 in this tab and print it again" corrects the song file once, so every copy of a repeated figure changes, and renders again.

## Requirements

- BAS-1: **Unreviewed** A song file renders to a compact text tab in the fixed format, and the fixture song's tab matches its recorded baseline exactly.
- BAS-2: **Unreviewed** The chart shows a bold label where each section starts, a repeated figure drawn once with its count, and each lyric under its own bar.
- BAS-3: **Unreviewed** The chart fits two US-Letter pages with tab digits at 9 pt or more, and a song that cannot fit is refused with a line naming it.
- BAS-4: **Unreviewed** Rendering the same song file twice gives byte-identical PDFs.
- BAS-5: **Unreviewed** Without Pillow, a tab PDF with a non-Latin title is refused rather than printed with question marks, unless lossy output is asked for.
- BAS-6: **Unreviewed** A song file holds only what a source shows; no bar or lyric comes from memory or a web search.

## Non-goals

- It does not hear audio: a link to a recording gives a title, tempo and section names at most.
- It does not pick between two bass tracks, or between instruments; it asks.

## Success metrics

- Every chart the skill renders is at most two pages, and none is printed with tab digits under 9 pt.
- No transcription ends without a list of missing bars, estimates and which source gave what.

## Tests

#### BAS-1

A song file renders to a compact text tab in the fixed format, and the fixture song's tab matches its recorded baseline exactly.

- Given the fixture song, when its compact text tab is generated, then it matches the recorded baseline byte for byte. — [bas-tab-baseline](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-09

#### BAS-2

The chart shows a bold label where each section starts, a repeated figure drawn once with its count, and each lyric under its own bar.

- Given an invented song with sections, repeats and lyrics, when its chart is rendered, then each section has a bold label, the repeated bars print once with a count, and each lyric sits under its own bar. — [bas-chart-layout](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-09

#### BAS-3

The chart fits two US-Letter pages with tab digits at 9 pt or more, and a song that cannot fit is refused with a line naming it.

- Given a normal song and a 400-bar song, when each chart is rendered, then the first fits two pages with tab digits at 9 pt or more and the second is refused with a line naming it. — [bas-chart-fit](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-09

#### BAS-4

Rendering the same song file twice gives byte-identical PDFs.

- Given one song file, when the tab PDF and the chart PDF are each rendered twice, then both copies are identical byte for byte. — [bas-pdf-same](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-09

#### BAS-5

Without Pillow, a tab PDF with a non-Latin title is refused rather than printed with question marks, unless lossy output is asked for.

- Given a tab with a Chinese title and no Pillow installed, when its PDF is rendered, then it is refused unless lossy output is asked for, and written when it is. — [bas-nonlatin](../../.loop/regression.tsv), both, PASS 2026-11-09, seen failing 2026-11-09

#### BAS-6

A song file holds only what a source shows; no bar or lyric comes from memory or a web search.

- Given sources for a song, when the agent writes the song file, then every bar and lyric comes from a source, which only a person reading the source report can check. — [bas-sources-only](../../.loop/regression.tsv), by a person, not run, seen failing no
- **not enforced**: no passing test
