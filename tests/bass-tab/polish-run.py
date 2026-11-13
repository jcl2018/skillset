"""Invented fixture: runs of missing bars. A has one lone missing bar (5); B opens with a long run (9-38);
C has bar 45 with a lyric, 46 plain and 47 with a chord, each its own bar, and a run 49-50 that continues
into D as 51-52 (a run never crosses a section start)."""

META = {"title": "Run Fixture", "tempo": 100, "time": "4/4"}
BARS = {n: [{"E": (n % 12, "")}] + [None] * 7 for n in range(1, 57)}
SECTIONS = {n: {"name": name, "notes": [], "same_as": None}
            for n, name in ((1, "A"), (9, "B"), (41, "C"), (51, "D"))}
MISSING = [5] + list(range(9, 39)) + [45, 46, 47, 49, 50, 51, 52]
for _n in MISSING:
    BARS[_n] = [None] * 8
CHORDS = {47: "Am"}
LYRICS = {45: "la"}
REPORT = {"missing": MISSING, "estimates": []}
