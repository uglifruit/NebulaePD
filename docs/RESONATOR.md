# 08_resonator — design

Builder: `tools/resonator.py` (prefix `rs_`). User guide: `patches/08_resonator_README.md`.

Goal: a Morphor ECHON-style instrument (exciter → BBD delay-line resonator per voice) plus a BBD-style echo after
it. The owner's choices were:
- an internal exciter struck by Reset, with Source swapping in the audio input;
- **4 voices** (2026-11-10), oldest-note stealing, each note holding the pitch it was struck at. Per the owner's
  picks: 4 mono voices panned (alt Size = width), an exciter per voice, the audio input into all 4 voices, and the
  pitch latched at the strike plus a 10 ms catch. (v1 was one stereo voice with L/R spread.);
- a BBD-style stereo delay, with free time on Speed;
- three V/oct routing modes on a short File press, where the fixed side sits at C4 + the stepped offset.

## Signal flow
```
[exciter] per voice k: wrap~(t f_k) (t: vline~ from the strike) -> 6 shapes x weights -> x env_k^2 x kf_k x EXC
          | or mono adc~ x icx_k (Source) -> hip~ 20 -> lop~ x2 (alt Start) -> x nf (freeze) x agc_k -> outlet k
[res]     block~ 16, per voice: w = x + softclip(g_k * mute_k * hip~1(lop~ damp_k(vd~ D_k))) -> delwrite~ ;
          out_k = (x(1-bal) + read*mute_k*bal) * VOICE_G, panned (pl_k, pr_k) -> summed L / R
[bbd]     per side: in*ein (+ping-pong) + softclip(eg * cross(hip~(lop~ tone(vd~ dt + wobble)))) -> delwrite~ 2100
out       = softclip(res * gd + bbd * gw) -> dac~
```

## Voices (2026-11-10)
- **Allocation:** `rs_go` (a strike, or the auto-repeat metro) advances `rs_av` = (av + 1) mod 4. Taking the voices in
  turn always lands on the oldest note, which is oldest-note stealing.
- **Pitch latch:** live pitches `rs_fr` (resonator) and `rs_fexc` (exciter) are computed as before, but they reach
  a voice (`rs_frk<k>` / `rs_fek<k>`) only through its catch spigot (`rs_cat<k>`).
  - At a strike the voice's spigot opens alone, the current values are pushed to it, and `[delay CATCH_MS]` (10 ms)
    closes every spigot.
  - After that, Pitch, the offset and the V/oct mode reach only new notes.
  - The catch is for a CV that lands one poll pass after the gate. The pass is 5.3 ms measured, 4–8 ms range. With
    uf1's 0.95 Pitch coefficient a jump settles within a pass (expected; the uf1 capture is pending).
- **Per-voice programs:** `voice_assigns(k)` computes damping, gain, D, `kf` and `icx` from the voice's own pitch.
  Size, Window, Invert, Freeze and Density reach every voice.
- **Steal:**
  - At a strike, `rs_mute<k>` (`vline~`) goes "0 in 0.5 ms, back to 1 in 0.25 ms at D + 0.5". It gates both the read
    output and the feedback.
  - Everything written before the mute leaves the line within D (the new period). During that time it is neither
    recirculated nor heard, so the stolen note is gone completely. The poly test measured C4 at 0.0003 after its
    steal, against 340–1700 for the other notes.
  - The strike waits STRIKE_LAG = 0.75 ms, so all of its excitation lands while the loop is open. In the first try
    the strike started with the mute, which ate its first 1.5 ms (the envelope peak): low plucks were 3× too quiet.
- **Sample-accurate exciter phase:** `wrap~(t·f)`, where t comes from a `vline~` ramp started at the strike.
  - A `phasor~` phase reset only takes effect at the next 64-sample block. A pluck shorter than one period then
    caught a different part of the wave depending on where the strike fell in the block.
  - Measured with STRIKE_LAG 0.75/1.5/2.5/3.5/5 ms: 92 Hz pluck peaks of 0.11/0.27/0.32/0.17/0.36 with `phasor~`,
    against 0.338–0.358 with `wrap~(t·f)`. v1 had the same effect, unnoticed.
- **Auto-level per voice:** `env~` of each voice's own output drives its own excitation gain, and is reset to 0 dB at
  its strike. One shared AGC on the sum pushed every new note down to −40 dB under a loud chord (steal test: −8 →
  −37 dB). AGC_DB = 85 (−15 dB RMS per voice).
- **Pan:** θ_k = (1 + PAN_k·width)·π/4, with PAN = −1, 1, −⅓, ⅓, and gains √2·(cos θ, sin θ). The centre is unity
  per side, as v1's mono output was. Tests run at width 0.

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
- (v1's L/R spread is gone: voices are mono and panned.)

## Exciter
- **Shapes:** sine `cos~(φ + 0.75)`, tri, saw, square (`spectral.step`), `noise~`, and `samphold~` noise
  clocked by the phasor wrap. Weights are `w_k = max(0, 1 − |5·start − k|)`. Gains are
  SHAPE_K = 0.85/1/1/0.6/2/3, because noise builds up less in a resonator than a tone at its pitch does.
- **Envelope:** `vline~` "1 A, 0 Dc A", squared. A = 0.5·3000^d ms and Dc = 5·600^d ms. The phase restarts
  sample-accurately at each strike (see Voices), so plucks are repeatable.
- **Level:** `kf = (1 + f_res·(A + Dc/2)/1000)^−0.75`. A strike spanning N periods of a matched tone builds up by
  about N^0.85. Measured pluck peaks are 0.30–0.71 from 92 Hz to 2.5 kHz.
- **Audio input:** `icx = min(1, KX·√(1 − G))`, with G = g·|H| and KX = 1. That's right for noise-like input.
  A sine exactly on the pitch builds up as 1/(1 − G), which is the auto-level's job.
- **Auto-level:** per voice, `env~ 1024 256` of that voice's output (control rate, so no DSP loop).
  - Above AGC_DB = 85 (−15 dB RMS), the voice's excitation gain drops by 0.5 × the excess per 5.3 ms and comes back
    at +0.1 dB per period, with a floor of −40 dB. It resets to 0 dB at each strike of that voice.
  - It catches bowing, auto-repeat and audio input, and leaves single strikes alone (a pluck's excitation is over
    before `env~` reports).

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
| shapes | each material | peaks 0.31–0.45 (S&H 0.15); saw/square edges are the only sample jumps |
| ext | matched sine and noise on the audio input, Size 0.3 / 1 (4 voices all on C4: the worst case) | −2.6 … −15 dB RMS, peaks ≤ 0.95 (soft clip) |
| freeze | hold 18 s, a strike during it | ±0.3 dB, strike shut out |
| delay | 200 ms echoes, feedback 0.55, File-held hold | −5.4 dB per echo; hold flat |
| repeat | alt Density stream to 0.5 | strikes about 1.9 Hz, stop when CCW |
| route | prints: modes, long press, offset, alt reset | as the routing table; long press = hold only |
| runaway | everything max, 16 Hz repeat, invert, freeze, 60 s | peak 0.74, −6.5 dB RMS, no NaN |
| runext | sine 0.9 + noise on the input, Size 1, feedback 1.1 | peak 0.92, −8.9 dB RMS (4 voices) |
| poly | C4 E4 G4 B4, then D5 steals C4; Pitch moved with no strike | all 4 ring; C4 gone (0.0003); every note exact (329.628/391.996/493.883/587.329) |
| catch | Pitch 5 ms after the gate; Pitch 25 ms after a gate | note = E4; note stays G4 (no 740 Hz) |
| steal | 12 strikes 150 ms apart at Size 1 (8 steal ringing notes) | level holds −5 … −8 dB; no click at any steal (2nd-difference vs local median) |
| width | width 1, three notes | L/R: −22/−240, −33/−20, −19/−23 dB |

- **CPU proxy** (back to back, 60 s runaway): 4 voices 2.4–2.9 s, v1 1.4 s, 07_shimmer 2.7–2.9 s.
- **Analysis:** pitch is the FFT peak with zero padding and parabolic interpolation; T60 is a single-bin DFT
  envelope with a fitted slope. `wavcheck.py freq` (zero crossings, 25 Hz resolution) is too coarse for cents.

## Ideas not done
- `block~ 32` if the Pi struggles (top 1.3 kHz, or 650 Hz inverted).
- Velocity: a CV-gated strike level (Start's CV jack as an accent).
- Glide/legato mode (a held voice following Pitch), if wanted: the latch makes every note fixed.
- Earlier attempt, reverted (41ec4be/daebe62): two voices, a settle-wait and a 40 ms pitch lag, built on a guessed
  1 ms poll rate.
