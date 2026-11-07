"""An invented fixture song for the bass-tab skill: eight bars of root notes, no source, no lyrics.
It is no real song and never changes; baseline.tab beside it is what the render must produce."""

R = None


def steady(string, fret):
    return [{string: (fret, "")}] * 8


META = {
    "title": "Fixture Song",
    "artist": "Fixture Artist",
    "key": "E major",
    "tempo": 100,
    "time": "4/4",
    "tuning": "E A D G (standard 4-string)",
    "source": "invented for the skill baseline",
    "legend": "h = hammer-on  |  p = pull-off  |  s = slide  |  ~ = let ring  |  x = dead note  |  8 columns per bar = 8th notes",
}

BARS, CHORDS = {}, {}
for n, (string, fret, chord) in enumerate([("E", 0, "E"), ("E", 0, "E"), ("A", 0, "A"), ("E", 7, "B"),
                                           ("E", 0, "E"), ("E", 0, "E"), ("A", 0, "A"), ("E", 7, "B")], start=1):
    BARS[n] = steady(string, fret)
    CHORDS[n] = chord

SECTIONS = {n: {"name": v, "notes": [], "same_as": None} for n, v in {1: "Verse", 5: "Chorus"}.items()}
LYRICS = {}
