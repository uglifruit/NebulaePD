# 13_partials: design notes

Built 2026-11-14. The owner chose:
- Pitch click = C2 (all four drones);
- Blend only mixes the input in;
- "sculpt + deal": Start = which partials (all → odd → even → primes), Size = stretch, Window = tilt,
  Overlap = drift, Density = how many, Speed = drift speed (none between the clicks), Reset = deal a new
  random mix, Freeze = hold.

The rest was mine. Builder `tools/partials.py`, tests `tools/partials_tests.py`, guide
`patches/13_partials_README.md` (also `docs/manual/14c_partials.md`).

## Decisions for the owner to review
| # | Decided | Alternatives |
|---|---|---|
| 1 | **"Even only" keeps the fundamental at half level**, so the note doesn't jump an octave | Pure even (the drone sounds an octave up) |
| 2 | **Stretch: partial *n* at *n*^(1 + 0.4 Size)** (only upward) | Also compress (Size below noon = squeezed partials) |
| 3 | **Tilt: level *n*^(−2(1 − Window))**: 1/n² dark, 1/n (saw) at noon, flat bright | A brightness peak (formant) that moves |
| 4 | **Density fades the top partials in one by one** (1 = a pure sine) | — |
| 5 | **Drift = a random walk per partial every 50 ms**; step 0.1 × (distance past the click)², none between the clicks | Smooth noise per partial |
| 6 | **Deal: new random levels 0.15 – 1, gliding over alt Density (default 2 s)** | Instant; deal also the stretch |
| 7 | **File = even** (deal back to equal) | File = a stored "home" mix (store with a long press) |
| 8 | **Source = twins** (each partial + a twin 6 cents up, alt Size 0–20 cents) | Source = odd/even stereo split |
| 9 | **Record = sub** (a sine an octave below) | Record = freeze the deal |
| 10 | **The level is normalised** (0.25 / rms of the levels, at most ×2.5), so it stays put whatever the shape | Unnormalised (dark/sparse shapes get quieter) |
| 11 | **Alt: width (odd left / even right), twin detune, deal glide**; Source + Record = defaults | — |
| 12 | **Stick name `O_partials.pd`** (Pd yellow page, Freeze; `ZZ_pitchlog` moves to the blue page, Record) | — |

## Engine
- **Per partial:** a subpatch (`partial<n>`) with its drift walk (`random` → ±step → accumulate → `clip 0 1`) and
  its deal (`random` → `pack f glide` → `line`). One E-compiler program (`resonator.watched`) recomputes its
  frequency, twin frequency and level on any change.
- **Masks:** a 130-point table per partial, written at load. The four anchors land exactly on indices 0, 43,
  86 and 129, and the lookup rounds. With 128 points the anchors fell between indices and the masks leaked
  (an "even only" with odd partials 36 dB down).
- **Oscillators:** `osc~` + twin `osc~` (× Source) × the level (`line~` 60 ms), to an odd or even bus.
  Normalisation (`pt_norm`), twin compensation (−3 dB with twins on), width pan, the sub `osc~` at f1/2,
  equal-power blend, soft clip.
- Knob receivers use `[change -1]` (see docs/SHIFT.md).

## Tests (`python tools/partials_tests.py`, 2026-11-14: all pass)
| Scenario | Result |
|---|---|
| pitch | Density 0: one sine at 65.37 Hz, then 130.74; nothing at the 2nd harmonic (115 dB down) |
| harm | 16 partials at n × C2, Window CW: levels within 0.22 dB |
| stretch | Size 1: partials 2, 3, 5 at n^1.4 × C2, nothing at n × C2 (94–105 dB) |
| masks | odd only: even 112 dB down; even only: odd 132 dB down, fundamental −5.9 dB; primes: the rest 133 dB down |
| tilt | partial 8 against 1: −36.2 / −18.1 / −0.1 dB at Window 0 / 0.5 / 1 |
| drift | past a click: levels move 7.7 dB (CW) and 15.7 dB (CCW); between the clicks 0.00; Freeze 0.00 |
| deal | Reset: spread 0 → 15.4 dB, gliding (half-way 1.6 dB short); File: even again |
| twin | partial 16's twin at +6 cents: −54 → +0.2 dB |
| sub | Record: +120 dB at 32.7 Hz |
| level | 1 sine / 16 bright / 16 dark / primes / odd stretched: −20.9 to −21.1 dB; everything moving: peak 0.62, no NaN |
| cpu | 0.34× 07_shimmer per minute of audio (drifting, twins on) |
