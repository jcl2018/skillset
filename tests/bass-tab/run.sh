#!/bin/sh
# Renders the fixture song in the predefined format and checks it. Needs python3 only.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../.." && pwd)
scripts="$root/skills/bass-tab/scripts"
out=$(mktemp -d)
trap 'rm -rf "$out"' EXIT
fail() { echo "FAIL: $1" >&2; exit 1; }

# 1. Text tab: compact cut, byte-compared with the recorded baseline.
python3 "$scripts/tabgen.py" "$here/fixture-song.py" "$out/fixture.tab" --bars 3 --cut compact >/dev/null
cmp -s "$out/fixture.tab" "$here/baseline.tab" || { diff "$out/fixture.tab" "$here/baseline.tab" >&2 || true; fail "fixture.tab differs from baseline.tab"; }

# 2. The format itself: compact cut collapses repeats, rows run R then G D A E.
grep -q 'x2' "$out/fixture.tab" || fail "no collapsed repeat label (xN)"
grep -q '^R|' "$out/fixture.tab" || fail "no rhythm row"
grep -q '^\[Checked\]' "$out/fixture.tab" || fail "no Checked block"

# 3. PDF: valid header, one page, same bytes on a second run.
python3 "$scripts/tab2pdf.py" "$out/fixture.tab" -o "$out/a.pdf" >/dev/null
python3 "$scripts/tab2pdf.py" "$out/fixture.tab" -o "$out/b.pdf" >/dev/null
[ "$(head -c 5 "$out/a.pdf")" = "%PDF-" ] || fail "output is not a PDF"
cmp -s "$out/a.pdf" "$out/b.pdf" || fail "PDF is not deterministic"
[ "$(grep -ac '/Type /Page ' "$out/a.pdf")" = 1 ] || fail "expected a 1-page PDF"

# 3b. Non-Latin text: refused without Pillow (never a silent "???" title), written once Pillow is present.
{ printf "title: \346\265\213\350\257\225\n"; grep -v "^title: " "$out/fixture.tab"; } > "$out/cjk.tab"
if python3 -c 'import PIL' 2>/dev/null; then
  python3 "$scripts/tab2pdf.py" "$out/cjk.tab" -o "$out/cjk.pdf" >/dev/null 2>&1 || true
else
  if python3 "$scripts/tab2pdf.py" "$out/cjk.tab" -o "$out/cjk.pdf" >/dev/null 2>&1; then fail "lossy PDF written without --allow-lossy"; fi
  python3 "$scripts/tab2pdf.py" "$out/cjk.tab" -o "$out/cjk.pdf" --allow-lossy >/dev/null 2>&1 || fail "--allow-lossy did not write"
fi

# 3c. Compact chart: section labels, collapsed repeats, lyric alignment, the 2-page limit (invented songs).
python3 "$here/chart_test.py" || fail "chart renderer test failed"
python3 "$scripts/chart2pdf.py" "$here/chart-song.py" -o "$out/c1.pdf" >/dev/null
python3 "$scripts/chart2pdf.py" "$here/chart-song.py" -o "$out/c2.pdf" >/dev/null
cmp -s "$out/c1.pdf" "$out/c2.pdf" || fail "chart PDF is not deterministic"
if python3 "$scripts/chart2pdf.py" "$here/chart-huge.py" -o "$out/h.pdf" >/dev/null 2>&1; then fail "oversize song was not refused"; fi

# 3d. v2: header, source report, 4/5-string staves, the format template (invented songs).
for c in header report five template; do python3 "$here/v2_test.py" "$c" >/dev/null || fail "v2 $c check failed"; done

# 3e. Chart polish: the nine layout fixes and the estimate, chord and report guards, one check each (invented songs).
for c in 1 2 3 4 5 6 7 8 9 10 11 12 13; do python3 "$here/polish_test.py" "$c" >/dev/null || fail "chart polish $c check failed"; done
python3 "$here/polish_test.py" count >/dev/null || fail "polish CASES, this loop and the chart-polish regression rows disagree"

# 4. Every script stays under 20 KB.
for f in "$scripts"/*.py; do
  [ "$(wc -c < "$f")" -lt 20480 ] || fail "$f is 20 KB or more"
done

# 5. Nothing personal or tool-specific in tracked files (pattern split so this file does not match itself).
pat="chj""iang|/Us""ers/|knowledge""-base|K""B_|gst""ack|ther""mis|chang""lin"
if git -C "$root" ls-files -z | xargs -0 grep -IlEi "$pat" 2>/dev/null | grep -q .; then
  fail "a forbidden string is present in a tracked file"
fi

echo "PASS: bass-tab fixture renders in the predefined format (tab + PDF)"
