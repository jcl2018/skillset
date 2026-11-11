"""Bass-tab v2 checks on invented songs. Usage: v2_test.py header|report|five|template"""
import json
import os
import subprocess
import sys
import tempfile

here = os.path.dirname(os.path.abspath(__file__))
scripts = os.path.join(here, "..", "..", "skills", "bass-tab", "scripts")
sys.path.insert(0, scripts)
import chart2pdf  # noqa: E402

calls = []
_text, _rule = chart2pdf.PDF.text, chart2pdf.PDF.rule


def spy_text(self, x, y, s, font, size, gray=0.0):
    calls.append(("t", round(x, 2), round(y, 2), s, font, size))
    return _text(self, x, y, s, font, size, gray)


def spy_rule(self, x0, y, x1, gray=0.75):
    calls.append(("r", round(x0, 2), round(y, 2), gray))
    return _rule(self, x0, y, x1, gray)


chart2pdf.PDF.text, chart2pdf.PDF.rule = spy_text, spy_rule


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def song(name):
    return chart2pdf.read_song(os.path.join(here, name))


def render(name, template=None):
    calls.clear()
    chart2pdf.render(song(name), "letter", template=template)
    return list(calls)


def texts(cs):
    return [c[3] for c in cs if c[0] == "t"]


def first_stave(cs):
    """Rule calls of the first bar of the first system: consecutive stave lines sharing one x."""
    rows = [c for c in cs if c[0] == "r" and c[3] == 0.45]
    n = 0
    while n < len(rows) and rows[n][1] == rows[0][1]:
        n += 1
    return rows[:n]


def cli(*args):
    p = subprocess.run([sys.executable] + list(args), capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def header():
    t = texts(render("v2-sparse.py"))
    labels = ["BPM", "Key", "Time signature", "Tuning", "Instrument", "Sources"]
    stave_at = next(i for i, s in enumerate(t) if s == "Verse")
    head = [s for s in t[:stave_at]]
    if "Sparse Fixture" not in head or "not shown" not in head:
        fail("title row: title then bare 'not shown' for the artist: %r" % head)
    blob = " ".join(head)
    pos = [blob.find(l + ":") for l in labels]
    if min(pos) < 0 or pos != sorted(pos):
        fail("header labels missing or out of order: %r" % blob)
    if blob.count("not shown") != 1 + len(labels):
        fail("each missing field must read 'not shown': %r" % blob)
    full = " ".join(texts(render("v2-report.py")))
    for want in ("BPM: 90", "Key: A minor", "Instrument: 4-string bass",
                 "invented source one; invented source two"):
        if want not in full:
            fail("header lacks %r" % want)
    print("header ok")


def report():
    cs = render("v2-report.py")
    t = texts(cs)
    for want in ("Source report", "Missing bars: 7", "Estimated bars: 3, 4"):
        if not any(want in s for s in t):
            fail("report lacks %r" % want)
    last_rule = max(i for i, c in enumerate(cs) if c[0] == "r" and c[3] == 0.45)
    pos = {s: i for i, s in enumerate(texts(cs))}
    after = [c[3] for c in cs[last_rule:] if c[0] == "t"]
    if not any("Source report" in s for s in after):
        fail("the report is not after the last stave line")
    sec = [s for s in after if "Chorus" in s and "not shown" in s]
    if not sec or not any("Verse" in s and "invented source one" in s for s in after):
        fail("source per section wrong: %r" % after)
    plain = " ".join(texts(render("v2-sparse.py")))
    if plain.count("not shown") < 3 + 7:
        fail("a song with no REPORT must print 'not shown' for each part")
    bad = os.path.join(tempfile.mkdtemp(), "bad.py")
    src = open(os.path.join(here, "v2-report.py")).read().replace('{1: "invented', '{3: "invented')
    open(bad, "w").write(src)
    rc, out = cli(os.path.join(scripts, "chart2pdf.py"), bad, "-o", bad + ".pdf")
    if rc == 0 or "Report Fixture" not in out or "3" not in out:
        fail("a bad section key was not refused by name: %r" % out)
    src = open(os.path.join(here, "v2-report.py")).read().replace('"missing": [7]', '"missing": [99]')
    open(bad, "w").write(src)
    rc, out = cli(os.path.join(scripts, "chart2pdf.py"), bad, "-o", bad + ".pdf")
    if rc == 0 or "99" not in out:
        fail("an out-of-range bar was not refused: %r" % out)
    print("report ok")


def five():
    cs = render("v2-five.py")
    st = first_stave(cs)
    labels = [c[3] for c in cs if c[0] == "t" and c[3] in ("G", "D", "A", "E", "B") and c[4] == "F3"][:5]
    if len(st) != 5 or labels != ["G", "D", "A", "E", "B"]:
        fail("5-string: %d lines, labels %r" % (len(st), labels))
    cs = render("chart-song.py")
    st = first_stave(cs)
    labels = [c[3] for c in cs if c[0] == "t" and c[3] in ("G", "D", "A", "E", "B") and c[4] == "F3"][:4]
    if len(st) != 4 or labels != ["G", "D", "A", "E"]:
        fail("4-string: %d lines, labels %r" % (len(st), labels))
    rc, out = cli(os.path.join(scripts, "tabgen.py"), os.path.join(here, "v2-five.py"),
                  os.path.join(tempfile.mkdtemp(), "x.tab"))
    if rc != 2 or "5-string" not in out or "chart2pdf.py" not in out:
        fail("tabgen did not refuse a 5-string song: %r" % out)
    print("five ok")


def template():
    base = os.path.join(scripts, "..", "templates", "chart-format.json")
    t = json.load(open(base))
    d = tempfile.mkdtemp()
    p = os.path.join(d, "t.json")

    def write(obj):
        json.dump(obj, open(p, "w"))
        return p
    t2 = json.loads(json.dumps(t))
    t2["header"] = list(reversed(t2["header"]))
    t2["missing_text"] = "unknown"
    t2["section"]["repeat"] = "{n} times"
    t2["section"]["size"] = 12.0
    t2["staff"]["gap"] = 1.2
    write(t2)
    for name in ("chart-song.py", "v2-sparse.py"):
        a = render(name)
        b = render(name, template=p)
        if a == b:
            fail("%s: the changed template changed nothing" % name)
    tt = texts(render("v2-sparse.py", template=p))
    blob = " ".join(tt)
    if "unknown" not in blob or "not shown" in blob or blob.find("Sources:") > blob.find("BPM:"):
        fail("missing text or header order did not follow the template: %r" % blob)
    cs = render("chart-song.py", template=p)
    if "2 times" not in texts(cs) or not any(c[0] == "t" and c[3] == "Intro" and c[5] == 12.0 for c in cs):
        fail("repeat format or section size did not follow the template")
    if render("chart-song.py") != render("chart-song.py", template=base):
        fail("the default template differs from no --template")
    rc, out = cli(os.path.join(scripts, "chart2pdf.py"), os.path.join(here, "chart-song.py"),
                  "-o", os.path.join(d, "o.pdf"), "--template", base)
    if rc != 0:
        fail("--template with the default file failed: %r" % out)
    t3 = json.loads(json.dumps(t))
    for r in t3["ladder"]:
        r["fs"] = 8.0
    write(t3)
    rc, out = cli(os.path.join(scripts, "chart2pdf.py"), os.path.join(here, "chart-song.py"),
                  "-o", os.path.join(d, "o.pdf"), "--template", p)
    if rc == 0 or "t.json" not in out or "Traceback" in out:
        fail("a template with no rung at 9 pt was not refused by name: %r" % out)
    t4 = json.loads(json.dumps(t))
    del t4["staff"]["gap"]
    write(t4)
    rc, out = cli(os.path.join(scripts, "chart2pdf.py"), os.path.join(here, "chart-song.py"),
                  "-o", os.path.join(d, "o.pdf"), "--template", p)
    if rc == 0 or "staff.gap" not in out or "Traceback" in out:
        fail("a template missing a key was not refused naming it: %r" % out)
    rc, out = cli(os.path.join(scripts, "chart2pdf.py"), os.path.join(here, "chart-song.py"),
                  "-o", os.path.join(d, "o.pdf"), "--template", os.path.join(d, "none.json"))
    if rc == 0 or "none.json" not in out or "Traceback" in out:
        fail("a missing template file was not refused by name: %r" % out)
    print("template ok")


CASES = {"header": header, "report": report, "five": five, "template": template}
if len(sys.argv) != 2 or sys.argv[1] not in CASES:
    fail("usage: v2_test.py %s" % "|".join(CASES))
CASES[sys.argv[1]]()
