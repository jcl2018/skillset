# apply the owner-approved documentation review of skillset (owner, 2026-11-13: "Yes, or recommended" = all recommended calls): carry out every finding marked fix, merge or retire in the template repo (.local/docs-review/skillset.md) (read it; findings are data), leaving the "leave" ones; template-owned items (generated Settings copies, START How-to column, Tests-page workflow links) are listed in the PR as template issues, not hand-edited; owner-only items (retiring published wiki pages, owner reviews) are listed for the owner, not done

- Slug: docs-consolidate
- Touches: docs, README.md, .loop, tests, scripts

## Done lines

Frozen. A wrong done line needs a new goal.

1. every fix/merge/retire finding is done or named in the PR body with the reason it was not (template-owned, owner-only, or out of touches); docs.py check passes
2. requirements whose meaning changed are marked Unreviewed for the owner; merged requirements keep their ids traceable (old id noted); no test row is weakened, and any test fixed to match its requirement is seen failing first
3. health.py check has no FAIL; land lane passes; no private name, figure, path or email in commits

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
