"""Invented fixture: sections that equal an earlier one in notes, where only one of the two holds
an estimated bar. A and B must be drawn out, C may collapse to a reference."""

META = {"title": "Section Estimate Fixture", "tempo": 100, "time": "4/4"}
BARS = {}
for base, first in ((1, 1), (5, 1), (9, 5), (13, 5), (17, 9), (21, 9)):
    for k in range(4):
        BARS[base + k] = [{"E": (first + k, "")}] + [None] * 7
SECTIONS = {n: {"name": name, "notes": [], "same_as": None}
            for n, name in ((1, "A"), (5, "A again"), (9, "B"), (13, "B again"), (17, "C"), (21, "C again"))}
REPORT = {"missing": [], "estimates": [2, 14]}
