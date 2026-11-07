"""Chart renderer test on invented songs: section labels, collapsed repeats, lyric alignment, page limit."""
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "..", "skills", "bass-tab", "scripts"))
import chart2pdf  # noqa: E402

texts = []
orig = chart2pdf.PDF.text


def spy(self, x, y, s, font, size, gray=0.0):
    texts.append((round(x, 2), round(y, 2), s, font, size))
    return orig(self, x, y, s, font, size, gray)


chart2pdf.PDF.text = spy


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


song = chart2pdf.read_song(os.path.join(here, "chart-song.py"))
data, stats = chart2pdf.render(song, "letter")
if not data.startswith(b"%PDF-"):
    fail("not a PDF")

# section labels: bold, one per section
bold = [t[2] for t in texts if t[3] == "F2"]
for name in ("Intro", "Verse", "Chorus", "Bridge", "Chorus 2"):
    if name not in bold:
        fail("no bold section label %r" % name)

# collapsed repeats: the intro's repeated bars print once with a count
if "x2" not in bold:
    fail("no collapsed repeat count")
printed_bars = sum(len(u["bars"]) for u in chart2pdf.pack(
    chart2pdf.plan_units(song, chart2pdf.LADDER[0], 480), 480)[0] if u["kind"] == "bars")
if printed_bars >= len(song["bars"]):
    fail("repeats were not collapsed")

# lyrics sit under their own bar: same x as the chord over that bar, and below it
lyr = [t for t in texts if t[2] in ("la la la", "tum tum", "first line here")]
if len(lyr) < 8:
    fail("lyrics missing: %d" % len(lyr))
for x, y, s, _f, _z in lyr:
    if not any(c[0] == x and c[1] > y and c[3] == "F2" for c in texts):
        fail("lyric %r at x=%s has no chord above it" % (s, x))

# a repeated section with the same words collapses to one reference line when asked
texts.clear()
_, st2 = chart2pdf.render(song, "letter", refs_only=True)
if st2["section_refs"] < 1:
    fail("a repeated section was not reduced to a reference")

# a song with no lyrics renders cleanly, on one page
plain = chart2pdf.read_song(os.path.join(here, "fixture-song.py"))
_, st3 = chart2pdf.render(plain, "letter")
if st3["pages"] != 1 or any(t[2] == "None" for t in texts):
    fail("lyric-free song did not render cleanly")

# the page limit: digits stay at 9 pt or more, and a song that cannot fit is refused by name
if stats["tab_font_pt"] < 9:
    fail("tab digits under 9 pt")
huge = chart2pdf.read_song(os.path.join(here, "chart-huge.py"))
try:
    chart2pdf.render(huge, "letter")
except SystemExit as e:
    if "Huge Fixture" not in str(e):
        fail("refusal does not name the song: %s" % e)
else:
    fail("a 400-bar song was not refused")

print("chart ok: pages=%d font=%spt refs=%d" % (stats["pages"], stats["tab_font_pt"], st2["section_refs"]))
