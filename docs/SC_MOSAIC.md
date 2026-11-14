# 07_sc_mosaic — design notes

Built 2026-11-14 **without a design walk-through** (the owner: "make auto decisions"). Patch `sc/07_sc_mosaic.scd`,
tests `tools/sc_mosaic_tests.py` (NRT), `tools/sc_mosaic_files_test.py` (live file handling),
`tools/sc_osc_tests.py sc/07_sc_mosaic.scd` (live controls). Guide `docs/manual/19_sc_mosaic.md`.

## Decisions for the owner to review
| # | Decided | Alternatives |
|---|---|---|
| 1 | `Concat` (sc3-plugins) with a 10 s store fed by the corpus playing | `Concat2`; a corpus analysed once (all of a file) — needs a non-realtime analysis tool |
| 2 | Corpus = a stick file (File = next, read with `Buffer.readChannel`, wav/aif/flac), or the input's past (Source) | the right input as the corpus |
| 3 | Size = grain, Density = strictness (randscore), Start = look-back, Window = search width, Overlap = feature weights | fixed weights |
| 4 | Speed = the corpus's speed (stretch's map: centre stopped, clicks 1×) | Speed = grain rate |
| 5 | Pitch = PitchShift of the output (bypassed at the click) | pitch on the corpus (Speed already does that) |
| 6 | **The output takes the input's envelope** (input level / piece level, ≤ ×4) | raw Concat output (stays loud through the input's silences: found in the first test) |
| 7 | Freeze = freeze the store, Record = hear the corpus, Reset = file start | Record = grab the input into the corpus |
| 8 | Alt: corpus level, width (a Haas delay), reverb size/amount | — |
| 9 | Stick name `07_sc_mosaic.scd` (SC orange page, File) | — |

## Tests (2026-11-14)
| Scenario | Result |
|---|---|
| follow | output level follows the input (envelope correlation > 0.5), silent in the input's gaps |
| corpus | made of the corpus: spectral flatness 0.001 against the noise input's 0.565 |
| self | Source on: rebuilt from the input's own past (flatness 0.564) |
| pitch | +12: the output's median frequency 446 → 907 Hz (×2.03) |
| freeze | Freeze + stopped corpus: it still answers from the store |
| level | everything moving: bounded, no NaN |
| files (live) | scans the folder (the unit's 6 stick WAVs, 24-bit), File loads the next two |
| controls (live) | all 15 reach the synth |

## Hardware questions
- CPU of Concat on the Pi; how long the start takes (one file loads at start, not all).
- Is the default match (Size 0.35, Density 0.7, Overlap 0.4) musical with real material?
