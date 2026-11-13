"""Lyric band checks on an invented placeholder fixture: no lyric box touches a string line, a digit, a stem, an
estimate mark, a repeat count or another text, none leaves its bar, and the 2-page limit and 9 pt floor hold.
Usage: lyric_test.py boxes|norhythm|limits|order"""
import json
import os
import re
import sys
import tempfile

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "..", "skills", "bass-tab", "scripts"))
import chart2pdf  # noqa: E402
import chartformat  # noqa: E402
from pdfkit import string_width  # noqa: E402

TXT, RULES, STEMS, APPROX, BARS = [], [], [], [], []
_t, _r, _s, _a, _db = (chart2pdf.PDF.text, chart2pdf.PDF.rule, chart2pdf.PDF.stem, chart2pdf.PDF.approx,
                       chart2pdf.draw_bar)


def spy_text(self, x, y, s, font, size, gray=0.0):
    TXT.append((x, y, s, font, size))
    return _t(self, x, y, s, font, size, gray)


def spy_rule(self, x0, y, x1, gray=0.75):
    RULES.append((x0, y, x1, gray))
    return _r(self, x0, y, x1, gray)


def spy_stem(self, x, y0, y1, w=0.7):
    STEMS.append((x, min(y0, y1), max(y0, y1)))
    return _s(self, x, y0, y1, w)


def spy_approx(self, cx, cy, w=7.0, gray=0.2):
    APPROX.append((cx - w / 2.0, cx + w / 2.0, cy - w * 0.4, cy + w * 0.4))
    return _a(self, cx, cy, w, gray)


def spy_bar(pdf, song, cfg, num, x0, bw, ys, g):
    BARS.append((x0, x0 + bw, ys[-1]))
    return _db(pdf, song, cfg, num, x0, bw, ys, g)


chart2pdf.PDF.text, chart2pdf.PDF.rule, chart2pdf.PDF.stem = spy_text, spy_rule, spy_stem
chart2pdf.PDF.approx, chart2pdf.draw_bar = spy_approx, spy_bar


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def template(rhythm=None, extra=None):
    raw = json.load(open(chartformat.DEFAULT, encoding="utf-8"))
    if rhythm is not None:
        raw["ladder"] = [r for r in raw["ladder"] if r["rhythm"] == rhythm]
    raw.update(extra or {})
    p = os.path.join(tempfile.mkdtemp(), "t.json")
    json.dump(raw, open(p, "w"))
    return p


def render(name="lyric-long.py", tpl=None):
    for lst in (TXT, RULES, STEMS, APPROX, BARS):
        lst.clear()
    song = chart2pdf.read_song(os.path.join(here, name))
    _, st = chart2pdf.render(song, "letter", template=tpl)
    return song, st


def box(t):
    x, y, s, font, size = t
    return (x, x + string_width(s, font, size), y - 0.25 * size, y + 0.95 * size)


def hit(a, b):
    return a[0] < b[1] and b[0] < a[1] and a[2] < b[3] and b[2] < a[3]


def check(song, st, label):
    words = set()
    for v in song["lyrics"].values():
        words.update(v.replace(" ", ""))
    lyr = [t for t in TXT if t[3] == "F3" and t[2] and all(c in words for c in t[2].replace(" ", ""))]
    if len(lyr) < len(set(song["lyrics"].values())):
        fail("%s: %d lyric pieces drawn for %d lyrics (text lost)" % (label, len(lyr), len(set(song["lyrics"].values()))))
    got = "".join(t[2] for t in lyr).replace(" ", "")
    for n, v in song["lyrics"].items():
        if v.replace(" ", "") not in got:
            fail("%s: the lyric of bar %d is not all drawn (text lost)" % (label, n))
    at = {(round(t[0], 2), round(t[1], 2)) for t in lyr}       # a lossy "??" redraw sits where its lyric is
    others = [t for t in TXT if t not in lyr and t[2].strip() and (round(t[0], 2), round(t[1], 2)) not in at]
    for i, a in enumerate(lyr):
        ba = box(a)
        for r in RULES:
            if r[3] == 0.45 and r[0] - 0.5 < ba[1] and ba[0] < r[2] + 0.5 and ba[2] - 0.4 < r[1] < ba[3] + 0.4:
                fail("%s: lyric %r sits on a string line" % (label, a[2]))
        for o in others:
            if hit(ba, box(o)):
                fail("%s: lyric %r overlaps %r (a digit, mark, chord or number)" % (label, a[2], o[2]))
        for m in APPROX:
            if hit(ba, m):
                fail("%s: lyric %r overlaps an estimate mark" % (label, a[2]))
        for sx, y0, y1 in STEMS:
            if ba[0] < sx < ba[1] and ba[2] < y1 and y0 < ba[3]:
                fail("%s: lyric %r crosses a stem or bar line" % (label, a[2]))
        for b in lyr[i + 1:]:
            if hit(ba, box(b)):
                fail("%s: lyrics %r and %r overlap" % (label, a[2], b[2]))
        own = [b for b in BARS if b[0] - 0.01 <= a[0] < b[1] and b[2] > ba[3]]
        if not own:
            fail("%s: lyric %r is under no bar" % (label, a[2]))
        b = min(own, key=lambda q: q[2] - ba[3])
        if ba[1] > b[1] + 0.01:
            fail("%s: lyric %r runs %.1f pt past its bar" % (label, a[2], ba[1] - b[1]))
    if st["pages"] > 2 or st["tab_font_pt"] < 9:
        fail("%s: pages=%s tab_font_pt=%s break the 2-page limit or the 9 pt floor" % (label, st["pages"], st["tab_font_pt"]))


def boxes():
    check(*render(), "default")
    print("boxes ok")


def norhythm():
    song, st = render(tpl=template(rhythm=False))
    check(song, st, "no rhythm row")
    print("norhythm ok")


def limits():
    song, st = render("chart-song.py")
    if st["pages"] > 2 or st["tab_font_pt"] < 9:
        fail("chart-song: pages=%s tab_font_pt=%s" % (st["pages"], st["tab_font_pt"]))
    t = chartformat.load()
    if not hasattr(t.lyrics, "min_size") or t.lyrics.min_size > t.lyrics.size:
        fail("the template has no lyrics.min_size at or under lyrics.size")
    print("limits ok")


def order():
    """A lyric is widened, then wrapped, then shrunk, then cut: never cut while a bigger option fits."""
    song, _ = render()
    t = chartformat.load()
    sizes = [x[4] for x in TXT if x[3] == "F3" and x[4] <= t.lyrics.size and x[4] != t.bar_numbers.size
             and re.search(r"[一-鿿]", x[2])]
    if not sizes or max(sizes) != t.lyrics.size or min(sizes) < t.lyrics.min_size:
        fail("lyric sizes %r are not between the template minimum and size" % sorted(set(sizes)))
    if "…" in "".join(x[2] for x in TXT):
        fail("the fixture's longest lyric was cut with an ellipsis instead of fitted")
    print("order ok")


CASES = {"boxes": boxes, "norhythm": norhythm, "limits": limits, "order": order}
if len(sys.argv) != 2 or sys.argv[1] not in CASES:
    fail("usage: lyric_test.py %s" % "|".join(CASES))
CASES[sys.argv[1]]()
