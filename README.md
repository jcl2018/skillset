# skillset

Small, standalone agent skills. Each skill is a folder under `skills/` with a `SKILL.md` and whatever
scripts and templates it needs, so it is portable across Claude Code, Codex and other agents that read
`SKILL.md`. Skills are meant to be listed on [Agensi](https://agensi.io) later.

| skill | what it does |
|---|---|
| [`bass-tab`](skills/bass-tab/SKILL.md) | Turns sources for a song into a compact bass tab plus a 1-2 page play-along chart PDF (sections, repeats, chords, lyrics) |

## Install a skill

Copy the skill's folder into your agent's skills directory.

```sh
# Claude Code (all projects)
cp -R skills/bass-tab ~/.claude/skills/bass-tab
# or one project
cp -R skills/bass-tab <project>/.claude/skills/bass-tab
```

For Codex or another agent that reads `SKILL.md`, put the folder wherever that agent looks for skills
(for example `~/.codex/skills/` or `.agents/skills/`). Skills use only `python3` and the standard library.

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
