"""Invented fixture for the lyric band: placeholder Chinese text (counting words, no real song), dense bars on the
lowest string, lyrics from one short word to a line wider than any bar, an estimated bar and a repeated bar."""

META = {"title": "Lyric Fixture", "artist": "Fixture Artist", "tempo": 100, "time": "4/4"}
NUM = "一二三四五六七八九十"


def dense(a, b):
    return [{"E": (a, ""), "A": (b, "")}, {"E": (a + 1, "")}, {"E": (b, "")}, {"E": (a, "")},
            {"E": (12, "")}, {"E": (b + 10, "")}, {"E": (a, "")}, {"E": (b, "")}]


BARS = {n: dense(n % 5 + 1, n % 7 + 2) for n in range(1, 13)}
BARS[9] = BARS[10] = dense(3, 5)
BARS[10] = BARS[9]
CHORDS = {2: "Am7", 5: "Gmaj7#11/Bb", 11: "D"}
LYRICS = {1: NUM[:2], 2: NUM, 3: NUM * 3, 4: NUM[:5] + " " + NUM[5:], 6: NUM * 2, 7: NUM[:3],
          8: NUM * 7, 9: NUM[:6], 10: NUM[:6], 12: NUM * 4}
SECTIONS = {1: {"name": "Verse", "notes": [], "same_as": None}}
REPORT = {"missing": [], "estimates": [3, 6]}
