<!-- workflow-docs -->
# Home

skillset holds small, standalone agent skills. Each skill is a folder under `skills/` with a `SKILL.md` and the
scripts and templates it needs, so it works in Claude Code, Codex and other agents that read `SKILL.md`.

## Skills

Each skill has a page that says what it is for, what it promises and which tests hold each promise.

- [Bass-tab](Bass-tab): turns sources for a song into a compact bass tab and a one-or-two-page play-along chart PDF.

## Install a skill

Copy the skill's folder into your agent's skills directory, for example `cp -R skills/bass-tab ~/.claude/skills/bass-tab`
for Claude Code. Skills need `python3`; bass-tab also uses Pillow for a non-Latin title, artist or lyrics.

## Check

Run `sh tests/bass-tab/run.sh` from the repo root. The rows in `.loop/regression.tsv` run the same checks one promise
at a time, and the nightly regression workflow runs them on GitHub.
