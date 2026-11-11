"""Invented fixture: a song with a source report. Section 2 names no source."""

META = {"title": "Report Fixture", "artist": "Fixture Artist", "key": "A minor", "tempo": 90,
        "time": "4/4", "tuning": "E A D G (standard 4-string)", "instrument": "4-string bass",
        "sources": ["invented source one", "invented source two"]}
BARS = {n: [{"A": (n % 3, "")}] * 8 for n in range(1, 9)}
CHORDS = {n: "A" for n in range(1, 9)}
SECTIONS = {1: {"name": "Verse", "notes": [], "same_as": None},
            5: {"name": "Chorus", "notes": [], "same_as": None}}
REPORT = {"missing": [7], "estimates": [3, 4], "sections": {1: "invented source one"}}
