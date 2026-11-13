# (Gate A passed 2026-11-13: V1 format frozen on agent-workflow-template v0.27.58, issue #2881; owner approved starting the Mac migrations; run workflow-setup update --apply from the template at ~/.workflow-loop/template-v0.27.58 and close every gap setup.py migration-check reports, the #3780 false gaps are fixed) skillset is fully migrated to the current template: setup run at the current version until `setup.py migration-check` passes with no gap, keeping every reviewed line and the repo's own settings (owner, 2026-11-11: "for all the existing repo, do the migration to fully tighten it")

- Slug: migrate-skillset
- Touches: .loop, .github/workflows, docs/wiki, README.md, CLAUDE.md, AGENTS.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. migration-check passes in skillset with no gap
2. no reviewed requirement wording changes; every overridden setting keeps its value
3. no private name, path or email in commits
4. health (on this Mac, every 4 hours) and regression (this Mac for a private repo, GitHub Actions every 4 hours for a public one) are turned on and shown on with their cadence in the repo's README and Home Automation section
5. the repo's own routines are entered in the routine registry (none beyond health and regression) and show in the Automation section with on or off, cadence, where they run and last run
6. every stale or old published wiki page (no source in docs/wiki, retired, old format) is listed in the PR body for the owner; none is deleted until the owner's own yes (deletion is owner-only, after the merge)
7. Runbooks for any skillset routine in the registry; the repo's Automation section links each routine to it

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
1. In a checkout of this branch, run `python3 ~/.workflow-loop/template-v0.27.58/skills/workflow-setup/scripts/setup.py migration-check --pr`.
   Expect: `MIGRATION OK (--pr: state codes not checked)`.
2. Run the same command without `--pr`.
   Expect: only `MIG_WIKI_STALE` lines (Bass-tab, Home, Tests) and `MIGRATION: 3 gap(s) (0 PR-closable, 3 state)`.
3. Open README.md and docs/wiki/Home.md and find the Automation table.
   Expect: health, regression and digest email read `on (declared)`; health and regression read `every 4 hours`; each row names the Claude scheduled task skillset-health-regression and links a Runbook at the v0.27.58 tag.
4. After the merge, run `python3 ~/.workflow-loop/template-v0.27.58/skills/workflow-docs/scripts/docs.py publish` and then the full migration-check again.
   Expect: `MIGRATION: 0 gap(s)` (done line 1 passes in full).

## Behavior changes

- Regression now runs on this Mac every 4 hours (`regression_runs: mac`, `regression_cron: 17 */4 * * *`), not in GitHub Actions. `.github/workflows/regression.yml` is removed.
- The Automation table declares health, regression and digest email as run by the Mac's Claude scheduled task, each with a runbook link.
- `.loop/START.md`, CLAUDE.md, AGENTS.md and the Settings blocks are regenerated at template v0.27.58.

## Notes

- Design: .loop/goals/migrate-skillset.design.md. Plan and full review: .loop/goals/migrate-skillset.plan.md (accepted obligations C1-C18, D1-D9 and G1-G15).
- regression_runs is mac. That is what migration-check wants whenever regression_cron is on, public or private, and the operation session asked for consistency with it. Done line 4's wording names GitHub Actions for a public repo; UC1 records this for the owner.
- regression_cron's old value `17 9 * * *` was the template default at adoption (template 17017962, settings.py:35), not an owner override. Every other config value is unchanged; the config diff shows only template_version, regression_cron, regression_runs and the added automation.
- skillset main has no branch protection and no rulesets, so removing regression.yml blocks no PR. A public repo gets no pr-lane statuses (template private.py:346).
- `docs.py automation` checks launchctl, so it reports the Claude scheduled task as "not loaded". The real liveness check is the scheduled task itself and its logs.
- Follow-ups for the template (out of scope here):
  - E4: the renderer says "launch agent" for a Claude scheduled task.
  - E4: `docs.py automation` liveness should check scheduled tasks, as MIG_TASK does.
  - E4: the digest_mail help still names Actions secrets.
  - E4: `regression.py workflow` says "this repo is private" for a public repo recorded mac.
  - E4: there is no missed-cycle health rule.
  - E4: the Tests page links a run with an empty run field to `actions/workflows/regression.yml` (render.py `run_cell`). For a mac repo it should say local.
  - E4: a non-cron cadence ("with each health round") renders as "cron `...`".
  - E4: health and regression both point at one Mac task, so the separate :47/:17 minutes are nominal. Both run every 4 hours in one round.
  - E5: a "migrate a repo" recipe.
- Release tags no longer trigger a regression run, because the removed workflow's `push: tags v*` trigger is gone. The Mac round runs every 4 hours on origin/main, and the ci_levels help text that mentions tag runs is template wording. Accepted under UC1 (Actions cannot run here).
- The Mac routine runs the template's scripts from the owner's template checkout, not from the pinned v0.27.58 copy. This is outside this repo (the routine prompt lives in the private routines folder), and is listed for the owner.
- No file under skills/ changed (`git diff origin/main -- skills/` is empty).
