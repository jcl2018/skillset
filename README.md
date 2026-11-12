# skillset

<!-- template:begin -->
Built with the [jcl2018/agent-workflow-template](https://github.com/jcl2018/agent-workflow-template) workflow loop.
<!-- template:end -->

Small, standalone agent skills. Each skill is a folder under `skills/` with a `SKILL.md` and whatever
scripts and templates it needs, so it is portable across Claude Code, Codex and other agents that read
`SKILL.md`. Skills are meant to be listed on [Agensi](https://agensi.io) later.

| skill | what it does |
|---|---|
| [`bass-tab`](skills/bass-tab/SKILL.md) | Turns sources for a song into a compact bass tab plus a 1-2 page play-along chart PDF (sections, repeats, chords, lyrics) |

## How to use

Say these to your agent. Each skill's wiki page has the exact commands.

### How to use Bass tab

| You say | What happens |
|---|---|
| "Make a bass tab of this song from these sources" | A song file is written from what the sources show, then the compact tab and a one-or-two-page chart PDF are made. |
| "Fix bar 12 in this tab and print it again" | The song file is corrected once, so every copy of a repeated figure changes, and the chart is printed again. |
| "Make the chart for this 5-string song with a low B" | The tab draws five string lines, labeled to match the tuning. |
| "What's in the header and where did each part come from?" | You get the header (title, artist, BPM, key, time signature, tuning, instrument and sources, "not shown" where a source doesn't say) and the source report. |
| "Which bars are missing or guessed?" | The source report lists missing bars, estimated bars and which source gave each section. |

## Install a skill

Copy the skill's folder into your agent's skills directory.

```sh
# Claude Code (all projects)
cp -R skills/bass-tab ~/.claude/skills/bass-tab
# or one project
cp -R skills/bass-tab <project>/.claude/skills/bass-tab
```

For Codex or another agent that reads `SKILL.md`, put the folder wherever that agent looks for skills
(for example `~/.codex/skills/` or `.agents/skills/`). Skills use `python3` and the standard library; bass-tab also uses Pillow for a non-Latin title, artist or lyrics, and without it refuses rather than print `?` unless told `--allow-lossy`.

## Use bass-tab

Ask your agent for a bass tab and give it sources (a screenshot or PDF of a tab, notes, links). It writes
a song file from what the sources show, then renders it:

```sh
cd skills/bass-tab
python3 scripts/tabgen.py song/song.py song/song.tab --bars 3 --cut compact
python3 scripts/chart2pdf.py song/song.py -o song/song.pdf   # 1-2 page chart
```

Start a song file from `skills/bass-tab/templates/song-template.py`. Links to recordings contribute a
title, tempo and section names at most; the skill never invents bars or lyrics (lyrics come from the owner or from what a source visibly shows).

## Check

```sh
sh tests/bass-tab/run.sh
```

Renders the fixture song, compares the text tab with a recorded baseline, builds the PDF, and checks script
sizes (each under 20 KB) and that no personal strings are present.

## License

MIT, see [LICENSE](LICENSE).

<!-- settings:begin -->
## Settings

Every repo setting from the template's settings reference, with this repo's value from `.loop/config.json`.

| Name | What it means | How to set it | Default | This repo |
|---|---|---|---|---|
| `base` | The branch goals start from and pull requests target. | set "base" in .loop/config.json | `main` | default |
| `agent_command` | The command that runs a goal in the background; the prompt is its last argument. | set "agent_command" in .loop/config.json | `[]` | **overridden:** `["claude", "-p", "--model", "claude-sonnet-5-5", "--allowedTools=Bash,Read,Write,Edit,Skill,Glob,Grep"]` |
| `parallel` | Workers running at once; 0 means unlimited. | set "parallel" in .loop/config.json | `0` | default |
| `cadence` | Minutes between check-ins of the operation session, 1 to 60, or off. | set "cadence" in .loop/config.json | `30` | **overridden:** `30` |
| `auto_approve` | true approves what a flow step leaves for the owner, logged as auto-approved. | set "auto_approve" in .loop/config.json | `false` | **overridden:** `true` |
| `auto_merge` | true lets the release step merge a goal's pull request and publish its release. | set "auto_merge" in .loop/config.json | `false` | **overridden:** `true` |
| `pr_bumps_version` | true moves the last number of the version file once on a goal's branch. | set "pr_bumps_version" in .loop/config.json | `false` | default |
| `version_file` | The file that holds the version; a release bumps it and writes the changelog. | set "version_file" in .loop/config.json | `VERSION` | default |
| `routines` | Commands the release step runs on the base branch before it merges. | set "routines" in .loop/config.json | `[]` | default |
| `regression_cron` | Five cron fields: when the regression routine runs in GitHub Actions; off turns it off. | set "regression_cron" in .loop/config.json | `17 */4 * * *` | **overridden:** `17 9 * * *` |
| `health_cron` | Five cron fields: when the health routine and its digest run in GitHub Actions; off turns it off. | set "health_cron" in .loop/config.json | `47 */4 * * *` | default |
| `judge_env` | The Actions secret holding the agent key; the scheduled judge runs only when it is set. | set "judge_env" in .loop/config.json | `ANTHROPIC_API_KEY` | default |
| `judge_setup` | A command the scheduled health run uses to install judge_command's program, run only with the secret. | set "judge_setup" in .loop/config.json | `(empty)` | default |
| `digest_owner` | Who the digest comment mentions; empty means the repo owner (an organisation notifies no one). | set "digest_owner" in .loop/config.json | `(empty)` | default |
| `digest_mail` | How the round's digest is mailed: cloudflare (Email Service), smtp, or off; the address and keys live only in Actions secrets. | set "digest_mail" in .loop/config.json | `cloudflare` | default |
| `smtp_host` | The SMTP server digest_mail smtp sends through (with DIGEST_SMTP_USER and DIGEST_SMTP_PASSWORD secrets). | set "smtp_host" in .loop/config.json | `smtp.gmail.com` | default |
| `smtp_port` | 465 (TLS) or 587 (STARTTLS) for digest_mail smtp. | set "smtp_port" in .loop/config.json | `465` | default |
| `review_depth` | full runs the plan and review skills' whole pipeline and refuses a condensed one; condensed allows a shorter run. | set "review_depth" in .loop/config.json | `full` | default |
| `criteria` | true makes docs check enforce the PRD page contract (Problem, Requirements, Non-goals, Success metrics, Tests). | set "criteria" in .loop/config.json | `true` | default |
| `criteria_max` | Most criteria a wiki page may hold, 1 to 50, default 10; docs check and health fail a page over it. | set "criteria_max" in .loop/config.json | `10` | default |
| `wiki_dir` | The folder of wiki pages. | set "wiki_dir" in .loop/config.json | `docs/wiki` | default |
| `risky_paths` | Regexes for paths whose goals need extra care. | set "risky_paths" in .loop/config.json | `["^\\.github/", "(^|/)auth", "(^|/)migrations?/", "(^|/)(schema|data)\\b"]` | default |
| `step_limit` | Seconds one flow step may run when the flow file sets no limit; 0 means the built-in limit. | set "step_limit" in .loop/config.json | `0` | default |
| `goal_lane_minutes` | Minutes a goal's regression lane may take before health warns and its LANE line says over. | set "goal_lane_minutes" in .loop/config.json | `10` | default |
| `goal_levels` | Row levels a goal lane plans from: land, or nightly for land and nightly rows. | set "goal_levels" in .loop/config.json | `land` | default |
| `ci_levels` | Target of the scheduled and tag regression runs: nightly (every row) or land. | set "ci_levels" in .loop/config.json | `nightly` | default |
| `token_budget` | Tokens a goal may spend over all steps before no new step starts; 0 means no budget. | set "token_budget" in .loop/config.json | `0` | default |
| `test_budget_minutes` | Minutes one in-loop test run (qa, ship, pull request) may take, 15 or more; rows past it are left to the scheduled full suite. | set "test_budget_minutes" in .loop/config.json | `15` | default |
| `prep_budget_minutes` | Minutes a lane may spend before its first test row (preparing, planning, waiting for a slot), 15 or more; a lane past it stops and says which part ran long. | set "prep_budget_minutes" in .loop/config.json | `15` | default |
| `step_budget_minutes` | Minutes one review or ship step may take, 15 or more; a step at its limit finishes with what it has done and records what it left. | set "step_budget_minutes" in .loop/config.json | `30` | default |
| `stale_branch_days` | Days a local branch on no remote may sit before health lists it with its removal command. | set "stale_branch_days" in .loop/config.json | `14` | default |
| `mend` | true lets watch start a fresh agent for a failed goal. | set "mend" in .loop/config.json | `false` | default |
| `mend_wait` | Seconds a failed goal waits before a mender starts. | set "mend_wait" in .loop/config.json | `120` | default |
| `max_tries` | Failed tries a goal gets before it stops and files a finding. | set "max_tries" in .loop/config.json | `3` | default |
| `resume_on_limit` | true lets watch resume a goal that hit a usage limit. | set "resume_on_limit" in .loop/config.json | `false` | default |
| `limit_wait` | Seconds to wait after a usage limit before resuming. | set "limit_wait" in .loop/config.json | `1800` | default |
| `watch_interval` | Seconds between rounds of watch. | set "watch_interval" in .loop/config.json | `20` | default |
| `agent_files` | Agent entry files setup wires the workflow-loop block into; [] turns wiring off. | set "agent_files" in .loop/config.json | `["CLAUDE.md", "AGENTS.md"]` | default |
| `template_repo` | The template's GitHub repo (owner/name) update reads releases from, when the installed package names none. | set "template_repo" in .loop/config.json | `(empty)` | default |
| `reply_hook` | false turns off the reply-format hook (setup.py --reply-hook installs it) in the operation session. | set "reply_hook" in .loop/config.json | `true` | default |
| `govern_hook` | false turns off the govern-only hook (setup.py --govern-hook installs it): edits, commits and pushes refused in the operation session. | set "govern_hook" in .loop/config.json | `true` | default |
| `full_auto` | true lets the operation session answer a worker's routine decision with its recommended option, logged; risky ones wait. | set "full_auto" in .loop/config.json | `true` | default |
| `pool_size` | Idle worker sessions the session pool keeps; when it runs low the operation session asks you to create the missing ones. | set "pool_size" in .loop/config.json | `20` | default |
| `silent_minutes` | Minutes a worker may send nothing before it shows under Needs you; LOOP_SESSION_QUIET (seconds) overrides it. | set "silent_minutes" in .loop/config.json | `30` | default |
| `feature_labels` | true makes health file and the regression workflow tag each issue feature:<Page> for its feature, and create that label; off by default, so issues carry their group or regression label only. | set "feature_labels" in .loop/config.json | `false` | default |
<!-- settings:end -->

<!-- automation:begin -->
## Automation

Health and regression, then each `automation` entry in `.loop/config.json`; to add one, add an entry.

| Routine | What it does | State | Cadence | Runs on | Last run | Owed by you |
|---|---|---|---|---|---|---|
| health | Checks the repo and files each finding. | off | every 4 hours | not deployed | docs.py automation | run workflow-setup to write .github/workflows/health.yml |
| regression | Runs every regression row, files each failure. | on | daily at 09:17 | GitHub Actions (regression.yml) | docs.py automation | none |
| digest email | Mails one digest per health round. | off | cron `with each health round` | not deployed | docs.py automation | run workflow-setup to write .github/workflows/health.yml |
<!-- automation:end -->
