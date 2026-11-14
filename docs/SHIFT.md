# 12_shift: design notes

Built 2026-11-14. The owner answered four design questions, all with the recommended option:
- Pitch = shift amount (centre = none);
- Speed = time, with Reset clocking it;
- modes Shift / Ring / Barber;
- a tape-ish loop.

Then they went away ("auto choose sensible options"), so the rest is mine. Builder `tools/shift.py`, tests
`tools/shift_tests.py`, guide `patches/12_shift_README.md` (also manual section `docs/manual/14b_shift.md`).

## Decisions for the owner to review
| # | Decided | Alternatives |
|---|---|---|
| 1 | **Pitch = shift, click = none, 0.1 Hz → 1 kHz per side on an exponential curve**; CV follows the same curve (up to 2 kHz) | **The walk-through promised "V/oct doubles the shift per volt".** That can't hold on one knob: 1 V/oct gives the 5 octaves of the knob's travel, the range is 13. Options: keep this; true 1 V/oct over a smaller range (e.g. 30 Hz – 1 kHz, no slow phasing); a coarse/fine split (alt Pitch = fine) |
| 2 | **Modes: Source = Ring (its LED), File = Barber (no LED)** | **Changed from the walk-through**, which had Source cycling three modes with the light off / on / blinking. Pd can't set any LED, so Source only shows on/off. Alternatives: Barber on Record (an LED) and flip on File; Source cycling three modes (the LED would show only odd/even) |
| 3 | **Stereo is Size, continuous**: right side's shift = left × (1 − 2 × Size) (same → none → opposite) | The walk-through had File = stereo on/off. File went to Barber, so stereo became a knob, which also gives the in-between "right side unshifted" |
| 4 | **Barber = a band-pass bell in the loop** (Window = centre 200 Hz – 4 kHz, Q 1) instead of the tone filter: echoes climb out of the band and fade while new ones enter, the Shepard-like endless climb | Two crossfading layers with ramping shifts (the barber-pole flanger method), a heavier build; Barber as a knob amount |
| 5 | **Ring = both sidebands** (re × cos, √2 to keep the level) | Ring with the carrier mixed in (amplitude modulation) |
| 6 | **Record = flip** (LED on = flipped), as the walk-through | — |
| 7 | **Freeze = feedback 100 %, input shut out** (the low cut drops to 5 Hz while held) | Freeze keeps the input coming in (a "sound on sound" hold) |
| 8 | **Speed free = 2 ms – 2 s** (exponential, 2000^Speed); **clocked = 7 zones** (1/16, 1/8, 1/8., 1/4, 1/2, 1 bar, 2 bars) | Fewer zones; triplets; a longer free range |
| 9 | **Clock: Reset pulses 30 ms – 4 s apart. The beat is a running average, and a 15 ms jump = a new tempo. Time follows only past 1 ms of drift. Free again after 2 s (or 2.5 beats).** A single press never sets a beat (only two in a row) | Tap tempo that latches (no timeout) |
| 10 | **Time changes glide over 250 ms** (a tape pitch bend) | A crossfade between two read heads (no bend, a click-free jump) |
| 11 | **Density = feedback 0 – 110 %, soft clip in the loop** | 0 – 100 % only |
| 12 | **Window = tone: noon flat, left = one-pole low-pass 20 kHz → 300 Hz, right = high-pass 20 Hz → 3 kHz** | A resonant filter; separate low/high knobs |
| 13 | **Start = ping-pong cross-feed** | Start = left/right time offset |
| 14 | **Overlap = direct** (the input through its own shifter, no delay) | Overlap = wow (moved to alt); Overlap = second tap |
| 15 | **Alt: wow depth (0.6 ms), drive (×2), low cut (27 Hz), wow rate (~0.5 Hz)**; Source + Record = defaults | Flutter; output level; saturation colour |
| 16 | **Stick name `N_shift.pd`** (Pd yellow page, Reset; `ZZ_pitchlog` moves to Freeze) | — |

## Engine
- **Per side:** `delwrite~` (10 s), `vd~` (4-point interpolation) at time + wow (clipped 2 ms – 9.5 s). Then
  Pd's `hilbert~` biquad pair (copied in, so nothing outside the patch is needed). Then `complex-mod~` logic:
  re·cos − im·sin, where the sign of the shift sets the direction (`phasor~` runs backwards for negative
  frequencies). Then tone (`lop~` → `hip~`) or Barber (`bp~` × 0.632: `bp~` peaks +4 dB at Q 1), the low
  cut `hip~`, and drive × soft clip ÷ drive = wet.
- **Feedback:** wet × (1 − ping-pong) + the other side's wet (`send~`/`receive~`, one block later) × ping-pong,
  × feedback (Freeze = 1), + input × (1 − Freeze).
- **Direct:** the input through its own Hilbert pair, the same oscillator.
- **Control:** knob receivers use `[change -1]`, so the first value always passes (see the gotcha below).
  Expressions run through resonator's E compiler (no `[expr]`).
- **Gotcha found here:** `[change]` starts at 0, so a knob reading exactly 0 at load never replaced the load
  default. The test caught it as feedback stuck at 0.4. Other patches use `[change]` the same way (for example
  10_vocoder's Density, whose 0.005 default stays if the knob is fully down at load). It's harmless while a
  knob isn't at exactly 0. Not changed there yet.

## Tests (`python tools/shift_tests.py`, 2026-11-14: all pass)
| Scenario | Result |
|---|---|
| shift | 1 kHz + 100 Hz → 1100 Hz, other sideband 53 dB down; Record → 900; Size CW → left 1100 / right 900; −300 Hz → 700; Ring → 900 and 1100 equal (±0.0 dB), carrier 106 dB down; the click → 1000 Hz only |
| direct | Overlap: the 1200 Hz shift heard before the first echo; Blend 0 = dry only |
| time | echo spacing 95.7 ms at Speed 0.6 (2000^0.6 = 95.6), 437.5 ms at 0.8 (437.3) |
| clock | 10 pulses, 500 ms ± 2 ms: beat 500.5 ms, then still; 1/4 = 500.5 ms, 1 bar = 2002 ms; free again 2 s after the last pulse; echoes 500.6 ms apart |
| climb | +50 Hz, feedback 0.8: echoes at 551, 598, 650, 697, 750, 803 Hz (550 … 800) |
| freeze | the level holds (−3.8 dB after 1–2 s as the top softens, −5.1 dB after 4 s); new input stays out; released, it comes in; bounded |
| barber | File toggles it; at the band centre within 1 dB of the tone path; the loop is a bell (31 dB over 6–12 kHz, against 1 dB in tone mode) |
| runaway | feedback 110 %, Ring, ping-pong, drive ×6, wow 4 ms, sweeps, Freeze on and off, 40 s: peak 0.95, no NaN, still sounding |
| cpu | per minute of audio 0.25× 07_shimmer (PC batch) |

## Hardware questions
- Does a 1–3 ms jittery module clock give steady echoes (the average should hold within 1 ms)?
- Is the Barber band audible as an "endless" climb, or does it want two crossfading layers (decision 4)?
