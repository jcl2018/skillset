"""Invented fixture: a 5-string bass song with a low B."""

META = {"title": "Five String Fixture", "artist": "Fixture Artist", "strings": 5,
        "instrument": "5-string bass", "tuning": "B E A D G (standard 5-string)"}
BARS = {n: [{"B": (n, "")}, {"E": (2, "")}] * 4 for n in range(1, 5)}
CHORDS = {n: "C" for n in range(1, 5)}
SECTIONS = {1: {"name": "Verse", "notes": [], "same_as": None}}
