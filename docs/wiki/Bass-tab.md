<!-- workflow-docs -->
# Bass-tab

Milestone: https://github.com/jcl2018/skillset/milestone/1

Review: **Unreviewed**

## Problem
- I learn bass lines from many places: tab videos on YouTube and Bilibili, tab sites like Songsterr, other sites I find, screenshots and PDFs.
- Each shows only part of the song at a time, and they don't share a layout.
- I want one compact printout that shows the whole song at a glance (sections, chords, lyrics, tempo and key) in the same format for every song, so I don't miss a part while I play along.

## Usage
- `python3 skills/bass-tab/scripts/chart2pdf.py SONG -o OUT [--paper letter|a4] [--expand-sections] [--template PATH] [--allow-lossy]` — Renders a song file to the play-along chart PDF (US-Letter by default; layout from `skills/bass-tab/templates/chart-format.json` or `--template`) and prints `wrote OUT  (N bytes)  pages=N  tab_font_pt=N  lines=N  section_refs=N` (exit 0). Refuses a song that does not fit two pages (exit 1, `chart2pdf: TITLE does not fit 2 pages at 9 pt tab digits (needs N). Cut bars or split the song.`), non-Latin text without Pillow (exit 2, `refused: non-Latin text would print as '?'. Install Pillow (python3 -m venv v && v/bin/pip install pillow) or pass --allow-lossy.`, after a `warning: lossy: ...` line per text), a template file that is missing, not JSON, missing a key or with no 9 pt rung (exit 1, `chart2pdf: template PATH ...`), a song whose `REPORT` names a bar not in it, a section that is not a start bar, or that sets both `source` and `sources` (exit 1, one line naming the song), and a missing `-o` (exit 2, `chart2pdf.py: error: the following arguments are required: -o/--out`). The chart prints every bar's number and each section label's start time when the song has a tempo; a missing bar is drawn full width and marked "missing", an estimated bar carries a "≈" sign, a section starts on a new line instead of sharing one with the last bars of the one before, and the repeat count sits above the closing repeat sign. A section that repeats an earlier one collapses to one reference line unless `--expand-sections` keeps it drawn out (`--collapse-sections` is still accepted and is now the default), a song that fits one page gets larger tab digits (11 or 12 pt), and a header field with no value, or a source report with no report, no list and no source named, is left out (an empty missing or estimates list still prints "none"). An estimated bar and a section holding one are always drawn out, never folded into a repeat or a reference line, and repeats and references also stop at a change of chord, so a song with estimates may print at a smaller size than one without; the estimate sign has its own room (`marks.estimate_room`) so it never meets a chord name.
- `python3 skills/bass-tab/scripts/tabgen.py SONG OUT [--bars N] [--cut compact|full]` — Writes the text tab (3 bars per line and the full cut by default; `--cut compact` is the sheet) and prints `bars=N range=A-B malformed=none  widths=[77]` (exit 0). Refuses a 5-string song (exit 2, `tabgen: TITLE is 5-string; render it with chart2pdf.py`). With fewer than two arguments it prints `usage: tabgen.py <song.py> <out.tab> [--bars N]` (exit 2).
- `python3 skills/bass-tab/scripts/tab2pdf.py TAB [-o OUT] [--paper a4|letter] [--section-break-frac F] [--allow-lossy] [--check]` — Renders a text tab to the long one-bar-wide PDF (A4 by default, next to the tab when `-o` is left out) and prints `wrote OUT  (N bytes)  pages=N  tab_font_pt=N  longest_line=N  blocks=N  mono_lines=N  sections=N  rasterized_runs=N` (exit 0); with `--check` it writes nothing and prints `OK (check, nothing written)  pages=N ...` (exit 0). Refuses a tab with no tab content (exit 2, `refused: no tab content found in TAB`), non-Latin text without Pillow (exit 2, `refused: non-Latin text would print as '?'. Install Pillow (python3 -m venv v && v/bin/pip install pillow) or pass --allow-lossy.`), and a tab line over 77 characters (exit 1, `tab2pdf: longest line is N chars, over the template maximum of 77.` then `Re-render with fewer bars per system (tabgen --bars N).`).

## Requirements

### Functional
- BAS-1: **Reviewed 2026-11-11** One format, Songsterr-style <!-- reviewed ce865339 -->
  - Every song is written to the same song file and printed in one layout modeled on Songsterr's tab: one line per string, labeled at left; bar numbers above bars; time signatures where they change; rhythm marks under notes.
  - The layout is adjusted for print: several bars per line, repeats collapsed.
  - The fixture song's compact tab matches its recorded baseline exactly.
- BAS-2: **Reviewed 2026-11-11** The whole song at a glance <!-- reviewed 5abec8be -->
  - A bold label where each section starts.
  - A repeated figure is drawn once with its count (x4).
  - A section that repeats an earlier one is one line ("Chorus 2 = Chorus").
  - Chord names sit over their bars, and each lyric under its own bar.
- BAS-6: **Unreviewed** Only what the sources show
  - Sources are whatever I provide: any URL (such as a video, Songsterr or another tab site, or a lyrics or chord page), screenshots, PDFs, notes.
  - Each bar, chord and lyric comes only from a source I provided and can be traced to it, never from memory or a web search I didn't ask for.
  - A source it can't open or read is never guessed around.
- BAS-7: **Unreviewed** Song header
  - Every chart starts with the same header: title, artist, BPM, key, time signature, tuning, instrument (such as 5-string bass), and every source used.
  - A header field the sources don't show is left out, never guessed; a missing title still reads "not shown".
- BAS-8: **Unreviewed** Source report
  - Every transcription ends with a short report in a fixed format listing missing bars, bars that are estimates, which source gave each section, and any source it couldn't open or read.
- BAS-9: **Reviewed 2026-11-11** Four- and five-string bass <!-- reviewed 399a7de6 -->
  - The tab draws as many string lines as the song's bass has (4 or 5, such as a low B), labeled to match its tuning.
- BAS-10: **Unreviewed** One format template
  - One template file defines the printed layout: header fields and order; how a section starts and how repeats and repeated sections show; the Songsterr-style staff; where chords and lyrics sit; spacing and fonts.
  - Every song renders through it, so changing it changes every song the same way.
  - A header field with no value is left out, never a blank or a guess; a missing title still reads "not shown".

### Non-functional
- BAS-3: **Reviewed 2026-11-11** Fits a printout <!-- reviewed 7e8cd415 -->
  - Two US-Letter pages at most, tab digits at 9 pt or more.
  - Repeats collapse and spacing tightens before the font shrinks.
  - A song that still can't fit is refused with a line naming it.
- BAS-4: **Reviewed 2026-11-11** Same input, same printout <!-- reviewed 91020a70 -->
  - Rendering the same song file twice gives byte-identical PDFs.
- BAS-5: **Reviewed 2026-11-11** No silent question marks <!-- reviewed 4ebe8a8d -->
  - A Chinese or other non-Latin title or lyric is never printed as question marks.
  - It renders correctly, or it's refused with a fix line.

## Non-goals
- It doesn't hear audio or transcribe by ear: it reads what the sources show.
- It doesn't choose between two bass parts: it asks.
- It doesn't print every repeated bar.

## Success metrics
- Every chart is at most two pages, with the header filled in.
- No transcription ends without its source report.

## Tests

| Test | Kind | Guards | Checks | Last result |
|---|---|---|---|---|
| [bas-tab-baseline](Tests#t-bas-tab-baseline) | requirement | BAS-1 | Given the fixture song, when its compact text tab is generated, then it matches the recorded baseline byte for byte. | PASS 2026-11-12 |
| [bas-chart-layout](Tests#t-bas-chart-layout) | requirement | BAS-2 | Given an invented song with sections, repeats and lyrics, when its chart is rendered, then each section has a bold label, the repeated bars print once with a count, and each lyric sits under its own bar. | PASS 2026-11-12 |
| [bas-sources-only](Tests#t-bas-sources-only) | requirement | BAS-6 | Given sources for a song, when the agent writes the song file, then each bar, chord and lyric comes only from a cited source, which a person reading the source report checks; the nightly run checks the report's format (BAS-8). | not run |
| - | requirement | BAS-6 | no passing test | not enforced |
| [bas-header](Tests#t-bas-header) | requirement | BAS-7 | Given a song whose source shows only a title, when its chart is rendered, then the title prints, header fields with no value are left out, and a full song's fields print in template order. | PASS 2026-11-12 |
| [bas-source-report](Tests#t-bas-source-report) | requirement | BAS-8 | Given a song with a source report, when its chart is rendered, then missing bars, estimates and the source per section print after the last stave line, a missing part reads "not shown", and a bad report key is refused. | PASS 2026-11-12 |
| [bas-five-string](Tests#t-bas-five-string) | requirement | BAS-9 | Given a 5-string and a 4-string song, when each chart is rendered, then the first draws five stave lines labeled G D A E B and the second four labeled G D A E, and the text tab refuses the 5-string song. | PASS 2026-11-12 |
| [bas-template](Tests#t-bas-template) | requirement | BAS-10 | Given a changed copy of the format template, when two songs are rendered through it, then the header order, missing text, repeat format, section size and line gap all follow it, and a bad template is refused by name. | PASS 2026-11-12 |
| [bas-chart-fit](Tests#t-bas-chart-fit) | requirement | BAS-3 | Given a normal song and a 400-bar song, when each chart is rendered, then the first fits two pages with tab digits at 9 pt or more and the second is refused with a line naming it. | PASS 2026-11-12 |
| [bas-pdf-same](Tests#t-bas-pdf-same) | requirement | BAS-4 | Given one song file, when the tab PDF and the chart PDF are each rendered twice, then both copies are identical byte for byte. | PASS 2026-11-12 |
| [bas-nonlatin](Tests#t-bas-nonlatin) | requirement | BAS-5 | Given a tab with a Chinese title and no Pillow installed, when its PDF is rendered, then it is refused unless lossy output is asked for, and written when it is. | PASS 2026-11-12 |
