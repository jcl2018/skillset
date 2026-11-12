# health-clear design

Problem: workflow-health reports docs drift (Home, README, Bass-tab review), a missing health.yml, and a requirement (BAS-6) with no row the workflow runs.

Approaches:
1. Run the generators (criteria.py render, entry.py write, automation.py workflow) and add rows. Low cost, low risk; output is deterministic.
2. Hand-edit the pages. Higher cost, drifts again.

Chosen: 1. BAS-6 is a person-checked criterion, so its nightly row runs the source-report test (BAS-8), the nearest machine check; a goal row guards this goal's health.yml file.

Done lines: health check green (only the nightly-freshness warning, which a first nightly run clears after merge); issues 10-16 close when the PR merges.

Open questions: none.
