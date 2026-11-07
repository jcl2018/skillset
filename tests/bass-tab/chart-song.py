"""An invented song for the chart renderer test: no real song, no real words.
Sections, a repeated figure, a repeated section with the same words, and lyrics under some bars."""


def steady(string, fret):
    return [{string: (fret, "")}] * 8


META = {"title": "Chart Fixture", "artist": "Fixture Artist", "key": "E major", "tempo": 100,
        "time": "4/4", "tuning": "E A D G (standard 4-string)", "source": "invented for the test"}

roots = [("E", 0, "E"), ("E", 0, "E"), ("A", 0, "A"), ("E", 7, "B")]
BARS, CHORDS, LYRICS = {}, {}, {}
for n in range(1, 25):
    string, fret, chord = roots[(n - 1) % 4]
    BARS[n] = steady(string, fret)
    CHORDS[n] = chord
# bars 9-12 differ so the verse is not a repeat of the intro
for n in range(9, 13):
    BARS[n] = [{"E": (n - 8, "")}, None] * 4
# bars 13-16 and 21-24 are the same chorus, with the same words
for n, words in {13: "la la la", 14: "tum tum", 15: "la la la", 16: "tum tum"}.items():
    LYRICS[n] = words
    LYRICS[n + 8] = words
LYRICS[9], LYRICS[10] = "first line here", "second line here"
SECTIONS = {n: {"name": v, "notes": [], "same_as": None}
            for n, v in {1: "Intro", 5: "Verse", 13: "Chorus", 17: "Bridge", 21: "Chorus 2"}.items()}
