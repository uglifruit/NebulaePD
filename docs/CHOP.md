# 09_chop — design notes

Slice sequencer, designed with the owner on 2026-11-14 (walk-through: source → sequencer → panel → buttons → alt
layer → summary, all recommended options picked, plus "free-run at the last tempo" when there's no clock).
Builder `tools/chop.py`, tests `tools/chop_tests.py`, guide `patches/09_chop_README.md` (also the manual section
`docs/manual/12_chop.md`).

## The agreed design
- **Source:** both. Record grabs clocked bars (1/2/4, alt Start) starting at the next bar line; File loads the
  next stick WAV; File held = back to the last grab. Whatever arrived last plays.
- **Slicing:** onsets, with an equal-16ths fallback (fewer than 2 onsets per bar), and alt Size from "grid" to
  "very sensitive".
- **Clock:** Reset = a beat, 16th steps inside; tap tempo; free-run at 120 BPM from load / the last tempo after
  the clock stops; a gap > 2 s (or 1.5 beats) = the next pulse is step 1.
- **Pattern:** as long as the loop; the hits stay on the loop's slice starts ("keep rhythm, swap hits").
- **Panel (layout A):** Start shuffle, Size gate, Density hits, Overlap ratchet, Window reverse, Blend mix,
  Pitch transpose, Speed pitch jumps (off between the clicks).
- **Buttons (layout A):** Reset clock, Record grab, Freeze hold dice (knobs still morph), File next / held = grab,
  Source = step 1.
- **Alt (map A):** grab bars, slicing, swing, ratchet range, edges, stutter; Source + Record = alt reset.

## Decisions taken while building (not in the walk-through)
| Decision | Why |
|---|---|
| Our own onset detector, not `bonk~` | `bonk~` reports onsets through a clock, so it can't analyse a stored file faster than real time (a `[switch~]` bang runs many blocks in one logical instant and only the last clock fires). It ships on the unit (checked in the SD image), but files need offline analysis, and one detector for grabs and files keeps the sensitivity the same for both |
| Onsets refined to the sample | The block-level detector is 64-sample coarse. Refining (first sample above 20 % of the local peak) let the pre-roll shrink from 3 to 1.5 ms, so a hit sounds ~1.5 ms after its step instead of ~4 ms |
| Slices start at the onset, triggered on the step | The loop's hits get quantised to the clock (tight); a grab at Shuffle 0 is still a seamless replay because each slice runs up to the next |
| A slice stops at its own end | A swapped short slice leaves a gap instead of running into the next hit's attack |
| A dropped hit (Density) chokes the playing slice | Otherwise a swapped long slice would ring through the gap |
| Last ratchet repeat plays on | The roll resolves into the hit instead of leaving a hole |
| Ratchet counts {2}, {2,3}, {2,3,4}, {2,3,4,6} | "up to 4× + triplets" from the walk-through |
| Pitch rounds to semitones | As glitch; the encoder and CV noise don't detune |
| Pitch jumps +5/+7/+12 up, −12/−24 down | As agreed ("tape drop" down) |
| Swing up to half a 16th (≈ 75 % MPC swing) | "heavy" at full |
| Edges: fade in and out = alt Window (1–20 ms, default 1.5 ms) | Fade-in starts at the slice start (1.5 ms before the onset), so the default leaves the attack untouched |
| No auto-load of a file at start-up | Switching to chop with Blend up shouldn't start a loop by itself |
| Record during a grab is ignored; Source/restart during a grab restarts it at the new step 1 | Keeps "bars" exact |
| File press while a file waits for its bar line replaces it | The waiting file's slot gets overwritten, so its pending switch is cancelled |
| Long files (> 6 bars at the current tempo) → their first 4 bars | Better than squeezing 20 bars into 64 steps |
| Clock: a pulse arriving ≤ 12 ms (+ the last tempo change) after the predicted beat is still "the beat" | Jitter (1–3 ms on the module) and tempo ramps never make a beat early or doubled; the cost is one beat up to 12 ms late when the clock stops |

## Engine
- **Slots:** 4 stereo tables of 2^21 + 8 samples (43.7 s): 0/1 grabs, 2/3 files, so loading never touches the
  playing slot. Meta per slot: used length, bars, sample rate, mono, candidate count.
- **Analysis** (`[pd ana_g]` for grabs, `[pd ana_f]` for files): a `[switch~ 64]` subpatch reads the slot with an
  `rpole~` counter; (L+R)/2 squared → two `lop~ 150` (fast) and one `lop~ 4` (slow); `snapshot~` after each
  bang. Ratio fast/slow (gated at −70 dB): a candidate starts where it first passes 1.5 (40 ms refractory),
  its strength is the peak ratio while it stays above. Grabs are analysed behind the write head (every 20 ms),
  the rest at the bar line where the grab ends; files in chunks of 24 blocks per scheduler tick (~64× real time).
- **Slicing** (`[pd slices]`, on a switch or a sensitivity change): per step, the strongest candidate ≥ the
  threshold nearest to it; starts = onset − 1.5 ms (or the step position on the grid); lengths to the next start.
- **Clock** (`[pd clock]`): restart / absorb / beat on each pulse; sub-steps at L/4 (odd ones swung); an internal
  beat after L + grace without a pulse (exactly L while free-running).
- **Sequencer** (`[pd seq]`): relabel (step 1) → bar-line work (grab end, grab start, switch) → dice at the cycle
  start unless frozen → hit. **Hit** (`[pd hit]`): 9 dice per step (`ch_d*` tables) compared with the knobs →
  slice, reverse, ratchet, jump → **event** (`[pd ev]`): next of 2 voices: `tabread4~` tables set per slot,
  `vline~` index ramp at 2^(st/12) × file sr / 48 k, `vline~` envelope; the other voice fades out (choke).
- Control math uses `resonator.py`'s `E` compiler, extended with table reads, `[random]` with a seed, loops
  (`[until]`) and `w:table:index` writes. **Gotcha:** a float into `[v name]` sets it; reads must be banged
  (`val()` puts a `[t b]` first). This bit three times while building.

## Tests (`python tools/chop_tests.py`, 2026-11-14: all pass)
| Scenario | Result |
|---|---|
| file | 8 onset slices; starts at onset − 1.5 ms (+0.0..+0.25 ms); 16/16 hits are the right slice, 0.4–1.4 ms after their step; no clicks |
| grab | a 500 ms clock, the loop as input: the grab plays from the bar line where it ends, 16/16 hits right (+0.4..+1.4 ms) |
| mono44 | a mono 44.1 kHz file: right pitch, both outputs |
| shuffle | hits stay on the loop's steps; a new order every cycle; Freeze repeats it |
| fx | reverse, ratchets ×2–4, +12, jumps up/down, 12 ms stabs, Density 0.5 ≈ half; no clicks (max step 0.11) |
| clock | free-run 125 ms; lock with ±2 ms jitter: beats exactly on the pulses, never doubled; stop → free-run at the last tempo; restart after 3.5 s = step 1; tempo ramps ±30–40 ms per beat: still on the pulses |
| sync | Source gate mid-beat → the next beat is step 1; 10 ms after a beat → re-fired as step 1; the latch toggle is deduped |
| sens | alt Size CCW = 16 equal slices; back = 8 onsets; a pad → grid |
| long | 3 bars → 4 bars of steps (all of it); 7 bars → its first 4 bars |
| filehold | grab → file → File held → back to the grab, at bar lines |
| alt | 2-bar grab (32 steps); swing; ratchets ×2 only; 20 ms edges; stutter; Source + Record resets |
| stick | the unit's own WAVs (from the SD image, 24-bit 44.1 k): drum loop 23 slices, 22/22 on attacks; Moon Beats 15/15; mbira 8/8; piano and tape loop → grid at the default sensitivity |
| cpu | per minute of audio about 1.0–1.3× 04_glitch (batch, PC); patch load ~0.3 s longer (64 MB of tables) |

## Hardware questions
- Does the File-press dropout (blocking `soundfiler` read, up to 43 s of audio) matter in practice?
- Onset sensitivity at noon on the owner's own drum loops; the 1.5 ms pre-roll by ear.
- Clock feel with the module's real jitter; Source gate as step 1 from the sequencer.
- Load time on the Pi (the four slots are 64 MB).
