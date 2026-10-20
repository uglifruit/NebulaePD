# 06_topo — design notes

A clocked drum-pattern generator (Grids-style topographic map, our own data) with a built-in FM drum synth. The
builder is `tools/topo.py`; the user guide is `patches/06_topo_README.md`. Send prefix `tp_`.

## Control map

| Nebulae | 06_topo | Send |
|---|---|---|
| Reset jack/button | clock: one 16th step per pulse | `tp_clock` |
| `sourcegate` (Source gate jack; button-independent trigger) | back to step 1: the next clock plays step 0 | `tp_rst` |
| Source latch | ignored: the Source gate jack also toggles it | — |
| Freeze latch | lock: no auto-mutation, no drift | `tp_lock` |
| Record latch, any change after priming | mutate burst: `4 + round(12·window)` mutations | `tp_mutnow` |
| `filestate` | press < 1 s = recall home; held 1 s = store home (fires at 1 s) | `tp_recall` / `tp_store` |
| start / size | map X / Y (+ drift, folded into 0..1) | `[pd pos]` |
| density | fill | `tp_fill` |
| overlap | chaos: level += (random 511 − 255)·overlap·0.5 per step | `tp_chaos` |
| window | auto-mutations per cycle `round(12·w²)`; 0 below 0.05 | `tp_namt` |
| blend | Sound: position `7·blend` → anchor `a = clip(int, 0, 6)`, fraction | `[v tp_sa]`, `tp_sfr` |
| speed | drift rate `3e-5·r²` per step, `r = clip((abs(speed − 0.5) − 0.13)/0.37)`: zero between the clicks | `tp_drate` |
| pitch | tune ratio `2^((pitch·60 − 36)/12)`, latched per hit | `tp_tune` |
| start/size/density/overlap_alt | lane fill offsets `v − 0.5` (K, S, H, P) | `tp_fo0..3` |
| window_alt | length `1 + round(31·v)` | `tp_len` |
| blend_alt | decay ×`exp((v − 0.5)·2·ln 4)` (0.25..4) | `tp_decay` |
| pitch_alt | swing `clip(10·pitch_alt)`; applied directly (no pickup), so the alt-reset click (→ 0) clears it | `tp_swing` |

The alt knobs use `spectral.pickup()`. Note that its jump guard compares against the stream-start baseline, so after
0.2 of travel it re-baselines and needs another 0.02 to reopen. Real knobs stream ~0.001 steps, so the effect is
small, but tests must sweep in small steps (see `topo_groove_test`).

## Tables

| Table | Size | Index | Content |
|---|---|---|---|
| `tp_map` | 3200 | `(y·5 + x)·128 + lane·32 + step` | node levels 0..252 (digit × 28), loaded at loadbang |
| `tp_off` | 128 | `lane·32 + step` | mutation offsets added to the interpolated map |
| `tp_home` | 128 | same | stored offsets (+ `[v tp_hdx/hdy]` drift) |
| `tp_snd` | 480 | `(voice·10 + param)·8 + anchor` | kit anchors; f, ratio, ncut as log2 |
| `tp_thrt` | 4 | lane | current thresholds (for the mutation flip) |

## Map (`NODES`)

25 nodes × 4 lanes (K, S, H, P) × 32 steps, written as digit strings (`.` = 0; `every()`/`merge()` build the
polyrhythmic column).
- X columns: four-on-the-floor, electro/funk, hip-hop, breakbeat/jungle, broken/polyrhythmic.
- Y rows: sparse → busy.
- Hierarchy rule: backbone 8–9, mid 5–7, ghosts 1–4, so the lowest Fill keeps the core.
- S 9 = snare + clap; H 9 = open hat (`ACCENT = 230`; 9 × 28 = 252).

## Engine

- **`[pd pos]`:** X = fold(start + dx) into 0..1, then ×4 → `ix = clip(int, 0, 3)`, `fx`; the same for Y. The weights
  `tp_w0..3 = (1−fx)(1−fy), fx(1−fy), (1−fx)fy, fx·fy` and `tp_nb = (5·iy + ix)·128` are recomputed on every
  change.
- **`[pd mapq]`:** `[s tp_q] lane·32+step` → four `tabread tp_map` at `nb + {0, 128, 640, 768}`, weighted and summed
  → `[v tp_qr]`. Synchronous (depth-first), so a caller sends `tp_q` and then reads `tp_qr`.
- **`[pd thr]`:** `thr_L = 255.001 − 255·clip(fill + fo_L)` → `[v tp_thrL]` and `tp_thrt`. At fill 0 nothing can
  reach it (levels are clipped to 255), so Fill 0 = silence even with chaos.
- **`[pd steps]`:** the clock trigger fires right to left:
  1. the period (`timer`, gaps > 2 s ignored) → `tp_swd = 0.4·swing·period`;
  2. advance: step = 0 if `tp_rflag` (reset or load), else `(step + 1) mod len`. Step 0 → `tp_cycle` (auto-mutate);
     then `tp_drift`;
  3. schedule: `[delay (step mod 2)·tp_swd]` → `tp_pst` → per lane:
     `lvl = clip(clip(qr + off) + chaos·(rnd − 255), 0, 255)`; hit if `lvl ≥ thr`; velocity `0.35 + 0.65·lvl/255`.
     S hit with `lvl ≥ ACCENT` → clap too; H hit with `lvl ≥ ACCENT` → OH, else CH.
- **`[pd mutate]`:** a mutation picks lane `mL = 32·rnd(4)`, step `ms = rnd(len)`, kind `rnd(10)`:
  - **0–4, move:** neighbour `n = (ms + d) mod len`, `d ∈ {−2, −1, 1, 2}`. If exactly one of the two steps plays
    (`level ≥ thr`), swap their levels by writing both offsets; otherwise **flip** step 1 (so moves are never
    silent no-ops).
  - **5–7, flip:** silent → `thr + u·(255 − thr)`; playing → `0.9·u·thr`.
  - **8–9, heal:** offset 0.
  - Before the flip/move fix, a 4-mutation burst was often inaudible (moves between two silent steps); see the
    test notes.
- **Drift:** per step, unless locked: `dx += (rnd(2001) − 1000)·tp_drate`, clipped ±0.5 (also dy).
- **Home:** `[until]` copies `tp_off ↔ tp_home` + the drift position.
- **Randomness:** `glitch.rnd()` instances seeded from the time to the first clock.

### Voices (`[pd voices]`)

- **Parameters (10)**, read at each hit from `tp_snd` with `lerp(anchor a, a+1, frac)`:
  - f (log2 Hz, × tune), ratio (log2), index (rad → turns), idec ms;
  - sweep (octaves → `k = 2^s − 1`), stime ms, nmix;
  - ncut (log2 Hz), adec ms, ndec ms (decays × `tp_decay`).
  - Results go into `[v tp_<V>_*]`.
- **Round robin:** two halves per voice. The new hit chokes the other half (`0 3` on its amp/noise `vline~`), so the
  half that starts is silent and its phases reset click-free (carrier to 0.75 turns = a zero crossing of `cos~`).
- **Signal path:**
  - `fs = F + FK·penv²` (a linear-frequency sweep, since old vanilla may lack `pow~`/`exp~`);
  - `cos~(phasor~(fs) + I·ienv²·osc~(R·fs))`, × `aenv³` × TG·vel;
  - plus `noise~ → bp~ NC Q` × `nenv³` × NG·vel.
- Envelopes are linear `vline~` ramps, cubed.
- The clap's amp/noise envelope is three bursts 9 ms apart, then the tail.
- Post: `hip~` per voice (two poles on the hats), equal-power pans, then `*~ 0.8` → `spectral.softclip`.
- **Anchors:** anchor 0 = `KIT`. Anchors 1..7 are `random.Random(606)` deviations scaled `0.3 + 0.7·a/7` by `SPREAD`
  (multiplicative for times/index, log2 for f/ratio/ncut), clamped by the per-voice `LIMITS` so a kick stays a kick.

## Tests (`sim/test_06_*.pd`, scenarios in `tools/gen.py`)

The test build adds `[pd testclock]`:
- `tp_tclk 1` sends Reset pulses every `tp_tper` ms (125 = 16ths at 120 BPM);
- it prints `step: t n`, `cycle: t` and `hit_<V>: t vel` (t = ms since load).

Group the prints into cycles to compare patterns. Checked offline:

| Test | Result |
|---|---|
| voices | each voice; spectra: K 47 Hz fundamental, S 183 Hz + noise to 8 k, C ~1.1 kHz band, CH/OH 4–16 kHz; the OH is cut 150 ms after a CH. No NaN, no jumps > 0.05 on the kick except its attack |
| sound | same blend → same tone (the noise branch differs, as expected); blend 1 → K 74 Hz, different S/CH spectra |
| pattern | locked, chaos 0: cycles 1–3 identical (29 hits, house node); fill 0 → 0 hits; fill 1 → 56 hits |
| mutate | Record → the next cycle differs; File short → the plain map; File held 1.3 s stores; Record → differs; File short → the stored pattern; Window 1 → a new pattern each cycle; Freeze → repeats |
| groove | swing 1 → odd steps exactly 50 ms late at 125 ms; length 12 → 12-step cycles; Source gate → the next step is 0; Speed 1 → the pattern drifts; fill 0.15 + hats offset −0.18 → kick/snare only |

A 61 s render takes ~1.5 s on the desktop, about 3× lighter per second than 05_spectral.
