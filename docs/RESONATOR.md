# 08_resonator — design

Builder: `tools/resonator.py` (prefix `rs_`). User guide: `patches/08_resonator_README.md`.

Goal: one voice of a Morphor ECHON-style instrument (exciter → BBD delay-line resonator) plus a BBD-style echo
after it. The owner's choices were:
- an internal exciter struck by Reset, with Source swapping in the audio input;
- dual L/R resonators with spread;
- a BBD-style stereo delay, with free time on Speed;
- three V/oct routing modes on a short File press, where the fixed side sits at C4 + the stepped offset.

## Signal flow
```
[exciter] phasor~ (rs_fexc) -> 6 shapes x weights -> x env^2 x kf x EXC   | or adc~ x icx (Source)
          -> hip~ 20 -> lop~ x2 (alt Start) -> x nf (freeze) x agc
[res]     block~ 16, per side: w = x + softclip(g * hip~1(lop~ damp(vd~ D))) -> delwrite~ ; out = x(1-bal) + read*bal
[bbd]     per side: in*ein (+ping-pong) + softclip(eg * cross(hip~(lop~ tone(vd~ dt + wobble)))) -> delwrite~ 2100
out       = softclip(res * gd + bbd * gw) -> dac~
```

## Voices and strike timing (hardware report 2026-11-07: big pitch jumps glided)
There were two causes:
- **The firmware slews Pitch.** `control.py`'s HybridData runs Pitch through a one-pole (0.33 per poll),
  hysteresis (0.001) and a stability gate, and the CV input has a cap, so a jump arrives as a 10–30 ms ramp.
- **One loop retuned the ringing note** like a slide.

The fixes (the owner picked both):
- **Two voices** (`VOICES = 2`) per side in `[pd res]`. `rs_go` toggles `rs_av`, which sets:
  - the excitation gates `rs_vg<k>` (1 ms);
  - which voice receives `rs_fr` → `rs_frk<k>`;
  - which voice's `rs_icx<k>` the exciter uses.

  Each voice has its own program (`voice_assigns(k)`) computing its damping, gain and D from its own pitch; the
  shared knobs (Size, Window, Freeze, Invert, spread) apply to both. At takeover the new voice's D moves in
  1 ms (`rs_Dms`), not 5.
- **Lag queue:** the active voice gets `rs_fr` through `[pipe LAG_MS]` (40 ms). A strike sends `clear` to it and
  pushes the current pitch straight to the new voice. Without this, the CV step that comes just before the gate
  retuned the old note (seen offline: its 261 Hz vanished after an octave jump).
- **Settle wait:** a strike fires once all of these hold:
  - at least STRIKE_MIN = 3 ms have passed;
  - SETTLE_N = 2 consecutive Pitch updates have each moved less than SETTLE_D = 0.0008, or no update has
    arrived for STALE_MS = 4 ms (offline tests send Pitch once).
  It fires at STRIKE_MAX = 30 ms at the latest.
- **Measured** with a firmware-style ramp (0.6 → 0.8, one-pole 0.33/ms, hysteresis): the strike came after
  14 ms at 521.3 Hz. The target is 523.3, and the last 7 cents follow live. With steady Pitch: 3 ms.

## Resonator
- **Block size.** `[pd res]` runs at `block~ 16`, because a feedback loop through `vd~` is at least one block long.
  DMIN = 17 samples, so the top is FMAX = 2600 Hz, or 1300 Hz inverted. The pitch is clamped there rather than
  going out of tune. With `block~ 16` and the reader sorted before the writer, `vd~` gives exactly the requested
  delay: the measured residual is 0, `KRES = 0`.
- **Tuning (control rate, `[pd ui]`):**
  - `D = P − τ_lp(f) + τ_hp(f)`, where P = SR/f_side, halved when inverted.
  - The one-pole LP phase delay is `τ_lp = atan(b sin ω / (1 − b cos ω)) / ω`, with b = 1 − min(1, 2π fc/SR)
    (Pd's lop~ coefficient). The DC blocker's lead is approximately `atan(1/f)/ω`.
  - L/R use f·2^(∓sp/2400).
  - Measured: 0.00 cents from 92 Hz to 2.49 kHz with Window open and at noon. About −1 cent with Window CCW, which
    is a strongly damped mode, measured in the first 100 ms.
- **Damping:** `fc = f_res · 2^(1 + 5.5 w)`, key-tracked. Window CW is open for f > 85 Hz, because the lop~
  coefficient clips to 1. Freeze sets fc to 1e5, which is exact passthrough.
- **Gain:** `g = min(1, 10^(−3 T_loop/T60) / |H_lp(f)|)`, with `|H| = a / √(1 − 2b cos ω + b²)`.
  - The fundamental decays at T60 whatever the damping is, until the cap: with Window CCW, high notes are short.
  - It is never above 1: with g > 1 the modes below f (the near-DC mode the hip~ leaves) would grow.
  - Measured: 0.341 s (target 0.34) and 2.32 s (target 2.33), at 92 and 261 Hz and with Window at noon.
- **Invert (Record):** g negative. The modes sit at odd multiples of 1/(2 T_loop), so P is halved. The even
  harmonics vanish (checked: 522 Hz gone, 784 Hz present on a 261 Hz note).
- **Freeze:** g = 1, damping open, excitation × 0. Over 18 s it holds within 0.3 dB; the slow drain comes from
  hip~ 1 at low notes.
- **Spread (alt Size):** cents between L and R. At 0 the two sides are sample-identical.

## Exciter
- **Shapes:** sine `cos~(φ + 0.75)`, tri, saw, square (`spectral.step`), `noise~`, and `samphold~` noise
  clocked by the phasor wrap. Weights are `w_k = max(0, 1 − |5·start − k|)`. Gains are
  SHAPE_K = 0.85/1/1/0.6/2/3, because noise builds up less in a resonator than a tone at its pitch does.
- **Envelope:** `vline~` "1 A, 0 Dc A", squared. A = 0.5·3000^d ms and Dc = 5·600^d ms. The phasor resets on
  each strike, so plucks are repeatable.
- **Level:** `kf = (1 + f_res·(A + Dc/2)/1000)^−0.75`. A strike spanning N periods of a matched tone builds up by
  about N^0.85. Measured pluck peaks are 0.30–0.71 from 92 Hz to 2.5 kHz.
- **Audio input:** `icx = min(1, KX·√(1 − G))`, with G = g·|H| and KX = 1. That's right for noise-like input.
  A sine exactly on the pitch builds up as 1/(1 − G), which is the auto-level's job.
- **Auto-level:** `env~ 1024 256` of the resonator output (control rate, so no DSP loop).
  - Above AGC_DB = 91 (−9 dB RMS), the excitation gain drops by 0.5 × the excess per 5.3 ms and comes back at
    +0.1 dB per period, with a floor of −40 dB.
  - It catches bowing, auto-repeat and matched input, and leaves single strikes alone. With the threshold at 88 it
    pulled down the strike that followed a loud ring.

## Controls
- **Pitch → P:** `(pitch − 0.6)·60` semitones, continuous (no rounding).
- **Routing:** st_res = P·(m≠2) + O·(m=2) and st_exc = P·(m≠1) + O·(m≠2). The exciter is clamped to 10 Hz–8 kHz.
- **Offset (alt Window):** stepped ±36, 0 over 0.46–0.54. `[change]` comes before `s rs_O`. The alt reset sends
  `set 0` to that `[change]` (`rs_Ochg`), so the knob's old step isn't blocked afterwards.
- **File:** the raw `filestate` level, primed.
  - Press: `v rs_held 0`, `delay 300`.
  - At 300 ms: held = 1, `rs_hold 1`.
  - Release: stop the delay. Held → `rs_hold 0`; not held → mode = (mode + 1) mod 3.
- **Auto-repeat (alt Density):** `[> 0.02] → [change]` starts or stops the metro, so the ~1 ms alt stream doesn't
  keep restarting it. The period is `1000 / (0.25·64^((k − 0.02)/0.98))` ms.
- **Alt reset:** as 07_shimmer: `rs_altrb` re-arms the pickups, then `ALT_RESET`, including `rs_mode 0`.

## Control-rate expressions
Vanilla Pd has no `expr`, so `resonator.py` has a small compiler:
- `E` trees (`V(name)`, constants, `+ − × /`, `min max == != >`, `sin cos atan exp log sqrt abs`) become chains of
  plain objects.
- A binary op with two non-constant operands gets a `[t b b]`. The right operand is evaluated first, into the cold
  inlet.
- `program(c, x, y, src, [(targets, E), ...])` runs the assignments in order on each bang. Targets are
  `s:name` / `v:name`.
- `watched(names, assigns)` re-runs a program whenever any `[r name]` changes; the values are in `[v name_v]`.
- Re-evaluating whole trees costs objects, but each program runs only on a change. The tune program is about 300
  objects.

## BBD delay
- **Time:** dt = 20·100^speed ms, a `line~` over 150 ms, so time changes bend the pitch.
- **Wobble:** `osc~` at 0.3/0.369 Hz (R phase ½), depth `(1 − tone)²·1.5 ms`.
- **In the loop:** tone `lop~` (1.5–16 kHz), `hip~ 60`, the L↔R cross by pp, softclip, × eg (Overlap·1.1).
- **Ping-pong pp (pitch_alt):** feeds the mono sum into L only and crosses the feedback.
- **Hold (File held):** eg = 1, input 0, tone 1e5, hip~ 0 (passthrough), no wobble.
  - Repeats measured flat (0.128 peak) for 3 s; they decay again on release.
  - Without the open tone and the hip bypass, a held loop drains (07's lesson).

## Tests (`python tools/gen.py --wav DIR` → `DIR/r_*.pd`; analysis with numpy, see below)
| Test | Checks | Result |
|---|---|---|
| tune / tunemid | 8 pitches 92 Hz–2.49 kHz (incl. CV past the knob), FFT peak | 0.00 c, L and R |
| tunedark | Window CCW, measured in the first 100 ms | −0.8 … −1.0 c |
| tuneinv | inverted, Window noon | 0.00 c up to 1046 Hz. 1760/2489 clamp to 1300.0 Hz |
| decay | T60 at Size 0.3 and 0.6, at 261 Hz, 92 Hz and Window noon | 0.341 s / 2.32 s (targets 0.34 / 2.33) |
| shapes | each material | peaks 0.34–0.57; saw/square edges are the only sample jumps |
| ext | matched sine and noise on the audio input, Size 0.3 / 1 | −7 … −19 dB RMS, peak ≤ 0.75 |
| freeze | hold 18 s, a strike during it | ±0.3 dB, strike shut out |
| delay | 200 ms echoes, feedback 0.55, File-held hold | −5.4 dB per echo; hold flat |
| repeat | alt Density stream to 0.5 | strikes about 1.9 Hz, stop when CCW |
| route | prints: modes, long press, offset, alt reset | as the routing table; long press = hold only |
| jump | octave jump with the gate (CV 1 ms before) | old note stays 261.626 Hz under the new 523.25 |
| settle | firmware-style ramp at the gate; steady; no stream | 14 ms (521.3 Hz); 3 ms; 3 ms |
| bend | Pitch moved while Freeze holds | held note moves to 369.99 Hz (40 ms late) |
| runaway | everything max, 16 Hz repeat, invert, freeze, 60 s | peak 0.75, −6.3 dB RMS, no NaN |
| runext | sine 0.9 + noise on the input, Size 1, feedback 1.1 | peak 0.80, −8.4 dB RMS |

- **CPU proxy:** a 60 s render takes 2.6 s with one voice, against 2.9 s for 07_shimmer's runaway. The second voice
  adds about 15–20 % (0.84–1.2 s against 0.74–1.0 s in back-to-back runs).
- **Analysis:** pitch is the FFT peak with zero padding and parabolic interpolation; T60 is a single-bin DFT
  envelope with a fitted slope. `wavcheck.py freq` (zero crossings, 25 Hz resolution) is too coarse for cents.

## Ideas not done
- `block~ 32` if the Pi struggles (top 1.3 kHz, or 650 Hz inverted).
- Velocity: a CV-gated strike level (Start's CV jack as an accent).
- A per-strike pitch latch (sample V/oct at the gate) for sequencers with slow CV.
