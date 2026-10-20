# 07_shimmer — design

Builder: `tools/shimmer.py` (prefix `sh_`). User guide: `patches/07_shimmer_README.md`.

Goal: a Strymon BigSky/blueSky-style shimmer (owner's reference). The sources were the SoS shimmer article (an
octave shifter feeding a long, bright hall, an optional chorus, swell, octave plus sub-octave) and the Aulart/Ableton
article (the shift inside the feedback loop for a cascade, with detune for "cloudiness").

## Signal flow
```
adc~ -> [swell] -> [reverb: hip~ lowcut -> pre-delay vd~ -> (+T) -> 4 allpasses -> FDN 8 (+ shifter on lines 0/1)]
     -> [chorus] -> * (gw * clearw * duck) -> + adc~ * gd -> softclip -> dac~
adc~ -> [duck] (envelope of the dry input -> wet gain signal)
```
- The tank and the shifter loop live in **one canvas** (`[pd reverb]`). A subpatch is sorted as a unit, so a loop
  between subpatches would be a DSP loop error, and send~/receive~ adds a block.
- **Tank:** 8 `vd~` lines. TANK_MS = 41.1 … 113.9 ms × room scale (`sh_scale`, line~ over 300 ms), each with an
  `osc~` modulation (rate `sh_mrate × MODK[i]`, phase i/8, depth `sh_mdep` ms). After each read come
  `lop~` (`sh_damp`), `*~ g_i`, a 3-stage Hadamard butterfly, the injection, `softclip`, and `delwrite~`.
  - `g_i = max(exp(−6.9078 L_i scale / RT), frz) · clr / √8`, computed at control rate in `[pd ui]`. Measured RT60
    is 1.35 s against 1.4 s, and 4.55 s against 4.9 s.
  - Damping: `fc = 7640 (0.2 + 0.8 √window)`. At 7640 Hz Pd's one-pole coefficient reaches 1, so Window CW and
    Freeze (`1e5`) are exactly undamped.
- **Diffuser:** 4 Schroeder allpasses per side (4.77/3.6/12.7/9.3 ms; g 0.75/0.75/0.625/0.625; R ×1.07). The
  diffused L feeds lines 0, 2, 4, 6 and R feeds 1, 3, 5, 7. The output is `OUTG × (sum of the 4 reads per side)`
  plus `ER × the diffused input`, a direct term. Without it the wet starts only after the shortest line (about 35–40
  ms), which sounds like pre-delay at Start 0 (hardware report, 2026-10-21). With it the onset is 2 ms.
- **Loop shimmer (Source off):** lines 0/1 keep `cos θ` of their feedback. The shifter takes the line's damped read
  `z`. The shifted signal `T` (A·gA + B·gB → `lop~ sh_stone` → `hip~ sh_lc`) is added to the diffuser input at
  `√2 · sin θ · g_s`, which reaches 4 lines at 0.5 each. The energy taken out equals at most the energy put back, so
  the loop gain never exceeds the reverb's own. θ = density · π/2 · (1 − frz).
- **Pre shimmer (Source on):** the shifter takes the pre-delayed input, and the diffuser gets
  `GIN · (cos φ · x + sin φ · T)` with φ = density (radians). There is no cascade.
- The routing gains (`cL sL cP sP selz selx`) are line~ ramps over 50 ms, so switching mode is click-free.
- **Shifter:** a 2-tap rotating delay with W = 80 ms. The phasor runs at `(1 − 2^(st/12)) · 1000/W`. The taps sit at
  `p·W + 1.5` and `wrap(p + ½)·W + 1.5` ms, with gains `½ ∓ ½ cos~(p)`. Voices A and B share one delwrite~ per
  side. Detune: A L/R = stA ± det, B L/R = stB ∓ det.
  - **No makeup gain.** For uncorrelated taps the power is 0.75, but a steady tone at multiples of 2000/W = 25 Hz
    adds coherently. With 1/√0.75 makeup that gives gain 1.33, and octave cascades stay on the 25 Hz comb. This was
    seen offline: the Voice B tail grew between 2.4 s and 5.4 s. With makeup 1 the pass power is 0.5…1.
- **Freeze:** the input is muted (`nfc = (1 − frz) · clr`), g = 1, damping is off, and the loop shimmer is paused.
  With shimmer running, a frozen tail drained −37 dB in 20 s, because each pass pushes energy up past the shimmer
  LP. With the shimmer paused it holds within 1 dB for 20 s.
- **Clear (Reset):** the wet gain goes to 0 over 10 ms. 10 ms later `clr = 0` (feedback and input zero). After
  FLUSH = 360 ms (longer than the longest line plus the shifter) `clr = 1`, and the wet gain returns over 20 ms.
- **Chorus:** 3 `vd~` voices per side (8/12/17 ms, rates `sh_mrate × 0.9/1.23/0.71`, R phases +½). It outputs
  `in·n + Σ/√3 · 0.7c·n`, with c = max(0, 2·overlap − 1) and n = 1/√(1 + 0.49c²). The tank depth is
  min(1, 2·overlap) · 1.5 ms · k and the chorus depth is 2.5 ms · k, with k = min(1, 1/rate).
- **Duck:** `env~ 1024 512` of the dry input → `1 − dk · min(1, 4 rms)`, where dk = 1 − 10^(−24·amt/20). The gain
  falls over 15 ms and recovers over 350 ms.
- **Swell:** `env~` hysteresis: an onset is above 55 dB, quiet is below 50 dB for 150 ms. An onset ramps the input
  gain to 1 over 1000 ms; quiet drops it to 0 over 80 ms. Enabling the swell arms it at 0 and sends `set 0` to the
  `[change]`, so input that is already playing counts as an onset.
- **Speed → Voice B:** zone code 0 = off (0.36–0.64). Codes 1–3 = (0.36 − s)/0.12 → −5, −12, −24. Codes 4–8 =
  (s − 0.64)/0.072 → +5, +7, +12, +19, +24. `[change]` sits before the sends.
- **Alt knobs** use `spectral.pickup()`. pitch_alt (detune) is applied directly, since it's an accumulator.
- **Alt reset (Source + Record):** `record_alt` toggles once per press (as in 03_gloop's alt clear). A primed press
  first bangs `sh_altrb`, which is pickup()'s `rebase` hook: it closes every spigot and re-baselines. Only then does
  it send `ALT_RESET`, the same values the patch loads with. The order matters: while Source is held each alt knob
  streams about every millisecond, so an open pickup would overwrite the reset at once. This was checked with a
  scratch run that streamed values every 10 ms: the values hold until the knob moves again, then pick up from the
  knob.

## Old-Pd notes
- There are no `!-` or `!/` objects in vanilla (they come from Max). Use `* -1, + a` and `pow -1`.
- Every float-controlled gain is a `line~` signal. `lop~`/`hip~` cutoffs are floats.
- The shortest feedback delay (an allpass at 3.6 ms) is longer than one 64-sample block.

## Tests (`python tools/gen.py --wav DIR` → `DIR/h_*.pd`)
| Test | Checks | Result |
|---|---|---|
| decay | RT60 vs Size (noise bursts) | 1.35 s (target 1.4), 4.55 s (target 4.9) |
| loop | 440 Hz burst → 880/1760/3520 build | cascade present; with shimmer, RT ≈ 5.2 s at the 8.1 s setting |
| pre | single layer | 880 Hz at −12 dB, no 1760 band |
| voiceb | Speed 0.2 = −12 | 220 Hz and 110 Hz present, monotonic decay |
| freeze / freezesh | hold, input shut out | flat within 1 dB over 20 s (both) |
| runaway | everything at max + sine + freeze | −11 to −14 dB RMS for 60 s, peak 0.93, no NaN |
| clear | Reset on a long tail | silent within 0.1 s, the next burst is fine, 0 clicks |
| duck | sine under full duck | wet −31 dB while playing, −13 dB once it stops |
| swell | Record on, sine onset | the wet rises over about 1.2 s |

CPU proxy: 60 s stereo renders in 2.3 s, about the same as 05_spectral unpitched.

## Ideas not done
- `switch~` off the chorus and Voice B when unused (if the Pi struggles).
- Smoother shifter: a longer window, or 3–4 overlapping taps.
- Reverse / bloom reverb modes, and a clocked pre-delay.
