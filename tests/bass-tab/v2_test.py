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


def render(name, template=None):
    return render_path(os.path.join(here, name), template)


def render_path(path, template=None):
    calls.clear()
    chart2pdf.render(chart2pdf.read_song(path), "letter", template=template)
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


def mutant(name, old, new, extra=""):
    """A throwaway copy of fixture NAME with OLD replaced by NEW (OLD must occur)."""
    src = open(os.path.join(here, name)).read()
    if old not in src:
        fail("mutant: %r not in %s" % (old, name))
    p = os.path.join(tempfile.mkdtemp(), "m.py")
    open(p, "w").write(src.replace(old, new) + extra)
    return p


def refused(script, song, want, *more):
    """The CLI exits non-zero with WANT in its output and no traceback."""
    out_arg = [] if script == "tabgen.py" else ["-o"]
    dest = os.path.join(tempfile.mkdtemp(), "out")
    rc, out = cli(os.path.join(scripts, script), song, *(out_arg + [dest] + list(more)))
    if rc == 0 or want not in out or "Traceback" in out:
        fail("%s did not refuse with %r: rc=%d %r" % (script, want, rc, out))


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
    if rc == 0 or "Report Fixture" not in out or "section start bar" not in out:
        fail("a bad section key was not refused by name: %r" % out)
    src = open(os.path.join(here, "v2-report.py")).read().replace('"missing": [7]', '"missing": [99]')
    open(bad, "w").write(src)
    rc, out = cli(os.path.join(scripts, "chart2pdf.py"), bad, "-o", bad + ".pdf")
    if rc == 0 or "99" not in out:
        fail("an out-of-range bar was not refused: %r" % out)
    refused("chart2pdf.py", mutant("v2-report.py", '"missing": [7]', '"misses": [7]'), "REPORT keys")
    refused("chart2pdf.py", mutant("v2-report.py", '"missing": [7]', '"missing": 7'), "list of bar numbers")
    refused("chart2pdf.py", mutant("v2-report.py", '"missing": [7]', '"missing": "7, 8"'), "list of bar numbers")
    refused("chart2pdf.py", mutant("v2-report.py", '"sections": {1: "invented source one"}',
                                   '"sections": [1]'), "REPORT sections")
    one = mutant("v2-report.py", '["invented source one", "invented source two"]', '"one source"')
    if "Sources: one source" not in " ".join(texts(render_path(one))):
        fail("a plain-string sources must print as one source")
    rc, out = cli(os.path.join(scripts, "tabgen.py"),
                  mutant("v2-report.py", '["invented source one", "invented source two"]', '[1, 2]'),
                  os.path.join(tempfile.mkdtemp(), "x.tab"))
    if rc != 0 or "Traceback" in out:
        fail("tabgen must print non-text sources, not crash: %r" % out)
    many = os.path.join(tempfile.mkdtemp(), "many.py")
    open(many, "w").write(
        'META = {"title": "Many Sections Fixture"}\n'
        'BARS = {n: [{"E": (0, "")}] * 8 for n in range(1, 91)}\n'
        'SECTIONS = {n: {"name": "Part %d" % n, "notes": [], "same_as": None} for n in range(1, 91)}\n'
        'REPORT = {"missing": [], "estimates": [], "sections": {n: "invented source" for n in range(1, 91)}}\n')
    refused("chart2pdf.py", many, "source report and caveats")
    refused("chart2pdf.py", mutant("v2-report.py", '"missing": [7]', '"missing": [7, 7]'), "more than once")
    refused("chart2pdf.py", mutant("v2-report.py", '"estimates": [3, 4]', '"estimates": [3, 7]'), "more than once")
    tab = os.path.join(tempfile.mkdtemp(), "one.tab")
    rc, out = cli(os.path.join(scripts, "tabgen.py"), one, tab)
    if rc != 0 or "source: one source" not in open(tab).read():
        fail("tabgen must print a plain-string sources as one source: %r" % out)
    refused("chart2pdf.py", mutant("v2-sparse.py", "BARS = {n: [{\"E\": (0, \"\")}] * 8 for n in range(1, 5)}",
                                   "BARS = {}"), "BARS")
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
    refused("chart2pdf.py", mutant("v2-five.py", '"strings": 5,', '"strings": 4,'), "lacks")
    refused("chart2pdf.py", mutant("v2-five.py", '"strings": 5,', '"strings": 6,'), "4 or 5")
    both = mutant("v2-report.py", '"sources":', '"source": "x", "sources":')
    refused("chart2pdf.py", both, "keep one")
    refused("tabgen.py", both, "keep one")
    for n in ('"5"', "7"):
        bad_n = mutant("v2-five.py", '"strings": 5,', '"strings": %s,' % n)
        refused("tabgen.py", bad_n, "4 or 5")
        refused("chart2pdf.py", bad_n, "4 or 5")
    refused("chart2pdf.py", mutant("chart-song.py", "META = {", 'META = {"open": {"E": "Eb"}, '), "is not a note")
    refused("chart2pdf.py", mutant("chart-song.py", "META = {", 'META = {"open": {"Q": "D"}, '), "is not a row")
    refused("chart2pdf.py", mutant("chart-song.py", "META = {", 'META = {"open": {"B": "A"}, '), "4-string")
    sharp = mutant("chart-song.py", "META = {", 'META = {"open": {"G": "G#"}, ', )
    cs = render_path(sharp)
    stave_x = min(c[1] for c in cs if c[0] == "r" and c[3] == 0.45)
    lab = next(c for c in cs if c[0] == "t" and c[3] == "G#")
    if lab[1] + chart2pdf.string_width("G#", "F3", lab[5]) > stave_x:
        fail("a two-letter string label runs into the stave")
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
    song_path = os.path.join(here, "chart-song.py")
    open(p, "w").write("{not json")
    refused("chart2pdf.py", song_path, "not valid JSON", "--template", p)
    for change, want in ((lambda x: x["section"].__setitem__("repeat", "{m}"), "bad value"),
                         (lambda x: x["report"]["parts"][0].__setitem__("key", "other"), "report parts"),
                         (lambda x: x["staff"].__setitem__("gap", "wide"), "bad value"),
                         (lambda x: x.__setitem__("header_size", 0), "bad value"),
                         (lambda x: x["section"].__setitem__("size", -1), "bad value"),
                         (lambda x: x["lyrics"].__setitem__("size", True), "bad value"),
                         (lambda x: x["title_row"].__setitem__("left", 5), "bad value"),
                         (lambda x: x.__setitem__("missing_text", None), "bad value"),
                         (lambda x: x["ladder"][0].__setitem__("secref", "false"), "bad value"),
                         (lambda x: x["ladder"][0].__setitem__("pad", -3), "bad value"),
                         (lambda x: x["ladder"][0].__setitem__("maxp", 0), "bad value"),
                         (lambda x: x["ladder"][0].__setitem__("maxp", 4.7), "bad value"),
                         (lambda x: x["staff"].__setitem__("gap", float("nan")), "bad value"),
                         (lambda x: x["ladder"][0].__setitem__("fs", float("inf")), "bad value"),
                         (lambda x: x["header"][0].__setitem__("field", ["tempo"]), "bad value"),
                         (lambda x: x["header"][0].__setitem__("label", 5), "bad value"),
                         (lambda x: x["report"].__setitem__("heading", 5), "bad value"),
                         (lambda x: x["report"].__setitem__("none_text", None), "bad value"),
                         (lambda x: x["report"]["parts"][0].__setitem__("label", 5), "bad value"),
                         (lambda x: x["section"].__setitem__("repeat", "x{n:>9}"), "bad value"),
                         (lambda x: x["section"].__setitem__("ref", "= {other.__class__}"), "bad value")):
        tb = json.loads(json.dumps(t))
        change(tb)
        write(tb)
        refused("chart2pdf.py", song_path, "t.json", "--template", p)
        refused("chart2pdf.py", song_path, want, "--template", p)
    t5 = json.loads(json.dumps(t))
    for r in t5["ladder"]:
        r["secref"] = False
    write(t5)
    refused("chart2pdf.py", song_path, "t.json", "--template", p, "--collapse-sections")
    g = json.loads(json.dumps(t))
    g["staff"]["gap"] = 2.1
    write(g)
    d0, d1 = first_stave(render("chart-song.py")), first_stave(render("chart-song.py", template=p))
    if abs((d1[0][2] - d1[1][2]) / (d0[0][2] - d0[1][2]) - 2.0) > 0.01:
        fail("staff.gap did not set the line gap")
    g["staff"]["gap"], g["staff"]["clef"] = 1.05, False
    write(g)
    if any(c[0] == "t" and c[3] in "TAB" and c[4] == "F2" and c[1] == round(chart2pdf.MARGIN + 1.5, 2)
           for c in render("chart-song.py", template=p)):
        fail("staff.clef false still drew the clef")
    asc = json.loads(json.dumps(t))
    asc["ladder"] = [r for r in t["ladder"] if r["fs"] < 10] + [r for r in t["ladder"] if r["fs"] >= 10]
    write(asc)
    if render("chart-song.py", template=p) != render("chart-song.py"):
        fail("a template listing rungs smallest-first changed the fitting order")
    t6 = json.loads(json.dumps(t))
    t6["title_row"]["size"], t6["header_size"] = 40.0, 30.0
    write(t6)
    cs = render("v2-sparse.py", template=p)
    title = next(c for c in cs if c[0] == "t" and c[3] == "Sparse Fixture")
    head = [c for c in cs if c[0] == "t" and c[5] == 30.0]
    rule = next(c for c in cs if c[0] == "r" and c[1] == round(chart2pdf.MARGIN, 2) and c[3] == 0.75)
    stave_top = max(c[2] for c in cs if c[0] == "r" and c[3] == 0.45)
    if not head or title[2] - head[0][2] < 30.0 or rule[2] < stave_top:
        fail("a large title or header overlaps: title y %s, header y %s, rule y %s, stave top %s"
             % (title[2], head and head[0][2], rule[2], stave_top))
    print("template ok")


CASES = {"header": header, "report": report, "five": five, "template": template}
if len(sys.argv) != 2 or sys.argv[1] not in CASES:
    fail("usage: v2_test.py %s" % "|".join(CASES))
CASES[sys.argv[1]]()
