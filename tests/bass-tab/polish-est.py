"""Invented fixture: estimated bars equal to their neighbours, with long chord names on them.
Groove: one figure, bars 3 and 6 estimated. Turn: a two-bar figure whose third copy holds bar 14."""

META = {"title": "Estimate Fixture", "artist": "Fixture Artist", "tempo": 100, "time": "4/4"}
ONE = [{"A": (3, "")}] + [None] * 7
X = [{"E": (5, "")}] + [None] * 7
Y = [{"A": (7, "")}] + [None] * 7
BARS = {n: ONE for n in range(1, 9)}
BARS.update({n: (X if n % 2 else Y) for n in range(9, 17)})
CHORDS = {3: "Gmaj7#11/Bb", 6: "Gmaj7#11/Bb", 14: "Gmaj7#11/Bb"}
SECTIONS = {1: {"name": "Groove", "notes": [], "same_as": None},
            9: {"name": "Turn", "notes": [], "same_as": None}}
REPORT = {"missing": [], "estimates": [3, 6, 14]}
