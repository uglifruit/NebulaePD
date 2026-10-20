# 06_topo — design notes

A clocked drum-pattern generator (Grids-style topographic map, our own data) with a built-in analog-model (808/909-style) drum synth. The
builder is `tools/topo.py`; the user guide is `patches/06_topo_README.md`. Send prefix `tp_`.

## Control map

| Nebulae | 06_topo | Send |
|---|---|---|
| Reset jack/button | clock: one 16th step per pulse | `tp_clock` |
| `sourcegate` (Source gate jack; button-independent trigger) | back to step 1: the next clock plays step 0 | `tp_rst` |
| Source latch | ignored: the Source gate jack also toggles it | — |
| Freeze latch | lock: no auto-mutation, no drift | `tp_lock` |
| Record latch, any change after priming | mutate burst: `4 + round(12·window)` mutations | `tp_mutnow` |
| `filestate` | press < 1 s = recall home; held 1 s = store home (fires at 1 s); two presses < 400 ms apart = vanilla (offsets 0, drift 0, home kept; the 2nd press closes the recall gate) | `tp_recall` / `tp_store` / `tp_vanilla` |
| start / size | map X / Y (+ drift, folded into 0..1) | `[pd pos]` |
| density | fill `clip((density − 0.04)/0.92)`: the bottom 4% is silent (a pot fully CCW reads ~0.01–0.03, and 9s play from fill 0.012) | `tp_fill` |
| overlap | chaos: level += (random 511 − 255)·overlap·0.5 per step | `tp_chaos` |
| window | auto-mutations **per beat** (every 4 steps) `8·w³`: the integer part, plus one more with probability equal to the fraction; 0 below 0.05 | `tp_namt` |
| blend | Sound: position `2·blend` → kit `a = clip(int, 0, 1)` and fraction (808 → 909 → crunch). Past noon also the crunch bus, `c = clip(2·blend − 1)`: mix `clip(4c)`, drive `1 + 5c` into `clip~ ±1`, bit-crush `qi = 2^(15 − 10c)` (16 → 6 bits), `samphold~` at `24000 − 18000c` Hz | `[v tp_sa]`, `tp_sfr`, `tp_cr*` |
| speed | drift rate `3e-5·r²` per step, `r = clip((abs(speed − 0.5) − 0.13)/0.37)`: zero between the clicks | `tp_drate` |
| pitch | tune ratio `2^((pitch·60 − 36)/12)`, latched per hit | `tp_tune` |
| start/size/density/overlap_alt | lane fill offsets `v − 0.5` (K, S, H, P) | `tp_fo0..3` |
| window_alt | length `2^(int(3.999·v) + 2)` = 4, 8, 16, 32 (always 4/4; odd meters only from Source-gate resets) | `tp_len` |
| blend_alt | decay ×`exp((v − 0.5)·2·ln 4)` (0.25..4) | `tp_decay` |
| speed_alt (routed only in 06: `controls_canvas(extra_alt=["speed_alt"])`) | swing `clip(abs(v − 23)/8)`: the click (23 = 0 dB) = straight, ±8 detents = 12/8. `pickup(move=0.5, jump=1000)`: only after it changes. It is also the module's input gain (`amixer Capture`), which carries over to other instruments | `tp_swing` |
| pitch_alt | unused. It used to be swing, but its stored value (from other instruments) started a swing as soon as Source was held | — |

The alt knobs use `spectral.pickup()`. Note that its jump guard compares against the stream-start baseline, so after
0.2 of travel it re-baselines and needs another 0.02 to reopen. Real knobs stream ~0.001 steps, so the effect is
small, but tests must sweep in small steps (see `topo_groove_test`).

## Tables

| Table | Size | Index | Content |
|---|---|---|---|
| `tp_map` | 3200 | `(y·5 + x)·128 + lane·32 + step` | node levels 0..252 (digit × 28), loaded at loadbang |
| `tp_off` | 128 | `lane·32 + step` | mutation offsets added to the interpolated map |
| `tp_home` | 128 | same | stored offsets (+ `[v tp_hdx/hdy]` drift) |
| `tp_snd` | 78 | `snd_base(V) + param·3 + kit` | `KITS` values; hz/log kinds stored as log2 |
| `tp_exp` | 1028 | `1 + 1024·u` | exponential decay `(e^(−6.91u) − 0.001)/0.999`: 1 → exactly 0 (−60 dB curve), clamped |
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
  1. the period (`timer`, gaps > 2 s ignored) → `tp_swd = swing·period/3` (1 = 12/8);
  2. advance: step = 0 if `tp_rflag` (reset or load), else `(step + 1) mod len`. Step mod 4 = 0 → `tp_beat` (auto-mutate); step 0 → `tp_cycle` (tests print it);
     then `tp_drift`;
  3. schedule: `[delay (step mod 2)·tp_swd]` → `tp_pst` → per lane:
     `lvl = clip(clip(qr + off) + chaos·(rnd − 255), 0, 255)`; hit if `lvl ≥ thr`; velocity `0.35 + 0.65·lvl/255`.
     S hit with `lvl ≥ ACCENT` → clap too; H hit with `lvl ≥ ACCENT` → OH, else CH.
- **`[pd mutate]`:** a mutation picks lane `mL = 32·rnd(4)`, step `ms = rnd(len)`, kind `rnd(10)`:
  - **0–4, move:** neighbour `n = (ms + d) mod len`, `d ∈ {−2, −1, 1, 2}`. If exactly one of the two steps plays
    (`level ≥ thr`), swap their levels by writing both offsets; otherwise **flip** step 1 (so moves are never
    silent no-ops).
  - **5–7, flip:** playing → `0.9·u·thr`; silent → `thr + u·(255 − thr)` only with probability `0.7·fill` (else
    unchanged). Without that, heavy mutation drifted towards half the grid playing (29 → 69 hits); with it the
    playing share settles near `0.7f/(1 + 0.7f)`.
  - **8–9, heal:** offset 0.
  - Before the flip/move fix, a 4-mutation burst was often inaudible (moves between two silent steps); see the
    test notes.
- **Drift:** per step, unless locked: `dx += (rnd(2001) − 1000)·tp_drate`, clipped ±0.5 (also dy).
- **Home:** `[until]` copies `tp_off ↔ tp_home` + the drift position. **Vanilla:** zero `tp_off`, dx = dy = 0.
- **Randomness:** `glitch.rnd()` instances seeded from the time to the first clock.

### Voices (`[pd voices]`)

Analog models after the TR-808/909 recipes. The first build used 2-op FM voices with 8 randomised anchors; on
hardware they sounded like bleeps (see below).

- **Parameters:** per voice (`KITS`), each with three kit values (808, 909, crunch). They are read at each hit from
  `tp_snd` with `lerp(kit a, a+1, frac)`, then transformed by kind:
  - `hz` (2^v × tune), `log` (2^v), `oct` (2^v − 1), `dec` (ms × `tp_decay`), `lin`;
  - the results go into `[v tp_<V>_<param>]`.
- **Envelopes:** `xenv()` = a `vline~` ramp u (0 → 1 over the decay) → `tabread4~ tp_exp`. True exponential, ending at
  exactly 0. It starts at u = 1 (silent, set at load). A hit sends `0, 1 <ms>`; a choke sends `1 3`.
- **Round robin:** two halves per voice. A new hit chokes the other half, so the half that starts is silent and its
  `osc~` phases reset to 0.75 turns (a rising zero crossing of the cosine) without a click.
- **Voices:**
  - **K:** `osc~` at `f·(1 + (2^sweep − 1)·penv)`, pitch env over ptime, × amp env. Plus a 4 ms burst of `hip~ 1500`
    noise (click), then `*~ drive` → `softclip`.
  - **S:** two `osc~` (f1, f2·0.6) with a 15 ms half-octave drop, × tone env. Plus noise → `hip~ ncut` ×2 → `lop~ 9000`
    × noise env. Mix: tone × (1 − 0.5·snappy), noise × 1.6·snappy.
  - **C:** noise → `bp~ fc 2` → `hip~ 400` × (three linear 7 ms bursts 10 ms apart + 0.7 × an exp tail from 28 ms).
  - **CH/OH:** the 808 metal: six square `phasor~`s at 205.3, 304.4, 369.6, 522.7, 540 and 800 Hz × metal, ÷6.
    Mixed with noise by `noise`, then `bp~ cut 1` → `hip~ 0.6·cut` ×2 × env. A CH hit chokes both OH halves.
  - **P:** `osc~` with a 40 ms sweep, × amp env, + a 6 ms `bp~ 3000` noise click.
- **Post:** equal-power pans, then `crunch()`, `*~ 0.8` and `spectral.softclip`. The `LEVEL`s set the single-hit peaks to about
  K 0.64, S 0.67, C 0.52, CH 0.34, OH 0.35, P 0.46.

### First hardware report (2026-10-20) and fixes

- **Report:** "drums don't sound like drums (bleeps)", and with Fill fully CCW it "keeps playing / knobs change
  nothing".
- **Not reproducible offline,** even with a simulated 1 ms control stream: Fill 0 was
  silent and X/Y changed the pattern.
- **Likely causes:**
  1. blend persisted CW from other instruments → randomised FM anchor 7;
  2. a pot fully CCW reads above 0.012, so the backbone 9s kept playing. They're also the part that changes least
     across the map.
- **Fixes:** the analog-model rebuild, three hand-designed kits, and the Fill dead zone. The owner suspects part of the
  report may have been their own mistake; re-test pending.

## Tests (`sim/test_06_*.pd`, scenarios in `tools/gen.py`)

The test build adds `[pd testclock]`:
- `tp_tclk 1` sends Reset pulses every `tp_tper` ms (125 = 16ths at 120 BPM);
- it prints `step: t n`, `cycle: t` and `hit_<V>: t vel` (t = ms since load).

Group the prints into cycles to compare patterns. Checked offline:

| Test | Result |
|---|---|
| voices | each voice; spectra: K 47 Hz with a 650 ms tail, S 177/260 Hz + noise, C ~1 kHz band, CH 5.6–7 kHz, OH 4–9 kHz, P ~160 Hz. Peaks as above. The OH is cut 150 ms after a CH. No NaN. The kick's only sample jumps are its click burst |
| sound | the same blend gives identical kick spectra; blend 1 (crunch) → K 62 Hz with drive harmonics, a brighter S; blend 0.5 → the 909 hats |
| pattern | locked, chaos 0: cycles 1–3 identical (29 hits, house node); density 0.03 (dead zone) → 0 hits; fill 1 → 56 hits |
| mutate | Record → the next cycle differs; File short → the plain map; File held 1.3 s stores; Record → differs; File short → the stored pattern; Window 1 → a new pattern each cycle; Freeze → repeats |
| meter | Length 32 and a Source-gate pulse every 12 steps → 12-step loops; the pulses stop → back to 32 |
| vanilla | Record → B; stored as home; Record → C; File double-tap → the plain map (A); File short → B (home kept). Window 1 → about 70% of hits change per cycle, density ~40 hits (map 29) |
| groove | alt Speed 23 → 31 → odd steps 41.67 ms late at 125 ms (12/8); holding Source with a stored 27 or 26 → no swing; window_alt 0.35 → 8-step cycles; Source gate → the next step is 0; Speed 1 → the pattern drifts; fill 0.15 + hats offset −0.18 → kick/snare only |

A 61 s render takes ~1.5 s on the desktop, about 3× lighter per second than 05_spectral.
