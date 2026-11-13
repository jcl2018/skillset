# Changelog

## v0.1.3 - 2026-11-13

- Wiki: update pages for lyric-layout

### How to verify

No manual steps were recorded.

## v0.1.2 - 2026-11-12

- Health: render docs, add health workflow, regression row, Bass-tab review
- Regression row for BAS-6
- Regenerate Tests page
- Merge remote-tracking branch 'origin/main' into loop/health-clear
- Drop health.yml (health runs on the Mac); re-render docs; flip health-clear-1 row
- Record seen-red for health-clear-1
- Reword BAS-6 (rule) and BAS-8 (report format); leave Bass-tab Unreviewed for the owner

### How to verify

No manual steps were recorded.

## v0.1.1 - 2026-11-12

- Bass-tab v2: header, source report, 5-string staves, format template, with tests and rows
- Bass-tab v2: docs, skill text, verify-by-hand steps, regression red dates
- Bass-tab v2: review fixes (report validation, template checks, page-budget refusal)
- Lane: re-render the Tests tables
- Bass-tab v2: the report fixture's missing bar is empty
- Merge remote-tracking branch 'origin/main' into loop/bass-tab-v2
- fix: pre-landing review fixes (missing bars never fold; v2 coverage)
- pr: record issue states and the lane's results

### How to verify

1. Run `python3 skills/bass-tab/scripts/chart2pdf.py tests/bass-tab/v2-report.py -o /tmp/v2-report.pdf` and open the PDF.
   Expect: a title row, one header line with BPM, Key, Time signature, Tuning, Instrument and Sources, a four-line stave labeled G D A E, and a "Source report" block under it listing missing bars 7, estimated bars 3 and 4, and a source for Verse but "not shown" for Chorus.
2. Run `python3 skills/bass-tab/scripts/chart2pdf.py tests/bass-tab/v2-five.py -o /tmp/v2-five.pdf` and open the PDF.
   Expect: a five-line stave labeled G D A E B, and "not shown" for every header field the fixture leaves out.
3. Copy `skills/bass-tab/templates/chart-format.json`, change the first header label from "BPM" to "Tempo" and `missing_text` to "unknown", then run `chart2pdf.py tests/bass-tab/v2-sparse.py -o /tmp/v2-sparse.pdf --template YOUR_COPY`.
   Expect: the header reads "Tempo: unknown" first, and every other missing field reads "unknown".

## v0.1.0 - 2026-11-09

- Adopt the workflow loop
- skillset-prd: Bass-tab PRD page, per-requirement regression rows, Home, config
- skillset-prd: BAS-6 marked not enforced, rows run and rendered
- skillset-prd: review fixes (row cleanup and scan exit codes, BAS-5 and Pillow wording)
- skillset-prd: rows run and Tests rendered after review

### How to verify

1. Open `docs/wiki/Bass-tab.md`.
   Expect: `Review: **Unreviewed**`, requirements BAS-1 to BAS-6 each **Unreviewed**, and under Tests a Given/When/Then line per row, with BAS-6 marked **not enforced**.
2. Open `docs/wiki/Home.md`.
   Expect: a link to Bass-tab under Skills.
3. Run `sh tests/bass-tab/run.sh` from the repo root.
   Expect: it ends with `PASS: bass-tab fixture renders in the predefined format (tab + PDF)`.
