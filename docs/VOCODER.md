# 10_vocoder — design notes

Built 2026-11-14 **without a design walk-through**: the owner was away ("make auto decisions and carry on to
next instruments for me to check"). Every choice below was mine. Each lists the alternatives, so the owner can
ask for a change after reading this (or after playing it). Builder `tools/vocoder.py`, tests
`tools/vocoder_tests.py`, guide `patches/10_vocoder_README.md` (also manual section `docs/manual/13_vocoder.md`).

## Decisions for the owner to review
| # | Decided | Alternatives |
|---|---|---|
| 1 | **Left in = modulator; carrier = internal chord, or the right input with Source on** (LED = external) | Source picks the modulator instead; or the carrier always comes from the right input when something is patched (Pd can't see jacks, so it would need a level detector) |
| 2 | **20 fixed bands, 100 Hz – 8 kHz, ⅓ octave apart, 4-pole band-pass each** | A band count on a knob (8 / 12 / 20); a wider range up to 12 kHz (more CPU, more hiss) |
| 3 | **Internal carrier = 3-note chord of 3 detuned saws each; Start picks 8 shapes** (unison, octaves, fifth, major, minor, sus4, maj7, min7); **Density = detune** | Start = voicing spread; more shapes; a pulse/square carrier; Density = voice count |
| 4 | **Pitch = chord root, 1 V/oct, click = C3** | Click = C4 (as resonator); semitone-quantised V/oct |
| 5 | **Speed = formant shift, ±6 bands, none between the clicks** (CW = formants up) | Formant shift on a knob (Size) with noon = none; a smaller range |
| 6 | **Freeze = hold the spectral envelope** (the carrier keeps playing) | Hold the carrier too (a held chord); a "sample-and-hold" on Reset instead |
| 7 | **File held = momentary freeze** (as shimmer) | File = next chord; File = carrier source |
| 8 | **Reset = next chord shape** (one past Start's zone, cycling) | Reset = retrigger an envelope on the carrier (a gated synth); Reset = freeze sample-and-hold |
| 9 | **Record = Track** (`sigmund~` follows the voice's pitch, rounded to semitones; Pitch then transposes) | No tracking (Record = something else, e.g. hold the chord); unrounded tracking (portamento-like) |
| 10 | **Overlap = sibilance** (noise driven by the voice above 5 kHz) | Sibilance fixed; Overlap = carrier leak |
| 11 | **Window = envelope speed** (one cut-off for attack and release) | Separate attack / release (alt Window = release) |
| 12 | **Blend = dry voice ↔ vocoder** | Dry carrier ↔ vocoder |
| 13 | **Alt layer:** width, presence, whisper, carrier leak, Track glide, noise gate; Source + Record = defaults | Band range, output drive, envelope release |
| 14 | **No carrier whitening** (classic channel vocoder: the carrier's own spectrum and level show through) | Whitening per band (any carrier gives a flat response, the level stops depending on the chord root). It was built first and cost about 1.8× shimmer's CPU, so it went |
| 15 | **Stick name `L_vocoder.pd`** (Pd yellow page, File; `ZZ_pitchlog` moves to Source) | — |

## Engine
- **Bands:** RBJ band-pass `biquad~` (two in series, 0 dB peak) per band for the modulator and the carrier.
  Pd's `bp~` was tried first: it's an all-pole resonator with no zeros, so every band passes the low end only
  ~5 dB down per stage, and the vocoder came out broadband. Size sets Q in 16 steps (1.5 – 12). Each step is
  one message box that sets all 80 biquads (the coefficients are computed in Python), so no trigonometry runs
  in the patch.
- **Carrier tilt:** +3 dB/oct (gain √(f/100 Hz) × CAL) folded into each carrier band's second biquad, so a saw's
  falling band energy comes out level.
- **Envelopes:** `abs~` → `lop~` (Window: 200 → 2 Hz). Freeze sets the cut-off to 0, and `lop~` then holds its
  state. The noise gate (broadband envelope against alt Blend's threshold) multiplies the modulator once,
  before the bands.
- **Formant shift:** every carrier band reads two modulator envelopes through `receive~` pairs (`set` on each
  integer step) and crossfades them by the fraction (a `line~`). Past the ends they read a silent `send~`.
- **Track:** `sigmund~ -hop 512 -npts 2048 -npeak 10 -maxfreq 2000` in a `switch~`ed subpatch (on only while
  Track is on: it's the costliest object, ~2× the whole band bank when running).
- **Output:** even bands → left bus, odd → right bus, panned once by the width (+6 dB makeup); + sibilance +
  carrier leak; equal-power mix with the dry voice; soft clip.

## Tests (`python tools/vocoder_tests.py`, 2026-11-14: all pass)
| Scenario | Result |
|---|---|
| bands | a sine at band 3 / 9 / 15 → that band (±1 at band 3) is the loudest, 26–35 dB over the median |
| shift | band 12 → 18 (Speed CW), → 6 (CCW), → 15 (half-way right) |
| freeze | held after the input stops (−24.0 → −24.2 dB), same spectrum (median 0.8 dB), silence on release; File held = momentary |
| gate | −70 dB noise in → silence; −30 dB → open |
| ext | Source on: the output is the 1 kHz carrier on the right input |
| pitch | click = C3 harmonics; Pitch 0.8 = C4; Start 0.45 = major (C3 E3 G3); Reset → minor (Eb3 sounds) |
| track | the root follows a 220 Hz voice (A3); Pitch 0.8 → 440 Hz; the output sounds at 220 Hz |
| sib | Overlap 1: +9.5 dB of noise above 5 kHz |
| level | white noise (−15.2 dB rms) → −17.0 dB out (white noise has 2/3 of its power above 8 kHz); Blend 0 = exactly the dry voice; everything moving at once: bounded, no NaN |
| cpu | per minute of audio about 0.9× 07_shimmer (PC batch) |

## Hardware questions
- CPU on the Pi (about shimmer's, which is itself awaiting a hardware report).
- Levels with a real voice and a microphone preamp: does the noise gate default (−60 dB) suit the module's
  input noise?
- Is the Track rounding (semitones) and its glide pleasant with a real voice?
- Do the defaults (Size noon, Window 0.3) sound like a vocoder straight away?
