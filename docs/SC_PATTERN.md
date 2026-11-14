# 05_sc_pattern — design notes

Designed with the owner on 2026-11-14 (four questions: voices, patterns, clock, panel; all recommended options,
the panel as sketched in `docs/SC_IDEAS.md`). The owner was then away again ("make auto decisions"), so the details
below the line were mine. Patch `sc/05_sc_pattern.scd`, tests `tools/sc_pattern_tests.py`, guide
`docs/manual/18_sc_pattern.md`.

## Agreed
- Four voices: pluck lead, FM bell, bass, noise hat.
- Euclidean hits per voice (Density) with a chance per hit; notes walk the scale; mutation re-rolls notes and
  rotations.
- Reset = one 16th, the tempo measured and each step **scheduled ahead** of its sound time (SC's 32 ms output
  latency); no clock = internal tempo on Speed.
- Panel: Pitch root, Start scale, Size length, Density hits, Overlap mutation, Window tone, Blend space (JPverb),
  Speed tempo/swing; Freeze lock, Record mutate, File home; alt = voice levels, octave spread, decay.

## Decided while the owner was away
| Decision | Why / alternatives |
|---|---|
| Source = voice set B (square lead, glassy bell, sub bass, shaker) | The panel sketch said "voice set A/B"; alternatives: a second pattern bank |
| File short = recall home, held 1 s = store home | as topo |
| Hit chance 85 %, rolled per cycle, held by Freeze | "chance" from the walk-through |
| Hits per voice = round(Density × weight × length), weights lead 0.75, bell 0.4, bass 0.5, hat 1.2 | a busy hat, a sparse bell |
| Notes: a random walk of scale degrees (−2..+2, sometimes a fourth), within −3..9 | |
| Tempo free: 60–240 BPM on Speed (120 between the clicks); swing right of the right click when clocked | Speed persists across instruments, so a load on a click is the default tempo |

## The clock (the hard part)
The module's output latency is 32 ms, so a step played when its pulse arrives is late. Instead:
- each step is **sent before its sound time** (timestamped OSC bundle, `s.makeBundle`), sound time = the predicted
  pulse; it goes out 30 ms + 32 ms early (the 30 ms margin rides over sclang stalls, which the tests log);
- a **phase-locked loop** follows the clock: each pulse is matched with the step already sent for it (from 40 %
  early to 60 % late: a stalled poll loop delays, never advances), the tempo eases 20 % towards the measured
  interval and the next step absorbs half the phase error. A tempo change only counts when two intervals in a row
  agree (one late pulse is a hiccup, not a change); then it follows at once;
- a pulse with no step sent for it (a much faster clock) plays its step at once;
- no pulse for max(2 s, 4 steps) = free-running at the Speed tempo;
- the first pulse, or one after such a gap, = step 1. A free-running step that hasn't started on the server yet is
  freed at its own start time (same time stamp, later in order), so it never flams with step 1. One already
  sounding from 50 ms before the pulse stands in as step 1.

Bugs found by the live test on the way: a jittery pulse taken as a tempo change; a restart flamming with the
last free-run step; a very late pulse doubling a step. All fixed as above.

## Tests (`python tools/sc_pattern_tests.py`, 2026-11-14)
- syntax: sclang compiles it.
- logic (17 checks, sclang, no server): lengths 4/16/32; hits per voice = Euclid; every note in the scale (major,
  minor pentatonic); Pitch 0.7 = +6 semitones; Freeze = identical cycles with full mutation; mutation changes
  cycles; Record burst; File home recall and store; hit chance 0.845 (0.85); set B.
- nrt: 16 s render, bounded (peak 0.22), not silent, set B's spectrum differs.
- live and liveq (the patch running for real, OSC pulses from Python, 120 BPM, ±2 ms jitter; liveq on the module's
  5.3 ms poll grid): steps sound on the clock (median ≈ 0, p95 3–6 ms, worst 4–10 ms), sent ≥ 41 ms ahead, one
  step per pulse, carries on when the clock stops, step 1 after a 3 s gap, no flam at either clock start. The PC
  sometimes holds the Python sender back by 20–100 ms (Windows with SC running); such runs are not judged (up to 3
  attempts).

## Hardware questions
- Does it land on time with the owner's clock (the module's real latency may not be exactly 32 ms: `~lout`)?
- CPU with JPverb on the Pi; levels of the four voices.
