# Implement the approved Bass-tab additions (prd: Bass-tab BAS-7..BAS-10, owner approved 2026-11-11: "approve"): the song header, the source report, four- and five-string bass, and one format template every song renders through, keeping the Songsterr-style layout. The repo is public: never put real song content in the skill or tests; keep every script under 20 KB.

- Slug: bass-tab-v2
- Touches: skills/bass-tab, tests, docs/wiki, .loop/regression.tsv

## Done lines

Frozen. A wrong done line needs a new goal.

1. BAS-7: every chart starts with the header fields in order, "not shown" where a source lacks one
2. BAS-8: every transcription ends with the source report (missing bars, estimates, source per section)
3. BAS-9: a 5-string song draws five labeled string lines, a 4-string song four
4. BAS-10: one template file defines the layout; changing it changes every rendered song; a missing field prints "not shown"
5. Each requirement has a regression row seen failing then passing, and BAS-1..6 stay green

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->
