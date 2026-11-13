# Design: docs-consolidate

Apply the owner-approved Bass-tab documentation review. Approach: wording-only edits to the Bass-tab page (no drawing code, the lyric-layout goal owns that), one new test case, three done-line rows.

- S1 chart behaviours get requirement wording inside BAS-2 and BAS-3 (the page is at the 10-requirement cap, so no new ids); BAS-2 and BAS-3 go back to Unreviewed.
- S2 BAS-6 says a person checks it. S4 BAS-8 states what the chart prints when there is no report. S7 the BAS-7 empty-field bullet is merged into BAS-10, with the merge noted.
- S3 new row bas-nonlatin-chart (BAS-5), seen failing first. S9 the chart2pdf Usage bullet is shortened.
- Not done here (named in the PR): template-owned (S5 Run links, S8 Settings copies, S11 retired settings), owner-only (S10 reviews), out of touches (S6 #25 and S12 split chart2pdf.py: drawing code; #21 nightly, #24 Home render; worktree and session cleanup; git hooks), blocked by the frozen contract (S14 health-clear-1 row, a done line's only row).
