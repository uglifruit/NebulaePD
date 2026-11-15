# tanpura.instr: design notes

Built 2026-11-14/15. The owner chose:
- Pitch click = C2;
- self-playing (Speed = cycle time), with a clock on Reset taking over (each pulse = the next string; 2 s
  without one and it plays by itself again);
- Record = pause;
- Start = the first string's tuning in zones (Pa / Ma / Ni / Sa);
- Blend only mixes the input in.

The rest was mine. Instrument `instr/tanpura.instr`, tests `tools/tanpura_sim.py`, guide
`docs/manual/17c_tanpura.md`.

## Decisions for the owner to review
| # | Decided | Alternatives |
|---|---|---|
| 1 | **Pitch = the low Sa** (the lowest string, C2 at the click); the middle Sa strings an octave up; Pa a fifth above low Sa | Pitch = the middle Sa (then the low string sits at C1) |
| 2 | **Just intervals**: Pa 3/2, Ma 4/3, Ni 15/8, Sa 2 | Equal temperament |
| 3 | **Evenly spaced plucks**, a quarter of the cycle each; Overlap sways them up to ±15 % | The traditional uneven rhythm (a longer pause after the low Sa) |
| 4 | **Speed: about 4 s between the clicks, to 1 s CW, 8 s CCW** | — |
| 5 | **Window = ring time 2–30 s** | — |
| 6 | **Density = jawari** (a folding bridge, see Engine); **Size = tone**; **Overlap = life** (sway + up to 6 cents between the Sa strings) | Overlap = pluck position |
| 7 | **Freeze = sustain** (loop gain 0.99999, the least-loss tone filter, the buzz faded out) | Freeze = hold the buzz too (the note then drains, 10 dB in 5 s) |
| 8 | **Source = octave up** | Source = a fifth string |
| 9 | **Alt: width, pluck hardness, reverb size and amount**; File unused | — |
| 10 | **Stick name `010_tanpura.instr`** (Csound user orange page, Freeze; `999_fw_backup`, `bt_storyteller`, `bt_test`, `pearls` move to the yellow page) | — |

## Engine
- **instr 10 (player):** a self clock; the Reset trigger takes over for 2 s; Record blocks plucks. It sets
  `gkTrig[string]` for one k-cycle.
- **instr 20.1–20.4 (strings), each a Karplus–Strong loop:**
  - `delayr`/`deltapi`/`delayw` at period − s/sr, with the loss filter (1 − s)·x + s·x[−1] (Size: s 0.5 → 0.05);
  - loop gain 10^(−3/(T60·f));
  - the pluck: a noise burst with a k-rate exponential decay, through `tone` (alt Size).
  - ksmps 32, so the shortest loop (one block) allows 1.3 kHz.
- **The jawari:** the string is folded back off a bridge that sits half an rms swing below its own centre (a
  20 Hz `tone` average). The fold's DC (a 5 Hz `tone`) is taken out of the correction only, so the string isn't
  detuned (98.14 Hz with full buzz).
- **What didn't work, and why (also in the code):**
  - Clipping instead of folding just shortened the notes.
  - A bridge measured from 0: the string drifted up off it within 0.1 s.
  - A bridge set from the peak: a plucked string is spiky (peak about 4× rms), so it sat below nearly
    everything.
  - `expseg` + `reinit` for the pluck envelope: replaced by the k-rate decay.
  - `portk` for the pitch glide: it starts at 0 Hz, so a pluck at load hit a string with no loop gain. Replaced
    by a glide that starts at the target.
  - `dcblock2` was avoided because of its delay (see docs/PULSAR.md).
- **instr 30:** sum, `dcblock`, `reverbsc` (alt), equal-power blend, `tanh`.

## Tests (2026-11-15)
`wsl … tools/tanpura_sim.py`: 16/16 pass on Csound 6.18. `python tools/tanpura_sim.py m609`: 1/1 on 6.09.1.

| Scenario | Result |
|---|---|
| strings | clocked one at a time: 98.1, 130.7, 130.9, 65.4 Hz (Pa, Sa, Sa, low Sa); a pluck at rms 0.057, peak 0.84 |
| tuning | first string × 1.501 / 1.333 / 1.876 / 1.999 of low Sa |
| self | noon: a pluck every 1.000 s, none missing; fully CW: every 0.250 s |
| clock | a pluck on every pulse (within the detector's 20 ms), nothing else; it plays itself again 2 s after |
| pause | no new plucks; the strings ring on (0.106 → 0.055) |
| freeze | frozen −44.6 → −47.6 dB over 5 s; unfrozen, the same strings are gone (−173 dB) |
| ring | −20 dB in 0.60 s (Window 0) against 2.65 s (0.6) |
| jawari | +6.6 dB above 1.5 kHz 1 s after the pluck, +12.8 dB 3 s after; pitch unchanged |
| octave | Source: Pa at 196.3 Hz |
| sweep | 60 s of extremes: peak 1.000 (tanh), no NaN; CPU 0.47× the factory looper |
| m609 | 6.09.1 compiles it; the 4th pluck at low Sa |

## Hardware questions
- Does the buzz sound like a jawari, or does it want more (Density's range) or a different shape?
- Is the even pluck rhythm right, or should it have the traditional pause after the low Sa?
