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
