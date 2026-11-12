"""Invented fixture: identical bass under different chords, and a chord named once for a figure.
Bars 1-4 share one bass line, chords A at bar 1 and D at bar 3. Sections 2-4 share one bass line:
chord E in section 2, G in section 3, nothing named in section 4 (G stays in force)."""

META = {"title": "Chord Fixture", "tempo": 100, "time": "4/4"}
BARS = {n: [{"E": (2, "")}] + [None] * 7 for n in range(1, 5)}
for base in (5, 9, 13):
    for k in range(4):
        BARS[base + k] = [{"A": (3 + k, "")}] + [None] * 7
CHORDS = {1: "A", 3: "D", 5: "E", 9: "G"}
SECTIONS = {n: {"name": name, "notes": [], "same_as": None}
            for n, name in ((1, "One"), (5, "Two"), (9, "Three"), (13, "Four"))}
