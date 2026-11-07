"""Text measuring and source parsing for tab2pdf. Standard library only."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_WARNINGS: list[str] = []


def _warn(msg: str) -> None:
    if msg not in _WARNINGS:
        _WARNINGS.append(msg)


PAPERS = {"a4": (595.28, 841.89), "letter": (612.0, 792.0)}
MARGIN = 42.0            # ~15 mm
FOOTER_GAP = 24.0

# Courier's advance width is exactly 0.6 em for every glyph.
COURIER_ADVANCE = 0.6
TAB_SIZE_MAX = 12.0
TAB_SIZE_MIN = 5.0

TITLE_SIZE = 19.0
ARTIST_SIZE = 11.5
META_SIZE = 8.5
SECTION_SIZE = 11.0
NOTE_SIZE = 8.5
FOOTER_SIZE = 7.5
SECTION_BREAK_FRAC = 0.14   # start a section on a fresh page below this
# 0.42 meant a section beginning anywhere in the lower 42% of a column pushed
# the whole page turn early, so a sheet routinely ran half empty. The guard is
# worth keeping - a turn mid-phrase costs the player the phrase - but only when
# the section really would land at the very foot of the page.

# Base-14 Helvetica / Helvetica-Bold advance widths (1/1000 em) for ASCII 32..126.
# These are fixed by the PDF spec, so measuring proportional text needs no font file.
_HELV = (
    278,278,355,556,556,889,667,191,333,333,389,584,278,333,278,278,
    556,556,556,556,556,556,556,556,556,556,278,278,584,584,584,556,
    1015,667,667,722,722,667,611,778,722,278,500,667,556,833,722,778,
    667,778,722,667,611,722,667,944,667,667,611,278,278,278,469,556,
    333,556,556,500,556,556,278,556,556,222,222,500,222,833,556,556,
    556,556,333,500,278,556,500,722,500,500,500,334,260,334,584,
)
_HELVB = (
    278,333,474,556,556,889,722,238,333,333,389,584,278,333,278,278,
    556,556,556,556,556,556,556,556,556,556,333,333,584,584,584,611,
    975,722,722,722,722,667,611,778,722,278,556,722,611,833,722,778,
    667,778,722,667,611,722,667,944,667,667,611,333,278,333,584,556,
    333,556,611,556,611,556,333,611,611,278,278,556,278,889,611,611,
    611,611,389,556,333,611,556,778,556,556,500,389,280,389,584,
)


def string_width(s: str, font: str, size: float) -> float:
    """Width of `s` in points. F1 is Courier (fixed pitch); the rest are Helvetica."""
    if font == "F1":
        return len(s) * COURIER_ADVANCE * size
    table = _HELVB if font == "F2" else _HELV
    total = 0
    for ch in s:
        o = ord(ch)
        if 32 <= o <= 126:
            total += table[o - 32]
        elif o >= 0x1100:
            # CJK, kana, hangul and full-width forms are one em wide. Scoring
            # them at the 556 default made a Chinese title measure ~55% of its
            # real width, so it "fitted" and then ran off the page.
            total += 1000
        else:
            total += 556
    return total / 1000.0 * size


def fit_to_width(s: str, font: str, size: float, limit: float,
                 min_size: float = 0.0) -> tuple[str, float]:
    """Shrink `s` (never below min_size), then ellipsize, until it fits `limit`."""
    if string_width(s, font, size) <= limit:
        return s, size
    while min_size and size > min_size:
        size -= 0.5
        if string_width(s, font, size) <= limit:
            return s, size
    out = s
    while out and string_width(out + "\u2026", font, size) > limit:
        out = out[:-1]
    return (out + "\u2026") if out else "", size


def wrap_to_width(text: str, font: str, size: float, limit: float) -> list[str]:
    lines, cur = [], ""
    for wd in text.split(" "):
        # A token wider than the whole column (a pasted URL, a long tuning
        # string) can never fit by wrapping, so chop it. Without this the
        # remainder ran off the page and was silently lost.
        while string_width(wd, font, size) > limit:
            cut = len(wd)
            while cut > 1 and string_width(wd[:cut], font, size) > limit:
                cut -= 1
            if cur:
                lines.append(cur)
                cur = ""
            lines.append(wd[:cut])
            wd = wd[cut:]
        trial = f"{cur} {wd}" if cur else wd
        if cur and string_width(trial, font, size) > limit:
            lines.append(cur)
            cur = wd
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines or [""]


CJK_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
]

# ---------------------------------------------------------------- source parsing

SECTION_RE = re.compile(r"^\[(.+)\]\s*$")
META_RE = re.compile(r"^([A-Za-z][A-Za-z0-9 _-]*):\s*(.*)$")


@dataclass
class Line:
    kind: str   # "mono" | "section" | "note"
    text: str


@dataclass
class Block:
    lines: list[Line] = field(default_factory=list)


@dataclass
class Song:
    meta: dict[str, str] = field(default_factory=dict)
    blocks: list[Block] = field(default_factory=list)


def parse_source(text: str) -> Song:
    song = Song()
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    # Leading metadata: `key: value` lines before the first blank/section/stave.
    i = 0
    while i < len(lines):
        raw = lines[i]
        if not raw.strip():
            i += 1
            if song.meta:
                break
            continue
        if SECTION_RE.match(raw):
            break
        m = META_RE.match(raw)
        if not m:
            break
        song.meta[m.group(1).strip().lower()] = m.group(2).strip()
        i += 1

    current = Block()
    for raw in lines[i:]:
        stripped = raw.strip()
        sec = SECTION_RE.match(raw)
        if not stripped:
            if current.lines:
                song.blocks.append(current)
                current = Block()
            continue
        if sec:
            if current.lines:
                song.blocks.append(current)
                current = Block()
            current.lines.append(Line("section", sec.group(1).strip()))
            continue
        if stripped.startswith(">"):
            current.lines.append(Line("note", stripped[1:].strip()))
            continue
        current.lines.append(Line("mono", raw.rstrip()))
    if current.lines:
        song.blocks.append(current)
    return song
