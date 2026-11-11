"""A song file for the bass-tab skill. Fill in what a source actually shows; leave the rest out.

Frets are written per slot as {string: (fret, mark)}; None is "still ringing / nothing struck",
{} is an explicit rest. A repeated figure is written ONCE and stamped wherever it is played.
Chart PDF:  python3 scripts/chart2pdf.py song.py -o song.pdf
Text tab:   python3 scripts/tabgen.py song.py song.tab --bars 3 --cut compact
"""

R = None  # a rest/ring slot


def steady(string, fret, mark=""):
    """Eight eighth notes on one string and fret (8 slots per bar)."""
    return [{string: (fret, mark)}] * 8


META = {
    "title": "Song Title",
    "artist": "Artist",
    "key": "E major",              # leave out if unknown; the key check then says it did not run
    "tempo": 100,                  # BPM; leave out if the source does not print it
    "time": "4/4",
    "tuning": "E A D G (standard 4-string)",
    "source": "where the notes were read from",
    "legend": "h = hammer-on  |  p = pull-off  |  s = slide  |  ~ = let ring  |  x = dead note  |  8 columns per bar = 8th notes",
    # "strings": 5,                # 5-string bass (low B): the chart draws five labeled lines
    # "instrument": "4-string bass",
    # "sources": ["a link", "a screenshot"],   # instead of "source", never both
    # "slots": 16,                 # 16th-note resolution; use --bars 1 when rendering
    # "open": {"E": "D"},          # drop D: the bottom row prints as D
}

# bar number -> list of 8 slots. The chord of each bar fixes which string a fret is on.
BARS = {1: steady("E", 0), 2: steady("A", 0)}
CHORDS = {1: "E", 2: "A"}
SECTIONS = {1: {"name": "Verse", "notes": [], "same_as": None}}

# Words under each bar: {bar number: "words"}. Only from the owner or what a source visibly shows
# (e.g. on-screen lyrics); never invented. Leave it empty when no source shows them.
LYRICS = {}

# Optional: the source report, printed after the last line. Absent parts print "not shown".
# REPORT = {"missing": [7], "estimates": [3, 4], "sections": {1: "a link"}}

# Optional: what the sheet does not know. Printed in every cut.
# CAVEATS = [("Not verified", ["Rhythm was read by eye.", "Frets were not measured."])]
