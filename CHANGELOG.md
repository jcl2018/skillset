# Changelog

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
