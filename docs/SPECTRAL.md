# 05_spectral — design notes

"Spectral Clouds+": a Nebulae instrument after the owner's **WorkshopSpectral**, the Workshop Computer port of Julius
Kammerl's Spectral Clouds (github `uglifruit/WorkshopSpectral`, `spectral.cpp`/`tape.h`).
- Builder: `tools/spectral.py`.
- User guide: `patches/05_spectral_README.md`.

As with 04_glitch, the aim is the same philosophy, not a port. The core is kept: random log-band gains, the
probability threshold scaled by the gains' spread, smoothing in τ, texture, normal + sealed freeze, re-roll, and
tape. The RP2040 limits are dropped: FFT 2048, true stereo. Four ideas are new: pitch, drift, gather and re-capture.

## Control map

| Nebulae | WorkshopSpectral | Here |
|---|---|---|
| density | Main (PROBABILITY) | `sp_hp` = 0.5 − p; threshold = mean + sp_hp·spread |
| size | X (BANDS) | n = 4·32^size (4..128), smoothed per tick like `smoothed_bands_` |
| window | Y (SMOOTHING) | < 0.1 snap, else τ = 50 ms·60^t, `sp_lp` = exp(−1/(τ·93.75)) |
| overlap | page 2 Main (TEXTURE) | ±0.5·overlap turns of `noise~` per bin, per side, not accumulated |
| start | page 2 X (RE-ROLL) | < 0.1 off, else mean interval 3 s → 1 frame, as a per-tick probability (`sp_rr`/1e6) |
| Reset | Pulse In 1 | re-roll (primed press) |
| Freeze latch | switch Down | freeze |
| Source latch | hold Down 2 s (sealed) | sealed |
| Record latch | — | gather |
| filestate | — | re-capture (`sp_cap` for 25 ms ≥ 2 hops) |
| pitch | — | semis = 60p − 36, ±0.05 dead zone; `sp_ir` = 1/r, `sp_r4` = r/4 |
| speed | — | drift `sp_du` = −(16/93.75)·d·\|d\| per tick, d = speed − 0.5 (click ±0.25 cycles/s) |
| blend | (mix externally) | dry/wet, dry delayed by the STFT latency |
| alt start / size | — | spread / gather decay (−60 dB in 60^a s) |
| alt window / overlap / density / blend | tape page 2 | tape time 25·80^a ms, feedback 0.85a, wow, mix |

Alt values pass through `pickup()`, a single-destination copy of `gloop.takeover`:
- a value is applied only after it moves 0.02 from the first value of its stream;
- after 150 ms of silence, the next value starts a new stream;
- a jump over 0.2 (the alt-reset click) re-baselines instead of applying.

## Engine

**STFT:**
- `[pd stft]`, `block~ 2048 4`: hop 512, 93.75 frames/s.
- Sine window on analysis and synthesis; the gain is 1/(2N), since the sum of w² at overlap 4 is 2.
- **Measured latency: N − 64 = 1984 samples (41.33 ms).** That is the reblocking latency, block size minus the
  parent's 64. `LAT_MS` delays the dry by exactly this, and blend 0.5 of a sine stays at 0.500.

**DSP order** within the frame is forced with dummy signal links: ana → pool1 → … → pool4 → syn (HANDOFF §6). Tables
written with `tabsend~` are therefore read by `tabread~` in the same frame. `tabreceive~` of the same table reads the
previous frame, which is how the write-back stores and accumulators work.

### ana (per side)
- **Magnitude:** `sqrt~(re² + im²)` × `sp_nz` (0 at DC and above Nyquist).
- **Phase (turns):**
  - The original's `RectToPolar` cubic, a = r(0.9724 − 0.1919r²)/2π with r = min/max (`abs~`, `min~`, `max~`,
    `/~`).
  - Then three reflections with steps `clip~(x·1e30, 0, 1)`, because old vanilla has no `atan2~` and no `>~`.
  - Max error 0.005 rad.
- **True frequency:**
  - F = k + 4·(wrap(Δphase − frac(k/4) + 8.5) − 0.5) bins.
  - The previous phase comes from `sp_php`.
- **Store `sp_M0`, `sp_F0`, `sp_P0`** (write-back), with sel = step(m − M·d):
  - newM = g ? max(M·d, m) : (frozen ? M : m);
  - F follows the same choice (sel when gathering);
  - d = `sp_deff` = max(decay, freeze): no decay while frozen.
- **Source phase P:**
  - live = g ? sel : nfz;
  - P = p + (1 − live)·hold·(P + F/4 − p), with hold = max(seal, gather) (`sp_hold`). Bins that took the live
    frame use the live phase. Held bins advance at their stored F when sealed **or gathering**, and use the live
    phase only in a plain normal freeze.
  - The first hardware test caught a bug here: hold was seal only. Gather with Source off then gave held partials
    the phase of whatever unrelated live bin lay under them, so the gathered spectrum collapsed into a noise sweep
    as soon as the input changed (440 → 660 test: the held 440 fell 15 dB in 0.5 s and broadband energy rose
    50 dB). It now fades at the gather rate.
  - At r = 1 this is exactly the original's sealed freeze.
- **Centred storage:** P is stored as P − k/2 (`sp_hk` = frac(k/2)). A centred windowed partial's bins alternate in
  sign, so a phase moved to another bin must carry that (−1)^Δk. Without it, +12 st collapsed to −23 dB.

### pool1..4 (per side)
- Level ℓ = argmax of level ℓ−1 at i and i + 2^(ℓ−1), so it covers bins i … i + 2^ℓ − 1.
- It carries M, F, the centred P, and the source bin J (level 0's J is `sp_k`).
- Each level has a `switch~` driven by `sp_pool<ℓ>` = pitched AND `sp_lvl` ≥ ℓ, so unpitched runs no pools.
  This saves about 40% CPU.

### syn (per side)
- **Unpitched:** magnitude `sp_M0`, phase `sp_P0` + k/2, i.e. the store as is. Calibration (`sp_flat 1`) is an exact
  passthrough: 0.500 in → 0.500 out, no clicks.
- **Pitched — peak-locked resynthesis** (`[pd pitched_L/R]`, `switch~`ed off while unpitched; syn blends its
  outlets by `sp_pitched`, so stale outlets don't matter):
  - Bin k reads the level-ℓ pool at k/r − off, with ℓ = clip(⌈1 − semis/12⌉, 1, 4) and off = 2^(ℓ−1) − 0.5. The
    2^ℓ ≥ 2/r window is centred on k/r, so no partial is missed down to −36 st.
  - That gives the loudest nearby bin J with M, F and P.
  - Magnitude = M·W(k − rF)/max(W(J − F), 0.5). `sp_W` is the sine-window kernel |cos πδ/(1 − 4δ²)|, main lobe
    only, sampled at 1/64 bin (cell midpoints). So each partial is redrawn with the right lobe at its new place.
  - Phase = J's centred P + k/2 while reseeding (`sp_rs`), else the accumulator `sp_A` + r·F/4.
  - All bins of a partial share one centred phase, which is exact for a symmetric window, and advance at the same
    rate.
  - The reseed fires 40 ms after the last Pitch change (`sp_cpz` = pitched·(1 − rs)).
- **Band mask:** `sp_eff[n·wrap(sp_L + u)]`. `sp_L` = log(k/8)/log(128) (0 below bin 9), so continuous band counts
  and drift come free, with no per-count layout rebuild.
- **De-click:** each bin's gate eases toward its new value, mask += 0.35·(target − mask) per frame (`sp_mkL/R`,
  `DECLICK`): about 95% in 7 frames (75 ms). A gate otherwise switches within one hop, and on sustained tones
  drift, re-rolls and threshold wobble then tick. On a sine with drift, 5 ms envelope steps over 10% of peak fell
  from 66 to 12 in 8.5 s; with typical settings, from 8 to 0.
- **Texture:** `cos~` → `rifft~` → window → 1/(2N).

### bands (control rate)
- `metro 10.667` = one tick per hop. The init tick snaps the states to their targets.
- **Per tick:**
  1. maybe re-roll (128 new targets per side, `random` seeded via `sp_seed`);
  2. lp = the smoothing coefficient;
  3. smooth n and advance the drift u;
  4. one 128-band `until` pass.
- **The pass:**
  - s = t + (s − t)·lp for L and R;
  - running sum and Σ|s − mean_prev|;
  - gates written to `sp_effL`/`sp_effR` (√2·s if s ≥ thr, else 0). R's gate uses (1 − spread)·sL + spread·sR.
- **After the pass:** mean, spread = clip(4.33·MAD, 1/32, 1), thr = mean + (0.5 − p)·spread for the next tick. This
  is the original's arithmetic, one tick late, so there is no second pass.

### Post
- **Tape** is `tape.h` in Pd: `vd~` with two-LFO wow (±5 ms at full), `lop~ 3000`, `hip~ 30`, a cubic soft clip
  (unity small-signal gain) and feedback ≤ 0.85. Out = in + mix·delayed.
- **Output** = dry·(1 − blend) + wet·blend, then a soft clip: linear to 0.7, then c + e·0.3/(0.3 + |e|), never
  pinning (as `SoftClipOut`).

## Measurements (offline, `python tools/gen.py --wav DIR`, then `pd -batch`)
| Test | Result |
|---|---|
| calib (`sp_flat`) | 440 Hz 0.500 → 0.500, 0 clicks; blend 0.5 = 0.500 (dry aligned) |
| freeze | normal freeze + input muted: rms 0.33 → 0.11 (−9.6 dB, the original measured ≈ −10). Sealed + muted: holds 0.27–0.30 |
| pitch sweep (sealed 440 Hz, −36…+24) | every step within FFT resolution of 440·2^(s/12); level −0.1…+0.0 dB; non-partial energy −23…−51 dB |
| pitch (live +7) | 659 Hz, level 0.350 vs 0.354 |
| gather | 440 held + 660 added; after the input stops it decays ~7.6 dB/s (alt-size default: −60 dB in 7.7 s); Freeze stops the decay |
| re-capture | frozen 440 → File → 660, no clicks |
| drift (Speed click) | the band pattern cycles back to its start after 4 s; Speed 0.5 = static |
| spread (alt start 0 → 1) | L/R correlation 1.000 → 0.36–0.62 |
| tape | echoes every 224 ms (default), 0.50 / 0.20 / 0.09 / 0.04 |
| CPU (desktop, 60 s stereo) | unpitched 2.3 s (was 2.7 s before the pitched path got its `switch~`), pitched up 3.0–3.4 s, −36 st 4.3–4.5 s |

**Hardware risk:** the whole STFT runs in one of every 8 DSP ticks. Scaling the desktop figures by an estimated 4× for
the Pi 4 gives a burst of about 1.7 ms per hop unpitched and about 3.3 ms at −36, against the module's
`-audiobuf 5`. Clicks on hardware that stay with a static spectrum (density fully CW, start CCW, Speed centre,
Pitch on its click) point to this. If it crackles on hardware, set `N = 1024` in `tools/spectral.py`: everything else derives from N,
and it halves the burst.

## Tests
`tools/gen.py` writes `sim/test_05_<name>.pd` for each scenario: calib, bands, freeze, pitch, gather, tape, drift,
recapture. `--wav DIR` also writes `DIR/s_<name>.pd` → `.wav`.

The test source (`[pd testsrc]`) gives:
- `sp_tsin` + `sp_tfreq`: sine;
- `sp_tchd`: four-saw chord;
- `sp_tnse`: noise;
- `sp_tblip`: 30 ms blip;
- `sp_tclk 1`: Reset every 500 ms.

Check with `tools/wavcheck.py`: `spec` (rms, peaks, octave-band dB, needs numpy), `freq`, `clicks`, `beats`.
