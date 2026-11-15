# avalanche.instr and lattice.instr: design notes

Built 2026-11-15. They're in the spirit of Jolin Lab's **Tabor** (avalanche) and Make Noise's **Soundhack
Plexiphon**, made with Tom Erbe (lattice). They're our own designs and names, written from the makers' descriptions.

The owner chose:
- for avalanche: the oscillators on the knobs, and a stereo reverb after (it's mono);
- for lattice: Plexiphon's own controls.

Everything else was decided while the owner was away: see the tables below.

Guides `docs/manual/17ie_avalanche.md`, `17if_lattice.md`; tests `tools/avalanche_sim.py`, `tools/lattice_sim.py`.
Stick `021_avalanche.instr`, `022_lattice.instr`.

## avalanche decisions for review
| # | Decided | Alternatives |
|---|---|---|
| 1 | **The oscillators:** four relaxation oscillators modelled sample by sample (a `setksmps 1` UDO). Each charges exponentially towards the supply, fires at 0.75 and resets to 0.1, with the rate set so that a full-power cycle takes 1/f | Avalanche-transistor circuit models (heavier, and no knob to show for it) |
| 2 | **The ties:** OSC1 kicks OSC2 (Size × 0.4) and some of OSC3. OSC2 kicks OSC3 (alt Size) and back to OSC1 (Start × 0.25). OSC3 kicks OSC1. OSC4 only shutters | All-to-all (a matrix with no knobs for it) |
| 3 | **Rates:** OSC1 on Pitch, 1V/oct (4 Hz at the click in the rhythm range, C3 in the tone range: File). OSC2 = OSC1 × 0.25–4 (Density). OSC3 = OSC1 × 0.25–4 × 1.13 (alt Start). OSC4 0.2–20 Hz (Window) | Free rates per oscillator (harder to keep musical) |
| 4 | **Starve (Speed):** full power at noon; either way the supply drops by up to 0.32, under the threshold, so the oscillators slow, stutter and stop. Source: your input's level starves it too | Starve on one side only |
| 5 | **Jitter:** ±4 % per sample on the charge rates (the components' noise). Freeze stops it, and the pattern settles into a cycle | No jitter (too regular) |
| 6 | **Shutter (OSC4, Overlap = depth):** shut for the early part of its cycle, open after. With Record it closes a low-pass (200 Hz–8.2 kHz) instead | A VCA on its ramp |
| 7 | **The sound:** the ramps centred plus their discharge spikes (NM). ZZ = `tanh(6x) − 0.3 tanh(2x)` into a 2.5 kHz low-pass. Blend crossfades | A diode-ladder fuzz |
| 8 | **TR (Pulse):** 15 ms whenever two oscillators fire in the same sample | One gate per OSC1 firing |
| 9 | **Reverb:** `reverbsc` after, alt Blend = amount (squared), alt Window = size | — |

## lattice decisions for review
| # | Decided | Alternatives |
|---|---|---|
| 1 | **The network:** eight delay paths (even indices left, odd right), lengths Size × 1, 1.127, 1.268, 1.413, 1.583, 1.731, 1.879, 2.039. Each reads the previous block's mix: a one-block lag, 0.67 ms, folded into the lengths | A per-sample FDN (several times the CPU) |
| 2 | **Mixing:** Householder-like: each path gives back itself minus a share of its group's sum, through `tanh`. The group is its own side (Couple 0) or all eight (Couple 1) | A full Hadamard matrix |
| 3 | **Plexus (Start):** low = all eight paths at full gain and fully entangled (reverb). Up = the paths fade out one by one to the first of each side, entanglement goes to 0, and taps at 1.5 × Size come in (the multi-tap echo) | Separate reverb and echo engines crossfaded (not modeless) |
| 4 | **Size (Pitch):** 5 ms–1.4 s, 120 ms at the click, 1V/oct, glided over 0.1 s (it re-pitches what's in the network) | Unglided (jumps) |
| 5 | **Decay (Overlap):** feedback × 1.12 at the top: super-infinite, held by the `tanh` | Capped at 1 |
| 6 | **Diffuse (Density):** four allpasses per side (4.7–21 ms, coefficient 0.62) mixed in, plus a low-pass closing from 18 to 5.4 kHz. Tested: the first pass's crest factor drops 3 dB | Allpasses inside the loop (it smears the echoes too) |
| 7 | **Color (Window):** a one-pole low-pass in every path below 1 o'clock (800 Hz–18 kHz), a one-pole high-pass above (20 Hz–1.5 kHz) | A tilt EQ |
| 8 | **Skew (File):** off → inverse (alt Size pushes Plexus and Color ± half that, Size ± up to an octave, left against right) → tandem (the same way) | Skew on a knob |
| 9 | **Send (Freeze, momentary), Hold (Source), Clear (Reset):** the clear lasts until the longest path and its tap have emptied | Freeze as a latch |
| 10 | **Pulse:** high above −30 dB (5 Hz envelope), held 150 ms, so it doesn't chatter | A trigger per echo |
| 11 | **Size and Record are unused:** Plexiphon's controls fill the rest | Modulation on Size (Plexiphon has none) |

## Tests (2026-11-15)
- avalanche: 14/14 on 6.18 + 6.09.1. Checked: C3 and 1V/oct in the tone range, 4 Hz in the rhythm range;
  cross-mod changes the rhythm; starve slows and silences; steady repeats; kick; the TR log; the shutter;
  the fuzz; source; reverb; the 60 s sweep. CPU 0.77× the factory looper, reverb included.
- lattice: 14/14 on 6.18 + 6.09.1. Checked:
  - echoes at Size (120 ms, and 240 ms at +0.2);
  - a dense tail with Plexus low, sparse echoes with it high (118 vs 29 peaks/s);
  - Decay ×9 in tail length; super-infinite; Color 21 dB apart; diffusion; Couple −219 → −1 dB;
  - skew; send; hold; clear (−93 dB); Pulse with no chatter; the sweep.

  CPU 0.42×.
- Found on the way:
  - taps beyond the delay buffer crash Csound 6.18 (a segfault mid-render that still leaves a valid, shorter WAV),
    so every tap is clamped and every sweep now checks it ran to the end;
  - Csound's `alpass` takes a ring time, not a coefficient (a long one passes the click straight through).

## Hardware questions
- avalanche: is 4 Hz the right centre for the rhythm range? Does Starve's range feel right?
- lattice: does Plexus morph smoothly enough between reverb and echo? Is super-infinite too loud?
