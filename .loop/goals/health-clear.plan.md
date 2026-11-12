# health-clear plan

Checked against the code: `.loop/regression.tsv`, `docs/wiki/Home.md`, `docs/wiki/Tests.md`, `docs/wiki/Bass-tab.md`, `README.md`, `.loop/START.md` exist; `.github/workflows/health.yml` is absent.

Build steps (in order)
1. `criteria.py render` and `entry.py write`: regenerate Home Settings/Automation, README line and blocks, Tests page.
2. `automation.py workflow`: write `.github/workflows/health.yml` (and `mail-test.yml`).
3. `criteria.py review Bass-tab --user`: records the owner's review of the edited Usage section (delegated by the user's instruction to decide without asking).
4. `regression.py add` rows: `bas-sources-only` (nightly, BAS-6, runs the BAS-8 report test) and `health-clear-1` (nightly, checks health.yml exists); `regression.py red` for both after commit.
5. `regression.py sync` must print SYNC OK; `health.py check` must have no FAIL/UNREAD.

Test per done line: health-clear-1 is red when health.yml is moved away, green with it present; health.py check green is the done line.

Could break: generated blocks overwritten by a later render (they come from the same generator); the nightly row needs the report test to stay.

Out of scope: git hooks (machine-local, installed separately), the first nightly run (clears the freshness WARN after merge), any bass-tab code.
