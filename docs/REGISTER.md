# register.instr: design notes

Built 2026-11-15: noise from a shift register clocked by Pitch, through a resonant low-pass. It's in the spirit
of a shift-register noise synth (our own design and name). The owner chose:
- **Freeze = lock the pattern**;
- **Source = the register drives the filter**;
- **Pitch = the clock, with Reset as an external clock**.

The rest was mine. Instrument `instr/register.instr`, tests `tools/register_sim.py`, guide
`docs/manual/17i_register.md`. Stick `016_register.instr`.

## Decisions for the owner to review
| # | Decided | Alternatives |
|---|---|---|
| 1 | **The register:** a linear-feedback shift register (taps for a maximal sequence at each length), stepped sample by sample in a user opcode (Csound has no LFSR opcode) | A k-rate register (no audio-rate clocks) |
| 2 | **Length (Start): 2 .. 24 bits**, more resolution at the short end. Short = a short repeating cycle (a pitched buzz); long = noise. Csound's bit operations are 32-bit, so `1 << 32` wrapped round and 32 bits went silent | 2 .. 31 |
| 3 | **Clock range on File:** noise (the click = 4186 Hz, to 48 kHz) → tone (÷16, click 262 Hz) → pattern (÷256, click 16 Hz). Pitch stays exact 1V/oct within each | A wider Pitch sweep (loses 1V/oct) |
| 4 | **Chance (Overlap):** the probability (0 .. 50 %) of flipping each fed-back bit. 0 = the register's own sequence (period 2^n − 1); 50 % = fully random | — |
| 5 | **Lock (Freeze):** the register just turns (the leaving bit comes back in), so the current pattern loops with a period of exactly its length | Lock = the chance goes to 0 (loops of 2^n − 1) |
| 6 | **Divide (Density):** the raw bits → a /2 → /4 → /8 flip-flop chain (each toggles on the previous one's rising edge), crossfaded | A mix of all four |
| 7 | **Filter:** `K35_lpf` (the Korg 35, as in the MS-20), nonlinear, Q 1 .. 9.9 (Window), cutoff 40 Hz .. 16 kHz (Size); the drive backs off as resonance rises | `zdf_ladder`; a state-variable filter with band-pass |
| 8 | **Source:** the register's low 8 bits as a value (a "DAC") step the cutoff, ±(alt Start × 2) octaves | Steps on the clock instead |
| 9 | **External clock (Reset):** each gate = one step; the Pitch clock takes over 2 s after the last gate | Reset reseeds |
| 10 | **Record = stereo:** a second register (another seed) on the right. It only runs while Record is on (CPU) | — |
| 11 | **Motion (Speed):** clockwise smooth wander (rspline), anticlockwise random steps (randh), of the clock (±1 octave) and the cutoff, at alt Window's depth | — |

## Engine notes
- Per-sample cost was the risk. The taps are looked up once per block, and the divider mix is done inside the
  opcode, so it returns 2 signals rather than 5. The worst case is both registers at the very top of the noise
  range; the test measures it.
- `dcblock`'s default gain (0.99) is a 76 Hz high-pass: it took the pattern range's fundamental. All our
  instruments now use 0.9995 (4 Hz).

## Tests (2026-11-15)
`wsl … tools/register_sim.py`: 14/14 on Csound 6.18. `python tools/register_sim.py m609`: 1/1 on 6.09.1.

| Scenario | Result |
|---|---|
| pitch | the 2-bit register's 3-step cycle at 1395.3 Hz (clock / 3), 697.7 Hz an octave down |
| range | tone 87.21 Hz, pattern 5.45 Hz |
| length | flatness 0.000 (2 bits) → 0.19 (24 bits; clocked noise dips at multiples of the clock) |
| chance | Overlap 0: repeats every 15 steps (autocorrelation 1.00); 1: random (0.05) |
| lock | a random 8-bit register locks into an 8-step loop (0.02 → 1.00) |
| divide | centroid 1627 → 333 Hz |
| filter | Size: centroid 165 → 1177 Hz; Window: a peak 13.6 dB over the passband |
| steps | Source: the filter's ring jumps 1.04 octave (sd) step to step, none without |
| extclock | steps only at the gates, Pitch's clock again 2 s later |
| stereo | L/R correlation 1.00 → −0.01 |
| motion | pitch sd 0.000 → 0.112 octave |
| sweep | 60 s of extremes: bounded, no NaN; CPU 0.44× the factory looper, 0.85× in the worst case (both registers at the top of the noise range; the clock is capped at 24 kHz) |

## Hardware questions
- The worst case (both registers at the top of the noise range) is 0.85× the looper's CPU on the PC; check it
  on the Pi.
- Is ÷256 slow enough for the pattern range, or should there be a ÷4096?
