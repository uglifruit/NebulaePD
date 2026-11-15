# horizon.instr and prism.instr: design notes

Built 2026-11-15. They're in the spirit of Bastl Instruments and Casper Electronics' **Dark Matter** (horizon) and
4ms's **Spectral Multiband Resonator** (prism). They're our own designs and names, written from the makers'
descriptions.

The owner chose:
- for horizon: Pitch = the loop's pitch, the panel's switches on the buttons, and a stereo reverb after;
- for prism: the SMR's own controls, with 11 scales in one bank.

Everything else was decided while the owner was away: see the tables below.

Guides `docs/manual/17ig_horizon.md`, `17ih_prism.md`; tests `tools/horizon_sim.py`, `tools/prism_sim.py`. Stick
`023_horizon.instr`, `024_prism.instr`.

## horizon decisions for review
| # | Decided | Alternatives |
|---|---|---|
| 1 | **The loop:** input (driven) + the delayed output → bass shelf → treble shelf → `tanh` → a 6 kHz one-pole → a DC block (38 Hz) → the delay. ksmps 16, so the shortest loop is 18 samples (C6 fits) | A per-sample loop (more CPU, higher squeals) |
| 2 | **Pitch:** the delay, 1V/oct, C4 (3.822 ms) at the click, C1–C6. Tested: rings at 263 Hz (C4 261.6), 521, 132 | Pitch as a filter in the loop (the original's character, but no note) |
| 3 | **Drive (Start):** −6 to +30 dB into `tanh`. Hyper (Freeze): +12 dB and a second `tanh` × 3 | A wavefolder for hyper |
| 4 | **Boosts:** Size = low shelf 180 Hz, Density = high shelf 3.5 kHz, 0–18 dB each (`pareq`), before the overdrive | Fixed boosts with a tilt knob |
| 5 | **Feedback (Window):** gain = Window / 0.7, so it sustains at 0.7 (about 2 o'clock) and rings past it. A −80 dB noise floor lets it start by itself | Unity at noon (rings too easily) |
| 6 | **Dynamics (Overlap), bipolar, ±5 % dead zone at noon:** an envelope follower (`follow2`, 3 ms attack; release 3 s slow / 0.3 s fast on Reset). Clockwise, VCA = 1 − d + d × env (playing opens it); anticlockwise, 1 − d × env (playing ducks it) | Separate open/duck switches |
| 7 | **VCA (File):** in the loop (it works the feedback) or out (it works the whole output, so the clean sound ducks too) | VCA always in the loop |
| 8 | **Polarity (Source):** the feedback inverted, so the loop rings an octave down with odd harmonics | Output polarity only (no audible effect without an external loop) |
| 9 | **Clean (Record):** before the drive or after it; X-fade (Blend) between clean and the loop (× 0.6) | — |
| 10 | **Wobble (Speed):** the loop's delay modulated ±6 % at the ends: a sine clockwise, random anticlockwise (0.3–6.3 Hz) | — |
| 11 | **Pulse:** a gate from the input's envelope (on above −20 dB, off below −26 dB) | A gate when the loop rings |
| 12 | **Reverb:** `reverbsc` after, alt Blend = amount, alt Window = size | — |

## prism decisions for review
| # | Decided | Alternatives |
|---|---|---|
| 1 | **Bands:** six, each two twin filters (two `resonz` in series, peak-normalised) that crossfade (equal power) when the band's note changes. Q = 2–500 (Size). Make-up gain √Q × 4 | `mode` resonators (ring, don't filter) |
| 2 | **Stereo:** the left and right inputs mixed into all six (one cable is enough); odd bands left, even right | Odds from the left input, evens from the right (the Nebulae can't tell if the right is patched) |
| 3 | **Scales (File), 24 notes each from the root:** chromatic, major, minor, pentatonic, whole tone, harmonic series (1–24), raga Bhairav, 17-TET, slendro (0, 231, 474, 717, 955 cents), Bohlen-Pierce (13 steps to 3:1), membrane (a drum's Bessel modes) | The SMR's own scale banks |
| 4 | **Notes:** band *i* sits on note *i* × Spread (Start: 1–4 steps). Root C3 at the Pitch click, 1V/oct, continuous | — |
| 5 | **Rotation:** Reset up, Freeze down, Speed auto (0.08–5 steps/s past the clicks). Record off: the six notes rotate round the bands (the chord stays, its notes cross sides). Record on: every band steps along the scale (the chord climbs, wrapping at 24) | — |
| 6 | **Morph (Density):** 5 ms–4 s. A change during a morph waits for it to finish, then the latest wins | Every step queued in turn (lags far behind a fast auto-rotate) |
| 7 | **Lock (Source):** the odd bands keep the rotation they had; the even ones go on | A lock per band (no buttons left) |
| 8 | **Nudge (Window):** odds up, evens down, ±5 semitones. **Tilt (Overlap):** ±6 dB a band (±15 dB at the ends) | Per-band level faders (the SMR's sliders) |
| 9 | **Pulse:** 10 ms on each step | — |

## Tests (2026-11-15)
- horizon: 15/15 on 6.18 + 6.09.1. Checked:
  - the pitch (within 0.6 %), self-start, polarity an octave down;
  - drive and hyper (THD −49 → −14 → −8 dB), the boosts;
  - Dynamics both ways (+82 dB open, −76 dB duck), the VCA out, Record, the envelope speeds, Pulse;
  - wobble (0.1 % between the clicks, 2–3 % past them), the reverb, the sweep.

  CPU 0.37×, reverb included.
- prism: 17/17 on 6.18 + 6.09.1. Checked:
  - tuning on both sides (> 40 dB clear of the other side's notes), transpose, scale, spread;
  - rotate up and down, scale rotation, lock, morph (0.22 vs 0.60 s to 90 %), auto-rotate both ways;
  - Pulse, nudge, tilt (+24 dB), Q, dry, the sweep.

  CPU 0.39×.
- Found on the way:
  - `follow2`'s release is a 60 dB time (0.5 s fell 10 dB in 80 ms);
  - white noise through narrow filters loses 20 dB, so prism makes it up by √Q;
  - noise through a narrow band wanders too much to time a morph (the test uses a chord of sines).

## Hardware questions
- horizon: is 2 o'clock the right place for it to start ringing? Does Dynamics need a wider dead zone?
- prism: is the make-up gain right with real material? Do the morphs click at short settings?
