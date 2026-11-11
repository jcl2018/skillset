"""Invented fixture: a song whose source shows only a title. Every other header field is absent."""

META = {"title": "Sparse Fixture"}
BARS = {n: [{"E": (0, "")}] * 8 for n in range(1, 5)}
CHORDS = {n: "E" for n in range(1, 5)}
SECTIONS = {1: {"name": "Verse", "notes": [], "same_as": None}}
