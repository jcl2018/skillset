"""An invented song too long for two pages: 400 bars, no two alike."""
META = {"title": "Huge Fixture", "artist": "Fixture Artist", "tempo": 100}
BARS = {n: [{"E": (n % 12, "")}, {"A": ((n * 7) % 12, "")}] * 4 for n in range(1, 401)}
for n in BARS:
    BARS[n] = [{"E": ((n * k) % 13, "")} for k in range(1, 9)]
SECTIONS = {1: {"name": "Only", "notes": [], "same_as": None}}
LYRICS = {}
