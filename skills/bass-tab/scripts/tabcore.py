"""Shared tab model: tuning, string choice, rhythm cells and repeat collapsing."""

from __future__ import annotations

STRINGS = ["G", "D", "A", "E"]
SLOT_W = 3
SLOTS = 8


# Duration codes for the rhythm row. A note lasts until the next struck slot, so
# this is DERIVED from the bars - never a second thing to keep in sync with them.
# Duration codes keyed by how many BEATS a note lasts, so the same table serves
# a bar cut into eighths and one cut into sixteenths. A song that needs 16th
# resolution says so once in META; everything else keeps the 8-slot default and
# renders byte-identically.
_DUR_BEATS = {0.25: "6", 0.5: "8", 0.75: "3", 1.0: "4", 1.5: "d",
              2.0: "2", 3.0: "D", 4.0: "1"}


def rhythm_cells(bar, slots=SLOTS):
    """One 3-char cell per slot: a duration code, '.' continuation, '-' rest.

    None is "nothing struck here": a rest, or the previous note still ringing,
    so a note lasts until the next struck slot. An empty dict {} is an EXPLICIT
    rest - nothing struck AND the previous note stops - which is the only way to
    write a quarter note followed by rests. Without it a quarter then two quarter
    rests prints as a dotted half, a wrong rhythm claim the sheet would make
    silently.
    """
    per_beat = slots / 4.0
    cells, i = [], 0
    while i < slots:
        if bar[i] is None:                       # still ringing, or a rest already placed
            cells.append("-" + "-" * (SLOT_W - 1)); i += 1; continue
        j = i + 1
        while j < slots and bar[j] is None:      # an explicit rest {} ends the note
            j += 1
        if bar[i] == {}:
            # An explicit rest prints as its OWN duration code, lower-case r
            # for a rest shorter than a beat and R for a beat or longer, so
            # the sheet draws a rest glyph where Guitar Pro draws one. Before
            # this a rest and a note ringing on were the same dash.
            code = _DUR_BEATS.get((j - i) / per_beat, "4")
            cells.append(("r" if code in "638" else "R") + "-" * (SLOT_W - 1))
        else:
            cells.append(_DUR_BEATS.get((j - i) / per_beat, "4") + "-" * (SLOT_W - 1))
        cells += ["." + "-" * (SLOT_W - 1)] * (j - i - 1)
        i = j
    return "".join(cells)


# Standard tuning, as semitone offsets from C. The note under a bar is DERIVED
# from the fretboard, so it cannot disagree with the notes printed beneath it.
_OPEN = {"E": 4, "A": 9, "D": 2, "G": 7, "B": 11}


_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


_LOW_TO_HIGH = ["E", "A", "D", "G"]


def strings_for(meta):
    """The song's rows, low to high: E A D G, or B E A D G when META["strings"] is 5."""
    n = meta.get("strings", 4)
    if n not in (4, 5):
        raise ValueError("META strings must be 4 or 5, not %r" % (n,))
    return (["B"] if n == 5 else []) + _LOW_TO_HIGH


def open_pitches(meta):
    """Each row's open-string pitch class: standard tuning unless META["open"]
    retunes a row.

    Drop D is {"E": "D"}. The bottom row keeps its place on the page and its key
    in the data, prints as "D", and sounds a whole step lower. Without this a
    drop-D song names every low-string note a whole step sharp, in the chord over
    each bar and in the key check, and nothing on the sheet would say so.

    A uniform retune (a half step down, say) needs no entry: the frets are as
    fingered and every interval is unchanged, which is how such a song is
    written. Only a tuning that changes the intervals BETWEEN strings does.
    """
    rows = strings_for(meta)
    pcs = {r: _OPEN[r] for r in rows}
    for row, note in (meta.get("open") or {}).items():
        if row not in pcs or note not in _NAMES:
            raise ValueError("META open %r: %r is not a row (%s) or %r is not a note (%s)"
                             % ({row: note}, row, "/".join(rows), note, " ".join(_NAMES)))
        pcs[row] = _NAMES.index(note)
    return pcs


def row_label(meta, row):
    """The letter a row prints under: its open note when META retunes it."""
    return (meta.get("open") or {}).get(row, row)


def string_for(fret, chord):
    """Which string carries this fret, given the chord the bar sits on.

    A fret number ALONE never fixes a note: fret 7 is B on the E string and E on
    the A string, fret 9 is C# on E and F# on A. Reading frets and guessing
    strings is therefore a coin flip that a cross-check cannot catch, because a
    mis-assigned string is mis-assigned identically in every repeat of the figure.

    The chord removes the guess. The four open strings are E A D G, whose pitch
    classes are distinct, so for a given fret there is AT MOST ONE string that
    sounds a given root - the answer is determined, not chosen. A fret and chord
    that agree on no string is a contradiction in the reading, and raises here
    rather than being silently printed on whichever line was typed.
    """
    hits = [st for st in _LOW_TO_HIGH
            if _NAMES[(_OPEN[st] + fret) % 12] == chord]
    if not hits:
        raise ValueError(
            "fret %d sounds %s on no string - chord %r is inconsistent with it "
            "(fret %d gives %s)" % (fret, chord, chord, fret,
            "/".join("%s=%s" % (st, _NAMES[(_OPEN[st] + fret) % 12])
                     for st in _LOW_TO_HIGH)))
    return hits[0]


def bar_note(bar, opens=None):
    """The lowest sounding note of the bar's first struck slot, or "".

    4-string rows only (E A D G): tabgen, its one caller, refuses a 5-string song.

    Handles what a naive slot-0 lookup cannot: a bar whose first slots are held
    over from the previous bar (common in riff-heavy songs), and a slot sounding
    more than one string (also common), where the bass note is the lowest.
    `opens` is the song's tuning (open_pitches); standard when not given.
    """
    opens = opens or _OPEN
    for slot in bar:
        if not slot:
            continue
        for st in _LOW_TO_HIGH:
            if st in slot:
                fret = slot[st][0]
                if isinstance(fret, int):
                    return _NAMES[(opens[st] + fret) % 12]
        return ""
    return ""


def collapse_runs(nums, bars, lyrics, max_period=4):
    """Runs of bars that may print as one FIGURE labelled `x N`.

    Collapsing only adjacent identical bars misses the case that matters most:
    a two-bar riff played nine times has no two ADJACENT bars equal, so nothing
    merged and the sheet printed all eighteen. A riff-based song is the proof: 151
    bars, 58 staves, not one collapsed run, for a song that is the same riff
    over and over. So a run is a repeating figure of 1..max_period bars, tried
    SHORTEST period first (a 2-bar figure stated as a 4-bar one halves the
    saving and reads as two different figures).

    A run still collapses ONLY when every row that varies per bar is constant at
    the matching position in every repeat. Six bars of one bass figure carrying
    six different lines of words are six bars: one stave has one lyric cell, and
    collapsing them would silently drop five of them. That guarantee is what
    makes the `x N` label safe to trust, so it is checked per position, not just
    per run.

    Returns [lo, hi, period] triples; the renderer prints `period` bar columns
    for each and labels the first one.
    """
    out, i, n = [], 0, len(nums)
    while i < n:
        best = (1, 1)                       # (period, repeats)
        for p in range(1, max_period + 1):
            if i + p > n:
                break
            reps = 1
            while True:
                j = i + reps * p
                if j + p > n:
                    break
                if any(bars[nums[j + k]] != bars[nums[i + k]] or
                       (lyrics.get(nums[j + k]) or "") != (lyrics.get(nums[i + k]) or "")
                       for k in range(p)):
                    break
                reps += 1
            if reps > 1 and reps * p > best[0] * best[1]:
                best = (p, reps)
        p, reps = best
        out.append([nums[i], nums[i + p * reps - 1], p])
        i += p * reps
    return out


def render_slot(slot, string_name):
    if slot is None or string_name not in slot:
        return "-" * SLOT_W
    fret, art = slot[string_name]
    body = str(fret)
    pad = SLOT_W - len(body)
    return body + art + "-" * (pad - 1) if art else body + "-" * pad


def timestamp(bar, tempo, beats=4):
    """Where this bar falls in the recording, from the tempo. Not a guess -
    arithmetic, so it stays true if the tempo is corrected."""
    if not tempo:
        return ""
    secs = (bar - 1) * beats * 60.0 / tempo
    return "%d:%02d" % (int(secs) // 60, int(secs) % 60)


def section_ranges(sections, bars):
    ks = sorted(sections)
    return {k: (k, ks[i + 1] - 1 if i + 1 < len(ks) else max(bars))
            for i, k in enumerate(ks)}
