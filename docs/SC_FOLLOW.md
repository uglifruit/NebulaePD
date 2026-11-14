# 06_sc_follow — design notes

Built 2026-11-14 **without a design walk-through** (the owner: "make auto decisions"). Patch `sc/06_sc_follow.scd`,
tests `tools/sc_follow_tests.py` (NRT) + `tools/sc_osc_tests.py sc/06_sc_follow.scd` (live controls), guide
`docs/manual/19_sc_follow.md`.

## Decisions for the owner to review
| # | Decided | Alternatives |
|---|---|---|
| 1 | Trackers: `Tartini` (sc3-plugins) for pitch, core `KeyTrack` and `BeatTrack` | `Pitch` (core, cheaper, rougher); the sc3-plugins `KeyMode` / `AutoTrack` named in SC_IDEAS |
| 2 | **Pitch = the interval in scale steps** (click = a third above; one V/oct octave = 7 steps) | Pitch = a transpose of everything; interval on a knob |
| 3 | Start = voice (FM bell / square / supersaw pad) | FM7 / physical models (heavier) |
| 4 | Density = arpeggio rate, off in its first quarter; synced to `BeatTrack`'s beat/half/quarter, or to Reset pulses while they come | free arpeggio rates |
| 5 | Overlap = 1 → 2 → 3 voices (a further third, the input an octave up) | a chord type selector |
| 6 | Speed = sub-octave right / octave up left of the clicks | Speed = arpeggio rate |
| 7 | Freeze = hold note and key (drone); Record = harmony below; Source = chromatic (parallel) | Source = the right input as a second voice to follow |
| 8 | File = arpeggio order (up, down, up-down, random) | File = a key lock |
| 9 | Alt: key-follow speed, width, input gate, detune, reverb size/amount | a fixed key on alt Start |
| 10 | One SynthDef (everything server-side), so the existing NRT and OSC tests apply | a sclang harmoniser with per-note synths |
| 11 | Stick name `06_sc_follow.scd` (SC orange page, Record) | — |

## How the harmony is found
Input pitch → midi (held while the input is below the gate or unpitched); key 0–23 from `KeyTrack` (major / minor,
held by Freeze); the note's scale degree from a 12-entry lookup (`Index` on a LocalBuf, nearest degree below for
notes outside the scale); degree + interval → midi with `DegreeToKey` in the key's scale. Chromatic: the
interval's major-scale semitones added directly.

## Tests (2026-11-14)
| Scenario | Result |
|---|---|
| third | a C major melody: 24 / 24 (the first take with a plain scale run: 21/24, the tracker heard F major) |
| octave | Pitch +1 octave: an octave and a third, 24 / 24 |
| below | Record: a third below, 22 / 24 (two Ds heard against another key) |
| chrom | Source: parallel major thirds, 24 / 24 |
| freeze | B4 held after the input stops (rms 0.160 → 0.168); without Freeze it stops |
| arp | Reset every 125 ms: one note per pulse, cycling notes |
| level | everything moving: bounded (peak 0.95, the limiter), no NaN |
| live controls | all 17 controls reach the running synth (`sc_osc_tests.py`) |

## Hardware questions
- CPU on the Pi: Tartini + two FFT trackers + three voices of three oscillators each.
- How it feels with a real voice: the latency (~70 ms), the gate default, the key settling time.
