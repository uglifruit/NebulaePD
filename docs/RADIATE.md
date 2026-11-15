# radiate.instr: design notes

Built 2026-11-15: a stereo filter of four resonant peaks, in the spirit of a quad-peak filter (our own design and
name, not a copy). The owner chose:
- Pitch = cutoff with exact 1 V/oct, **click = C6** (1046.5 Hz; about 46 Hz .. 11.7 kHz);
- Size = resonance up to self-oscillation, Start = Radiate, Window = output morph LP → BP → HP → smile, Reset =
  ping, Speed = animation, Blend = dry/wet;
- **Freeze = hold the animation**;
- **Source = the right input modulates** (audio-rate FM of the cutoff);
- **File = peak tuning shapes** (even → harmonic → octaves → chord);
- **Record = clean ↔ dirty**;
- **Density = number of peaks (1 → 4), Overlap = drive**, animation depth on the alt layer;
- the name **radiate**.

The rest was mine. Instrument `instr/radiate.instr`, tests `tools/radiate_sim.py`, guide
`docs/manual/17e_radiate.md`. Stick `012_radiate.instr` (Csound user, yellow page, Record).

## Decisions for the owner to review
| # | Decided | Alternatives |
|---|---|---|
| 1 | **Filters: `zdf_2pole_mode`** (zero-delay-feedback 2-pole, low/band/high from one filter, cutoff swept every sample), 4 peaks × 2 channels in parallel | `K35` or `diode_ladder` (nonlinear, but low/high only and dearer); a hand-written nonlinear SVF (per-sample code: far too slow on the Pi) |
| 2 | **Self-oscillation is synthesised:** above 85 % of Size, each peak's Q keeps rising (40 → 120) and a sine exactly on its frequency fades in. A linear filter can't self-oscillate stably, and a nonlinear one in Csound would need per-sample code. The tuning is exact (1 V/oct tested to 0.01 %); the sine doesn't get pulled by the input the way an analog filter's does | True nonlinear self-oscillation (out of the Pi's reach in Csound) |
| 3 | **Ping = the same sines, struck:** Reset makes every peak ring at its frequency, decaying over alt Density's time (20 ms .. 3 s). Exact pitch, even level whatever the resonance | Feed an impulse into the filters (the level then depends on Q and frequency, from a click to deafening) |
| 4 | **Radiate spreads the peaks upward from the lowest** (Pitch = the lowest peak, so a self-oscillating chord sits on the Pitch note). Noon = exactly the File shape (a flat zone, 0.4–0.6, so it's easy to find); fully anticlockwise = all on one peak; fully clockwise = twice the shape | Spread both ways round the cutoff |
| 5 | **Shapes (semitones above the lowest):** even 0 8 16 24; harmonic 0 12 19.02 24 (1:2:3:4); octaves 0 12 24 36; chord 0 7 12 16 (root, 5th, octave, 10th). Changes glide over 30 ms | Other chords; a 5th shape |
| 6 | **Stereo: each peak has a place** (at full width: −0.3, +0.3, −0.8, +0.8, low peaks near the middle, high peaks wide), as a balance so a stereo input's channels never cross. alt Overlap = width (default 0.6) | Detune the right channel's peaks against the left |
| 7 | **Smile = the lowest peak's low-pass + the highest peak's high-pass**: lows and highs pass, with resonant edges and a dip between that widens as Radiate spreads. With one peak it's a notch | A notch at every peak |
| 8 | **Output morph:** a linear crossfade of adjacent types (LP→BP, BP→HP, HP→smile) | Equal-power crossfade |
| 9 | **Levels:** low/high-pass × Q^−0.3 (the passband dips a little as the peak grows), band-pass × 2 Q^−0.5; +4 dB makeup. Pink noise in: every type and resonance within −2.7 .. +5.7 dB of the input | Keep the passband at unity (the peak gets very loud at high Q) |
| 10 | **Source (FM):** the right input sets an exponential multiplier on every cutoff (alt Start = depth, up to ±4 octaves for a full-scale input), at audio rate; both filter channels then take the left input. Exponential FM raises the average pitch a little at depth, as on analog filters | Linear FM |
| 11 | **A silent right input copies the left** (rms under −66 dBFS, 50 ms fade), so a mono source comes out in stereo. A stereo source with long silences on the right gets the left copied during them | Never copy (a mono source leaves the right side empty) |
| 12 | **Dirty (Record):** an asymmetric tanh before the peaks (even and odd harmonics), the signal pulling every cutoff by up to ±0.15 octave (a growl), and a tanh after. Clean: only the final soft clip | Switch to the diode ladder |
| 13 | **Animation (Speed):** none between the clicks (the depth fades out over 0.3 s); clockwise a sine/cosine pair (a circle: Radiate one way, cutoff the other); anticlockwise a smooth random pair; 0.03 .. 8 Hz towards the ends. alt Size = depth (Radiate ±0.25, cutoff ±2 octaves), alt Window = target (Radiate only ↔ both ↔ cutoff only) | One LFO shape; a separate depth knob |
| 14 | **Freeze stops the animation's phase and depth** where they are | Freeze the whole sound |
| 15 | **Drive (Overlap):** ×0.35 .. ×11, unity at 0.3 | — |
| 16 | **alt Blend = output level ±12 dB**; alt Pitch unused | Reverb (most of our instruments) |
| 17 | **Defaults at load:** C6, Radiate noon, Size noon (Q ≈ 6), four peaks, low-pass, drive unity, fully wet | — |

## Engine
- **instr 10 (control):**
  - File → shape; Reset → a one-block ping flag;
  - the animation phase (stopped by Freeze);
  - each peak's frequency, level (Density), balance (width), and the output weights;
  - written out with a macro, `$PEAK(n)`, not a loop.
- **instr 15 (input):**
  - drive; the right input's two jobs (audio, or the FM modulator);
  - the silent-right copy;
  - the a-rate cutoff multiplier `exp(...)`. `exp` works at a-rate in 6.09; `pow` doesn't.
- **instr 20.1–20.4 (peaks):** each filters both channels at an a-rate cutoff (the k-rate frequency, interpolated,
  times the multiplier), mixes low/band/high/smile, and adds its voice (self-oscillation or ping) with `poscil` at
  the same a-rate frequency, so FM moves the voices too.
- **instr 30 (out):** `dcblock`, the dirty tanh, the level, equal-power Blend, then a final `tanh`.
- `zdf_2pole_mode` outputs low, band, high, in that order. All three have a gain of Q at the cutoff (measured in
  6.18).
- On the module, every opcode used is in Csound 6.11: checked against the SD image's `libcsound64.so`.

## Tests (2026-11-15)
`wsl … tools/radiate_sim.py`: 30/30 on Csound 6.18. `python tools/radiate_sim.py m609`: 1/1 on 6.09.1.

| Scenario | Result |
|---|---|
| pitch | self-oscillating: 1046.50, 523.25, 2093.00, 130.81 Hz at Pitch 0.6 / 0.4 / 0.8 / 0 (C6, C5, C7, C3); rms 0.30 |
| types | one peak, white noise: LP lows over highs +28.4 dB; BP +31/+32 dB over both; HP +27 dB; smile a notch 17 dB deep |
| shapes | 4 peaks within 2.5 % of each shape (noise-driven peaks pull towards close neighbours, up to 1.7 %; the voices are exact) |
| density | 1, 2, 3, 4 peaks |
| radiate | fully anticlockwise one peak (27 dB clear); fully clockwise 0 16 32 48 semitones |
| stereo | full width: peaks 3 / 4 at +13.9 / −13.5 dB L−R; width 0 centred |
| ping | silent until the ping, then 1046.50 Hz; ring time 0.14 s → 2.6 s (alt Density 0.2 → 0.8) |
| animate | centroid sd 0.03 octave between the clicks, 0.44 clockwise, 0.03 frozen, 0.30 anticlockwise |
| fm | Source off: one line, the right input heard; on: 14 sidebands 100 Hz apart, the right input gone (−107 dB) |
| normal | silent right input: L = R; a live right input stays its own channel |
| dirty | clean 2nd/3rd harmonics −121/−45 dB; dirty −31/−32 dB |
| level | pink noise: −2.7 .. +5.7 dB of the input over every type and Size 0–0.85 |
| sweep | 60 s of extremes: bounded, no NaN; CPU 0.69× the factory looper |
| m609 | 6.09.1 compiles it; self-oscillates at 1046.50 Hz |

## Hardware questions
- Does the synthesised self-oscillation feel right when you play a sequence into Pitch, and with input running?
- Dirty: is it dirty enough? The diode ladder is the next step if not.
- The silent-right copy: any false switching with real sources?
