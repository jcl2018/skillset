"""Chart polish checks on invented songs. Usage: polish_test.py 1|2|...|9 (one per layout fix)."""
import os
import re
import subprocess
import sys
import tempfile

here = os.path.dirname(os.path.abspath(__file__))
scripts = os.path.join(here, "..", "..", "skills", "bass-tab", "scripts")
sys.path.insert(0, scripts)
import chart2pdf  # noqa: E402
import chartplan  # noqa: E402

TXT, RULES, REPS, APPROX, DRAWN, LINES = [], [], [], [], [], []
_t, _r, _rb = chart2pdf.PDF.text, chart2pdf.PDF.rule, chart2pdf.PDF.repeat_bar
_db, _pack = chart2pdf.draw_bar, chart2pdf.pack


def spy_text(self, x, y, s, font, size, gray=0.0):
    TXT.append((x, y, s, font, size))
    return _t(self, x, y, s, font, size, gray)


def spy_rule(self, x0, y, x1, gray=0.75):
    RULES.append((x0, y, x1, gray))
    return _r(self, x0, y, x1, gray)


def spy_rep(self, x, y0, y1, opening):
    REPS.append((x, opening))
    return _rb(self, x, y0, y1, opening)


def spy_bar(pdf, song, cfg, num, *a):
    DRAWN.append(num)
    return _db(pdf, song, cfg, num, *a)


def spy_pack(*a, **k):
    out = _pack(*a, **k)
    LINES[:] = out
    return out


chart2pdf.PDF.text, chart2pdf.PDF.rule, chart2pdf.PDF.repeat_bar = spy_text, spy_rule, spy_rep
chart2pdf.draw_bar, chart2pdf.pack = spy_bar, spy_pack
if hasattr(chart2pdf.PDF, "approx"):
    _ap = chart2pdf.PDF.approx

    def spy_approx(self, *a, **k):
        APPROX.append(a)
        return _ap(self, *a, **k)
    chart2pdf.PDF.approx = spy_approx


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def render(name, **kw):
    for lst in (TXT, RULES, REPS, APPROX, DRAWN, LINES):
        lst.clear()
    path = name if os.path.isabs(name) else os.path.join(here, name)
    try:
        _, st = chart2pdf.render(chart2pdf.read_song(path), "letter", **kw)
    except TypeError as e:
        fail("render does not take the option: %s" % e)
    return st


def strs():
    return [t[2] for t in TXT]


def tpl():
    return chart2pdf.chartformat.load()


def mutant(name, old, new):
    src = open(os.path.join(here, name)).read()
    if old not in src:
        fail("mutant: %r not in %s" % (old, name))
    p = os.path.join(tempfile.mkdtemp(), "m.py")
    open(p, "w").write(src.replace(old, new))
    return p


def c1():
    song = chart2pdf.read_song(os.path.join(here, "v2-report.py"))
    cfg = chart2pdf.ladder(tpl())[0]
    bw = chartplan.bar_width(7, song, cfg)
    typical = max(chartplan.bar_width(n, song, cfg) for n in song["bars"] if n != 7)
    if bw < typical - 0.01:
        fail("missing bar 7 is %.1f wide, squeezed under a normal bar (%.1f)" % (bw, typical))
    render("v2-report.py")
    if strs().count("missing") != 1:
        fail("the missing bar is not marked 'missing' on the chart: %r" % strs().count("missing"))
    print("1 ok")


def c2():
    render("v2-report.py")
    if len(APPROX) != 2:
        fail("expected one estimate mark for each of bars 3 and 4, saw %d" % len(APPROX))
    top = max(r[1] for r in RULES if r[3] == 0.45)
    if any(a[1] <= top for a in APPROX):
        fail("an estimate mark is not above the bar")
    render("chart-song.py")
    if APPROX:
        fail("a song with no estimates got an estimate mark")
    print("2 ok")


def c3():
    size = getattr(getattr(tpl(), "bar_numbers", None), "size", None)
    if size is None:
        fail("the template has no bar_numbers.size")
    for name in ("chart-song.py", "v2-report.py"):
        render(name)
        got = sorted(int(t[2]) for t in TXT if t[4] == size and t[3] == "F3")
        if not DRAWN or got != sorted(DRAWN):
            fail("%s: bar numbers %r do not match the bars drawn %r" % (name, got, sorted(DRAWN)))
    print("3 ok")


def c4():
    render("chart-song.py")
    want = {"0:00", "0:09", "0:28", "0:38", "0:48"}      # tempo 100, 4/4, section starts 1 5 13 17 21
    got = {s for s in strs() if re.match(r"^\d+:\d\d$", s)}
    if got != want:
        fail("section start times %r, wanted %r" % (sorted(got), sorted(want)))
    for name in ("Verse",):
        lab = next(t for t in TXT if t[2] == name)
        tm = next(t for t in TXT if t[2] == "0:09")
        if tm[1] != lab[1] or tm[0] <= lab[0]:
            fail("the time is not beside its section label")
    render("v2-sparse.py")
    if any(re.match(r"^\d+:\d\d$", s) for s in strs()):
        fail("a song with no tempo got a section time")
    print("4 ok")


def c5():
    render("chart-song.py")
    if not LINES:
        fail("no lines")
    for i, ln in enumerate(LINES):
        if ln[0]["kind"] == "ref":
            continue
        tail = ln[0]["label"] is None
        for u in ln[1:]:
            if u["kind"] == "bars" and u["label"] and tail:
                fail("line %d: section %r starts on the line holding the last bars of the previous one"
                     % (i, u["label"]))
        starts = [k for k, u in enumerate(ln) if u["kind"] == "bars" and u["label"]]
        if starts and starts[0] > 0 and i + 1 < len(LINES):
            nxt = LINES[i + 1][0]
            if nxt["kind"] == "bars" and nxt["label"] is None:
                fail("line %d: section %r starts here and wraps onto the next line" % (i, ln[starts[0]]["label"]))
    print("5 ok")


def c6():
    render("chart-song.py")
    close = [x for x, opening in REPS if not opening]
    counts = [t for t in TXT if t[2] == "x2"]
    chords = [t for t in TXT if t[3] == "F2" and t[2] in ("E", "A", "B")]
    if not counts or len(counts) != len(close):
        fail("expected one x2 for each closing repeat sign")
    for cx, cy, s, f, z in counts:
        w = chart2pdf.string_width(s, f, z)
        sign = min(close, key=lambda x: abs(x - (cx + w / 2)))
        if abs(cx + w / 2 - sign) > 3.0:
            fail("x2 is not centered over its closing repeat sign (text center %.1f, sign %.1f)"
                 % (cx + w / 2, sign))
        row = [c for c in chords if abs(c[1] - cy) < z * 1.3 and c[0] < cx + w + 6 and c[0] + 6 > cx]
        if row:
            fail("x2 shares a row and crowds a chord name: %r" % (row,))
        near = [c for c in chords if c[0] > cx and c[0] < cx + w + 4 and c[1] >= cy - z and c[1] <= cy + z]
        if near or any(c[1] >= cy for c in chords if c[0] < cx + w and c[0] + 8 > cx):
            fail("x2 is not above the chord row, beside a chord name")
    print("6 ok")


def c7():
    st = render("chart-song.py")
    if st["pages"] != 1 or st["tab_font_pt"] <= 10.0:
        fail("a one-page song kept small digits: pages=%d font=%s" % (st["pages"], st["tab_font_pt"]))
    spill = os.path.join(tempfile.mkdtemp(), "two.py")
    open(spill, "w").write(
        'META = {"title": "Two Page Fixture"}\n'
        'BARS = {n: [{"E": (n % 7, "")}] * 8 for n in range(1, 120)}\n'
        'SECTIONS = {n: {"name": "Part %d" % n, "notes": [], "same_as": None} for n in range(1, 120, 6)}\n')
    st = render(spill)
    if st["pages"] != 2 or not 9.0 <= st["tab_font_pt"] <= 10.0:
        fail("a two-page song must stay on 2 pages at 9-10 pt: %r" % st)
    print("7 ok")


def c8():
    st = render("chart-song.py")
    if st["section_refs"] < 1 or "= Chorus (bars 13-16)" not in strs():
        fail("a repeated section was not collapsed by default: refs=%d" % st["section_refs"])
    folded = len(DRAWN)
    kept = render("chart-song.py", expand=True)
    if kept["section_refs"] != 0 or len(DRAWN) <= folded:
        fail("expand did not keep the repeated section: %r, %d bars drawn vs %d" % (kept, len(DRAWN), folded))
    rc = subprocess.run([sys.executable, os.path.join(scripts, "chart2pdf.py"), os.path.join(here, "chart-song.py"),
                         "-o", os.path.join(tempfile.mkdtemp(), "e.pdf"), "--expand-sections"],
                        capture_output=True, text=True)
    if rc.returncode != 0 or "section_refs=0" not in rc.stdout:
        fail("--expand-sections did not keep the section: %r" % (rc.stdout + rc.stderr))
    print("8 ok")


def c9():
    render("v2-sparse.py")
    blob = " ".join(strs())
    if "not shown" in blob or "BPM:" in blob or "Key:" in blob or "Source report" in blob:
        fail("a song with only a title printed empty fields or an empty report: %r" % blob)
    if "Sparse Fixture" not in strs():
        fail("the title is gone")
    render(mutant("v2-report.py", '"key": "A minor", ', ""))
    blob = " ".join(strs())
    if "Key:" in blob or "BPM: 90" not in blob or "Time signature: 4/4" not in blob:
        fail("a header field with no value must be left out and the rest kept: %r" % blob)
    if "Source report" not in blob:
        fail("a report with real content was dropped")
    print("9 ok")


CASES = {str(i + 1): f for i, f in enumerate((c1, c2, c3, c4, c5, c6, c7, c8, c9))}
if len(sys.argv) != 2 or sys.argv[1] not in CASES:
    fail("usage: polish_test.py 1|2|3|4|5|6|7|8|9")
CASES[sys.argv[1]]()
