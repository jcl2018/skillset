"""Chart polish checks on invented songs. Usage: polish_test.py 1|2|...|14|count (one per layout fix;
10-12 add the estimate, chord and report guards, each proved by mutants of the production functions;
count checks that CASES, run.sh and the regression rows agree)."""
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
    missing_cost()
    print("1 ok")


def missing_cost():
    """A song with missing bars must plan in work that grows with its length, not with its square."""
    out = ['META = {"title": "Cost Fixture"}', "BARS = {}", "SECTIONS = {}"]
    for n in range(1, 121):
        if n % 12 == 1:
            out.append('SECTIONS[%d] = {"name": "P%d", "notes": [], "same_as": None}' % (n, n))
        out.append('BARS[%d] = [{"E": (%d, "")}] + [None] * 7' % (n, n % 11 + 1))
    out.append('REPORT = {"missing": %r, "estimates": %r}' % (sorted(set(range(5, 121, 6)) | set(range(100, 111))), [n for n in range(3, 121, 6) if n not in range(100, 111)]))
    p = os.path.join(tempfile.mkdtemp(), "cost.py")
    open(p, "w").write("\n".join(out) + "\n")
    calls, real = [0], chartplan.natural

    def counting(*a, **k):
        calls[0] += 1
        return real(*a, **k)
    chartplan.natural = counting
    try:
        render(p)
    finally:
        chartplan.natural = real
    if calls[0] > 120 * 120:
        fail("missing bars make planning quadratic: %d width computations for 120 bars" % calls[0])


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
    wide_time_format()
    # a tempo that is not a real beats-per-minute (at least 1) gives no time, never a traceback or a negative time
    for tempo in (0, None, "fast", -90, 1e-300, float("inf"), float("nan")):
        try:
            tm = chartplan.start_time({"meta": {"tempo": tempo}}, 5)
        except Exception as e:      # noqa: BLE001 - any crash is the failure being proved
            fail("tempo %r crashed the section time: %s" % (tempo, type(e).__name__))
        if tm != "":
            fail("tempo %r printed the time %r, wanted none" % (tempo, tm))
    if chartplan.start_time({"meta": {"tempo": 100}}, 5) != "0:09":
        fail("a valid tempo lost its time")
    print("4 ok")


def wide_time_format():
    """A template that wraps the time in words must pack by the text that is drawn, so labels stay apart."""
    import json
    t = json.load(open(chart2pdf.chartformat.DEFAULT))
    t["section"]["time"] = "Start time: {t}"
    t["ladder"] = t["ladder"][:1]      # the 12 pt rung: one-bar sections are 35 wide and share a line
    d = tempfile.mkdtemp()
    tp = os.path.join(d, "t.json")
    json.dump(t, open(tp, "w"))
    out = ['META = {"title": "Time Fixture", "tempo": 100, "time": "4/4"}', "BARS = {}", "SECTIONS = {}"]
    for n in range(1, 5):
        out.append('SECTIONS[%d] = {"name": "%s", "notes": [], "same_as": None}' % (n, "ABCD"[n - 1]))
        out.append('BARS[%d] = [{"E": (%d, "")}] + [None] * 7' % (n, n))
    sp = os.path.join(d, "s.py")
    open(sp, "w").write("\n".join(out) + "\n")
    render(sp, template=tp)
    items = [x for x in TXT if x[2] in ("A", "B", "C", "D") or x[2].startswith("Start time: ")]
    items.sort(key=lambda x: (-round(x[1]), x[0]))
    for a, b in zip(items, items[1:]):
        if abs(a[1] - b[1]) < 1 and a[0] + chart2pdf.string_width(a[2], a[3], a[4]) > b[0] + 0.01:
            fail("section text %r overlaps %r with a wide time format" % (a[2], b[2]))
    if len([x for x in items if x[2].startswith("Start time: ")]) != 4:
        fail("the time format did not apply to each section")


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
    count_over_numbers()
    print("6 ok")


def count_over_numbers():
    """A repeat on a line with no section label (a section's second line) must not land on a bar number."""
    out = ['META = {"title": "Count Fixture", "tempo": 100, "time": "4/4"}', "BARS = {}"]
    for n in range(1, 61):
        fret = 3 if 41 <= n <= 48 else n % 12 + 1
        out.append('BARS[%d] = [{"E": (%d, "")}] + [None] * 7' % (n, fret))
    out.append('SECTIONS = {1: {"name": "Long", "notes": [], "same_as": None}}')
    p = os.path.join(tempfile.mkdtemp(), "c.py")
    open(p, "w").write("\n".join(out) + "\n")
    render(p)
    size = tpl().bar_numbers.size
    counts = [t for t in TXT if re.fullmatch(r"x\d+", t[2])]
    nums = [t for t in TXT if t[3] == "F3" and t[4] == size and t[2].isdigit()]
    labels = [t for t in TXT if t[2] == "Long"]
    if not counts or not nums or any(abs(c[1] - labels[0][1]) < 5 for c in counts):
        fail("count fixture: the repeat is not on a line without a section label")
    for c in counts:
        w = chart2pdf.string_width(c[2], c[3], c[4])
        for n in nums:
            nw = chart2pdf.string_width(n[2], n[3], n[4])
            if n[0] < c[0] + w and c[0] < n[0] + nw and n[1] < c[1] + c[4] * 0.72 and c[1] < n[1] + n[4] * 0.72:
                fail("repeat count %r (%.1f, %.1f) lands on bar number %r (%.1f, %.1f)"
                     % (c[2], c[0], c[1], n[2], n[0], n[1]))


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


def expect(cond, msg):
    """A check inside a mutant run: raises, never exits, so mutate() can see it fail."""
    if not cond:
        raise AssertionError(msg)


def mutate(mod, name, repl, check, label):
    """Patch one production function, run CHECK, restore. The check must fail: a surviving mutant
    means that guard site is not proved."""
    if not hasattr(mod, name):
        fail("mutant %s: %s.%s does not exist" % (label, mod.__name__, name))
    old = getattr(mod, name)
    setattr(mod, name, repl)
    try:
        check()
    except AssertionError:
        return
    finally:
        setattr(mod, name, old)
    fail("mutant survived: %s (%s.%s)" % (label, mod.__name__, name))


def bar_units():
    return [u for ln in LINES for u in ln if u["kind"] == "bars"]


def unit_of(num):
    return next(u for u in bar_units() if num in u["bars"])


def est_bars():
    """Estimated bars equal to a neighbour: all drawn, one sign each, repeats split around them."""
    render("polish-est.py")
    est = [3, 6, 14]
    expect(all(n in DRAWN for n in est), "an estimated bar was folded away: drawn %r" % sorted(DRAWN))
    expect(len(APPROX) == len(est), "expected %d estimate signs, saw %d" % (len(est), len(APPROX)))
    expect(all(unit_of(n)["reps"] == 1 for n in est), "an estimated bar sits inside a repeat")
    runs = {(u["bars"][0], len(u["bars"]), u["reps"]) for u in bar_units() if u["reps"] > 1}
    expect({(1, 1, 2), (4, 1, 2), (7, 1, 2), (9, 2, 2)} <= runs,
           "bars around an estimate no longer repeat on their own: %r" % sorted(runs))
    chords = [t for t in TXT if t[3] == "F2" and t[4] == tpl().chords.size]
    for cx, cy, w in APPROX:
        left = cx - w / 2.0
        same = [t for t in chords if t[0] <= cx and abs(t[1] - cy) < 3]
        expect(same, "no chord name on the estimated bar's row")
        c = max(same, key=lambda t: t[0])
        edge = c[0] + chart2pdf.string_width(c[2], c[3], c[4])
        expect(left > edge + 0.5, "the estimate sign (left %.1f) meets the chord name (right %.1f)" % (left, edge))


def est_sections():
    """A section holding an estimate is never a reference nor a reference target (both directions)."""
    st = render("polish-sec.py")
    expect(st["section_refs"] == 1, "expected only section C to collapse, section_refs=%d" % st["section_refs"])
    expect(sorted(DRAWN) == list(range(1, 21)), "bars drawn %r, wanted 1-20" % sorted(DRAWN))
    expect(len(APPROX) == 2, "expected 2 estimate signs, saw %d" % len(APPROX))
    expect("= C (bars 17-20)" in strs(), "section C did not fold to a reference (positive control)")


def temp_song(title, nsec, per, every):
    """nsec sections of per bars; every Nth bar estimated (0: none)."""
    out = ['META = {"title": "%s"}' % title, "BARS = {}", "SECTIONS = {}"]
    b, est = 1, []
    for s in range(nsec):
        out.append('SECTIONS[%d] = {"name": "Part %d", "notes": [], "same_as": None}' % (b, s))
        for k in range(per):
            out.append('BARS[%d] = [{"E": (%d, "")}] + [None] * 7' % (b, s % 7 + 1))
            if every and k % every == 0:
                est.append(b)
            b += 1
    out.append('REPORT = {"missing": [], "estimates": %r}' % est)
    p = os.path.join(tempfile.mkdtemp(), "t.py")
    open(p, "w").write("\n".join(out) + "\n")
    return p


def est_pages():
    plain = render(temp_song("Twin Fixture", 12, 12, 0))
    drawn_plain = len(DRAWN)
    heavy = render(temp_song("Heavy Fixture", 12, 12, 3))
    expect(heavy["pages"] <= 2 and heavy["tab_font_pt"] >= 9.0, "estimate-heavy song left the limits: %r" % heavy)
    expect(len(DRAWN) > drawn_plain, "estimates did not add drawn bars: %d vs %d" % (len(DRAWN), drawn_plain))
    expect(plain["pages"] <= heavy["pages"], "the twin is longer than the heavy song")
    try:
        render(temp_song("Overlong Fixture", 20, 20, 1))
    except SystemExit as e:
        expect("Overlong Fixture does not fit 2 pages at 9 pt" in str(e), "refusal line changed: %s" % e)
        return
    expect(False, "an estimate-only song too long for 2 pages was not refused")


def c10():
    est_bars()
    est_sections()
    est_pages()
    never = lambda *a: True       # a guard that lets everything fold
    mutate(chartplan, "base_ok", never, est_bars, "an estimated bar may start a repeat")
    mutate(chartplan, "rep_ok", never, est_bars, "an estimated bar may be a repeated copy")
    mutate(chartplan, "unfoldable", chartplan.missing, est_bars, "estimates left out of the never-fold set")
    mutate(chartplan, "sign_room", lambda *a: 0.0, est_bars, "no room kept for the estimate sign")
    mutate(chartplan, "sec_target_ok", never, est_sections, "an estimated section may be a reference target")
    mutate(chartplan, "sec_new_ok", never, est_sections, "an estimated section may collapse to a reference")
    print("10 ok")


def chord_fold():
    render("polish-chord.py")
    chords = sorted(t[2] for t in TXT if t[3] == "F2" and t[4] == tpl().chords.size and not re.match(r"x\d", t[2]))
    expect(chords == ["A", "D", "E", "G"], "a chord name was lost: printed %r" % chords)
    runs = {(u["bars"][0], u["reps"]) for u in bar_units() if u["reps"] > 1}
    expect((1, 2) in runs and (3, 2) in runs and (1, 4) not in runs,
           "bars 1-4 should fold in two runs split at the chord change, got %r" % sorted(runs))
    expect(sorted(DRAWN) == [1, 3] + list(range(5, 13)), "bars drawn %r" % sorted(DRAWN))
    expect(len([ln for ln in LINES if ln[0]["kind"] == "ref"]) == 1, "expected exactly one section reference")
    expect("= Three (bars 9-12)" in strs(), "section Four should fold into Three (chord G in force)")
    expect("= Two (bars 5-8)" not in strs(), "section Three folded into Two across a chord change")


def c11():
    chord_fold()
    never = lambda *a: True
    mutate(chartplan, "fig_chords_agree", never, chord_fold, "a repeat may cross a chord change")
    mutate(chartplan, "sec_chords_agree", never, chord_fold, "a section reference may cross a chord change")

    def literal(song):
        return {n: song["chords"].get(n) or "" for n in song["bars"]}

    real = chartplan.Fold

    def literal_fold(song):
        f = real.__new__(real)
        f.unf, f.eff = chartplan.unfoldable(song), literal(song)
        return f
    mutate(chartplan, "Fold", literal_fold, chord_fold, "the chord in force is not carried forward")
    print("11 ok")


def report_cases():
    t = tpl()
    secs = {1: {"name": "Verse"}, 5: {"name": "Chorus"}}
    ranges = {1: (1, 4), 5: (5, 8)}

    def lines(rep, key=True):
        song = {"sections": secs}
        if key:
            song["report"] = rep
        try:
            return [x[0] for x in chart2pdf.chartformat.report_lines(song, ranges, t)]
        except Exception as e:                                  # a crash is a failed check, not a pass
            raise AssertionError("report_lines raised %r for %r" % (e, rep))
    hidden = [("no report key", None, False), ("None", None, True), ("empty map", {}, True),
              ("empty sections map", {"sections": {}}, True), ("None lists", {"missing": None, "estimates": None}, True),
              ("empty and None source values", {"sections": {1: "", 5: None}}, True)]
    for name, rep, key in hidden:
        expect(lines(rep, key) == [], "%s must leave the report out: %r" % (name, lines(rep, key)))
    kept = [("empty missing list", {"missing": []}, "Missing bars: none"),
            ("empty estimates list", {"estimates": [], "sections": {}}, "Estimated bars: none"),
            ("both empty", {"missing": [], "estimates": []}, "Missing bars: none"),
            ("a missing bar", {"missing": [7], "sections": {}}, "Missing bars: 7"),
            ("sources only", {"sections": {1: "invented source"}}, "Verse (bars 1-4): invented source"),
            ("empty list and empty sources", {"estimates": [], "sections": {1: ""}}, "Estimated bars: none")]
    for name, rep, want in kept:
        got = lines(rep)
        expect(got and got[0] == t.report.heading and want in got, "%s must stay visible with %r: %r" % (name, want, got))
    expect("Estimated bars: not shown" in lines({"missing": []}), "an unset part must read not shown beside a set one")


def report_render():
    song = os.path.join(tempfile.mkdtemp(), "r.py")
    body = 'META = {"title": "Report Edge Fixture"}\nBARS = {1: [{"E": (1, "")}] + [None] * 7}\n' \
           'SECTIONS = {1: {"name": "A", "notes": [], "same_as": None}}\n'
    open(song, "w").write(body + 'REPORT = {"missing": [], "estimates": []}\n')
    render(song)
    expect("Missing bars: none" in strs() and "Estimated bars: none" in strs(), "explicit none lines were dropped")
    open(song, "w").write(body + "REPORT = {}\n")
    render(song)
    expect("Source report" not in strs(), "an empty report was printed")


def c12():
    report_cases()
    report_render()
    mutate(chart2pdf.chartformat, "report_hidden", lambda *a: False, report_cases, "an empty report is printed")
    mutate(chart2pdf.chartformat, "report_hidden",
           lambda rep, parts: all(not rep.get(k) for k in ("missing", "estimates", "sections")),
           report_cases, "an explicit none list is dropped")
    mutate(chart2pdf.chartformat, "report_hidden",
           lambda rep, parts: all(rep.get(k) is None for k in ("missing", "estimates")),
           report_cases, "a sources-only report is dropped")
    print("12 ok")


def count_boxes():
    """Every repeat count must keep clear of every section label and start time on its row."""
    t = tpl()
    for name in ("polish-est.py", "chart-song.py"):
        render(name)
        counts = [x for x in TXT if re.fullmatch(r"x\d+", x[2])]
        expect(counts, "%s: no repeat count drawn" % name)
        names = [x for x in TXT if (x[3] == "F2" and x[4] == t.section.size and not re.fullmatch(r"x\d+", x[2]))
                 or (x[3] == "F3" and x[4] == t.section.time_size and re.fullmatch(r"\d+:\d\d", x[2]))]
        for c in counts:
            c0, c1 = c[0], c[0] + chart2pdf.string_width(c[2], c[3], c[4])
            for n in names:
                if abs(n[1] - c[1]) >= 8:
                    continue
                n1 = n[0] + chart2pdf.string_width(n[2], n[3], n[4])
                expect(c1 <= n[0] or c0 >= n1, "%s: repeat count %r (%.1f-%.1f) overlaps %r (%.1f-%.1f)"
                       % (name, c[2], c0, c1, n[2], n[0], n1))


def count_stack():
    """Counts pushed past one long label must not land on each other."""
    out = ['META = {"title": "Stack Fixture", "tempo": 100, "time": "4/4"}', "BARS = {}"]
    for n in range(1, 73):
        out.append('BARS[%d] = [{"E": (%d, "")}] + [None] * 7' % (n, (n - 1) // 12 % 2 + 1))
    out.append('SECTIONS = {1: {"name": "Verse with a pretty long label name here", "notes": [], "same_as": None}}')
    p = os.path.join(tempfile.mkdtemp(), "s.py")
    open(p, "w").write("\n".join(out) + "\n")
    render(p)
    counts = [x for x in TXT if re.fullmatch(r"x\d+", x[2])]
    expect(len(counts) > 2, "stack fixture: expected several repeat counts, got %d" % len(counts))
    for i, a in enumerate(counts):
        for b in counts[i + 1:]:
            if abs(a[1] - b[1]) < 8:
                a1, b1 = a[0] + chart2pdf.string_width(a[2], a[3], a[4]), b[0] + chart2pdf.string_width(b[2], b[3], b[4])
                expect(a1 <= b[0] or b1 <= a[0], "repeat counts %r and %r overlap (%.1f-%.1f, %.1f-%.1f)"
                       % (a[2], b[2], a[0], a1, b[0], b1))


def c13():
    count_boxes()
    count_stack()
    mutate(chart2pdf, "count_x", lambda cx, w, boxes, gap: cx - w / 2.0, count_boxes,
           "a repeat count ignores the section label")
    print("13 ok")


def run_template(text):
    """A copy of the default template with marks.missing_run set to TEXT (None removes the key)."""
    import json
    raw = json.load(open(chart2pdf.chartformat.DEFAULT, encoding="utf-8"))
    if text is None:
        raw["marks"].pop("missing_run", None)
    else:
        raw["marks"]["missing_run"] = text
    p = os.path.join(tempfile.mkdtemp(), "t.json")
    json.dump(raw, open(p, "w"))
    return p


def run_lines():
    """Bar ranges per line of polish-run.py, a gap as ('gap', a, b)."""
    return [[("gap", u["bars"][0], u["bars"][-1]) if u["kind"] == "gap" else (u["bars"][0], u["bars"][-1])
             for u in ln] for ln in LINES]


def run_fixture():
    st = render("polish-run.py")
    s, t = strs(), tpl()
    for want in ("bars 9-38 missing", "bars 49-50 missing", "bars 51-52 missing"):
        expect(s.count(want) == 1, "%r printed %d times" % (want, s.count(want)))
    expect(s.count(t.marks.missing) == 4, "expected 4 per-bar missing marks (bars 5, 45, 46, 47), saw %d"
           % s.count(t.marks.missing))
    nums = [x[2] for x in TXT if x[3] == "F3" and x[4] == t.bar_numbers.size]
    expect(not any(str(n) in nums for n in range(10, 39)), "a bar number inside the run 9-38 is printed")
    expect("Am" in s and "la" in s, "the chord on bar 47 or the lyric on bar 45 is not printed")
    gaps = {u["bars"][0]: u for ln in LINES for u in ln if u["kind"] == "gap"}
    expect(sorted(gaps) == [9, 49, 51], "gap runs are %r, not [9, 49, 51]" % sorted(gaps))
    expect(gaps[9]["label"] == "B" and gaps[9]["time"], "the run 9-38 lost its section label or time")
    expect(gaps[51]["label"] == "D" and gaps[49]["label"] is None, "a run's label is not the section's own")
    for ln in LINES:       # c5's rule: no section starts on the line holding another's last bars
        tail = ln[0]["label"] is None
        expect(not any(u["label"] for u in ln[1:] if tail), "a section starts beside the previous one's tail: %r" % run_lines())
    for ln in LINES:
        expect(not any(u["kind"] == "gap" for u in ln) or len(ln) == 1, "a gap shares its line")
    expect(st["lines"] == len(LINES) == 7, "lines=%d: %r" % (st["lines"], run_lines()))
    song = chart2pdf.read_song(os.path.join(here, "polish-run.py"))
    cfg = chart2pdf.ladder(tpl())[0]
    wide = max(chartplan.bar_width(n, song, cfg) for n in song["bars"] if n not in chartplan.missing(song))
    expect(chartplan.bar_width(5, song, cfg) >= wide - 0.01, "the lone missing bar 5 is narrower than a real bar")


def run_single():
    """One missing bar: the same PDF bytes as before this change, and one per-bar mark."""
    import hashlib
    data, _ = chart2pdf.render(chart2pdf.read_song(os.path.join(here, "v2-report.py")), "letter")
    want = open(os.path.join(here, "missing-one.sha256")).read().strip()
    expect(hashlib.sha256(data).hexdigest() == want, "a single missing bar's chart changed")
    render("v2-report.py")
    expect(strs().count(tpl().marks.missing) == 1 and not any("bars" in x and "missing" in x for x in strs()),
           "a lone missing bar is not one per-bar mark")


def run_template_checks():
    for bad in ("{c}", "{a:>3}", "{a.x}"):
        try:
            chart2pdf.chartformat.load(run_template(bad))
        except SystemExit as e:
            expect("marks.missing_run" in str(e), "bad wording %r refused without naming the key: %s" % (bad, e))
            continue
        expect(False, "wording %r was accepted" % bad)
    try:
        chart2pdf.chartformat.load(run_template(None))
    except SystemExit as e:
        expect("marks.missing_run" in str(e) and "bars {a}-{b} missing" in str(e),
               "the missing-key refusal gives no line to add: %s" % e)
    else:
        expect(False, "a template without marks.missing_run was accepted")
    render("polish-run.py", template=run_template("gap {a} to {b}"))
    expect("gap 9 to 38" in strs(), "the template's wording is not what the chart prints")
    render("polish-run.py", template=run_template("x" * 400 + " {a}-{b}"))
    usable = chart2pdf.PAPERS["letter"][0] - 2 * chart2pdf.MARGIN
    long_ = [t for t in TXT if t[2].startswith("xxx")]
    expect(long_ and all(t[0] + chart2pdf.string_width(t[2], t[3], t[4]) <= usable + chart2pdf.MARGIN for t in long_),
           "a long wording runs off the stave")


def run_notes():
    song = chart2pdf.read_song(os.path.join(here, "polish-run.py"))
    song["bars"][12] = [{"E": (3, "")}] + [None] * 7      # a "missing" bar that holds notes stays a bar
    cfg = chart2pdf.ladder(tpl())[0]
    runs = chartplan.missing_runs(song, 9, 40, chartplan.missing(song))
    expect(runs == [(9, 11), (13, 38)], "a bar with notes was swallowed into a run: %r" % runs)


def c14():
    run_fixture()
    run_single()
    run_template_checks()
    run_notes()
    missing_cost()
    mutate(chartplan, "missing_runs", lambda *a, **k: [], run_fixture, "no run is ever found")
    mutate(chartplan, "plain", lambda *a, **k: True, lambda: (run_fixture(), run_notes()),
           "a bar with a chord, lyric or notes joins a run")
    mutate(chartplan, "continues", lambda g: False, run_fixture, "the tail flag is lost after a gap")
    print("14 ok")


def counts(cases, run_sh, tsv):
    """The numbers 1..N that CASES, the run.sh loop and the chart-polish rows each name."""
    loop = re.search(r"for c in ([0-9 ]+); do python3 .*polish_test\.py", run_sh)
    rows = {m.group(1) for m in re.finditer(r"^chart-polish-(\d+)\t\S+\tpython3 tests/bass-tab/polish_test\.py (\d+)\t",
                                            tsv, re.M) if m.group(1) == m.group(2)}
    return sorted(int(c) for c in cases), sorted(int(c) for c in (loop.group(1).split() if loop else [])), \
        sorted(int(r) for r in rows)


def c_count():
    a, b, c = counts(CASES, open(os.path.join(here, "run.sh")).read(),
                     open(os.path.join(here, "..", "..", ".loop", "regression.tsv")).read())
    if not (a == b == c and a == list(range(1, len(a) + 1))):
        fail("CASES %r, run.sh %r and regression rows %r disagree" % (a, b, c))
    # negative controls: a dropped run.sh case, a dropped row and a stray CASES entry are each seen
    sh = "for c in 1 2 3; do python3 \"$here/polish_test.py\" \"$c\"; done"
    row = "chart-polish-%d\tland\tpython3 tests/bass-tab/polish_test.py %d\tx\n"
    tsv = row % (1, 1) + row % (2, 2) + row % (3, 3)
    if len({tuple(x) for x in counts({"1": 0, "2": 0, "3": 0}, sh, tsv)}) != 1:
        fail("count check rejects matching inputs")
    for bad in (counts({"1": 0, "2": 0, "3": 0}, sh.replace("2 ", ""), tsv),
                counts({"1": 0, "2": 0, "3": 0}, sh, row % (1, 1) + row % (3, 3)),
                counts({"1": 0, "2": 0, "3": 0, "4": 0}, sh, tsv)):
        if len({tuple(x) for x in bad}) == 1:
            fail("count check missed a mismatch")
    print("count ok (%d cases)" % len(a))


CASES = {str(i + 1): f for i, f in enumerate((c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12, c13, c14))}
if len(sys.argv) != 2 or sys.argv[1] not in list(CASES) + ["count"]:
    fail("usage: polish_test.py 1|2|3|4|5|6|7|8|9|10|11|12|13|14|count")
try:
    c_count() if sys.argv[1] == "count" else CASES[sys.argv[1]]()
except AssertionError as e:
    fail(str(e))
