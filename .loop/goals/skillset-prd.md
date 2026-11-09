# Migrate skillset's existing skills to PRD wiki pages in the template's v0.12.0 format

- Slug: skillset-prd
- Touches: docs/wiki, .loop, README.md, .github/workflows

## Done lines

Frozen. A wrong done line needs a new goal.

1. The adoption is in: the local branch workflow-setup is merged into this branch where it fits (or setup is run fresh), with .loop/config.json carrying the PRD setting and a check that runs the repo's tests
2. One docs/wiki PRD page per skill under skills/ (for example bass-tab), in the template's PRD layout (Review line, Problem, Usage, Requirements with IDs, Non-goals, Success metrics, Tests), written only from what is really in the repo, with the Review line, Requirements, Non-goals and Success metrics Unreviewed for the owner
3. Each requirement's Tests are Given/When/Then scenarios linked to rows in .loop/regression.tsv for the repo's real tests under tests/; a requirement with no real test is shown as not enforced
4. A Home page links the PRD pages; every page is in .loop/docs.tsv; docs.py check passes and health.py check is green
5. The repo is public: no private names, paths, emails or personal notes in any committed file, checked with the template's private-name scan before the PR

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
1. Open `docs/wiki/Bass-tab.md`.
   Expect: `Review: **Unreviewed**`, requirements BAS-1 to BAS-6 each **Unreviewed**, and under Tests a Given/When/Then line per row, with BAS-6 marked **not enforced**.
2. Open `docs/wiki/Home.md`.
   Expect: a link to Bass-tab under Skills.
3. Run `sh tests/bass-tab/run.sh` from the repo root.
   Expect: it ends with `PASS: bass-tab fixture renders in the predefined format (tab + PDF)`.

## Notes

- Owner decisions, relayed verbatim: "I also want to turn on the auto merge." and, approving the plan (option B, with
  per-requirement rows): "Yes, I want to. I want to choose B, approve it, and turn on auto approve." So
  `.loop/config.json` sets `"auto_merge": true` and `"auto_approve": true`.
- Setup was run fresh rather than merging the old local `workflow-setup` branch, which predates the PRD page format.
  This version of the config has no `checks` key; the repo's test check is the land row `repo-suite`
  (`sh tests/bass-tab/run.sh`).
- Private-name scan: the template's scan pattern was run over every tracked file, file name and commit on this branch,
  with one term removed from the pattern because it is this repo's own skill name. No match. The committed
  `repo-public` row checks only for home-directory paths and personal email addresses, so the public repo does not
  carry a list of private terms.
- The PRD page and its requirements stay Unreviewed for the owner. BAS-6 has no automated test and shows as not enforced.
- GitHub milestones are not created here.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
