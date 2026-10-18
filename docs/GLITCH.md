# 04_glitch — design notes

A port of the owner's Workshop Computer program 57 **Glitch**: a clock-synced beat-repeater. The reference behaviour is
the firmware source, `releases/57_glitch/main.cpp` in TomWhitwell/Workshop_Computer. The builder is `tools/glitch.py`;
the user guide is `patches/04_glitch_README.md`.

The aim is the same use and the same philosophy as the WC version. Where the Pico's limits forced a choice (the buffer
length), the patch uses the Pi's headroom instead of copying the limit.

## Control map

| Nebulae | WC equivalent | Glitch | Stutter |
|---|---|---|---|
| Reset jack/button | Pulse In 1 | clock (beat = time between pulses) | same |
| Source latch | boot switch position | off = Glitch | on = Stutter (applies at the next clock) |
| Record latch | switch Down | force every slice | same |
| start > 0.5 | switch Mid + Pulse In 2 | gate: glitch every slice | same |
| (else) | switch Up | random < probability | random < probability |
| size | Main knob zone | ÷1 2 3 4 6 | 1 2 3 4 8 slices |
| density | Main knob remainder | glitch + reverse probability | drift probability |
| window | X | degrade amount | shuffle probability |
| overlap | Y | degrade probability | repeat probability |
| Freeze latch | CV In 1 | freeze | freeze |
| blend | (Out 2 = dry) | dry/wet | dry/wet |
| pitch (+1V/oct) | (new) | transpose slices, `round(pitch·60) − 36` st, live. Pass-through: slice-locked pitch-down only | same |
| speed | (new) | ramp: slice k of the beat += `k·round(24·(speed−0.5))` st, latched per slice | same |

CV In 2 (bipolar mod) needs no mapping: every Nebulae pot already sums its own CV jack.

There is no equivalent for the CV outs, the pulse outs or the dry output, because Pd can't drive the Nebulae's gate
output and has no CV outputs. The Source, Record and Freeze LEDs show mode, force and freeze, and the Reset LED
flashes on the clock.

## Constants (`tools/glitch.py`)

| Name | Value | Why |
|---|---|---|
| `BUF` | 2^21 samples (43.7 s) | A power of two makes `/BUF → wrap~ → *BUF` exact in float32, so there is no off-by-one sample at large indices |
| `MAX_BEAT` | 10 s | A clock gap longer than this reuses the last beat length (it is a stopped clock, not a beat) |
| `DRIFT_BEATS` | 12 | Stutter drift reaches back `1..min(BUF/L − 1, 12)` beats (the WC got ~3 beats at 120 BPM from its 2.33 s buffer) |
| `MARGIN` | 128 samples | Each beat's slices end ~2.7 ms before the expected next pulse |
| `GRACE` | 30 ms | After a beat's last slice, wait this long for a late pulse before cycling again |
| `HYST` | 240 samples | Beat-length changes under 5 ms are ignored (TCP/poll jitter) |

## Engine

- **Writer.** An `rpole~` counter plus `tabwrite~`, both restarted by a metro every BUF samples (whole blocks, so they
  stay aligned). It writes `old·frz + in·(1−frz)`, with a 5 ms ramp on frz. Freezing therefore holds the content
  while the counter keeps running. `gt_snap` → `snapshot~` of the counter → `gt_c` gives the next write index.
- **Virtual write position `v`.**
  - Normally `v` is the counter.
  - While frozen, `v` is the counter at the moment of freeze.
  - After unfreeze, `v` stays there until a clock edge at which at least L samples have been written since unfreeze.
    Without this, the first beat after unfreeze would read audio from before the freeze.
- **Clock edge** (`clock` subpatch, a trigger fired right to left):
  1. Beat length L: block-rounded and capped, with hysteresis.
  2. Snapshot of the write position.
  3. `v`.
  4. Geometry:
     - div from the zone and mode;
     - `len = blockfloor((L − MARGIN)/div)`;
     - the mode start: Glitch `S = v − L`; Stutter `S = v − bb·L`, then reshuffle and idx = 0.
  5. Stop the pending slice delays.
  6. First slice.
- **Slice boundary.** The mode subpatch rolls its probabilities and sends B, D, dec, q and g, then `gt_slice` (counter
  clear). Everything happens in one logical instant, so it all lands in the same DSP block. Slice lengths are whole
  blocks, so the `[delay]` chain stays block-exact. After the div-th slice of a beat the next one waits `GRACE`; if no
  clock comes, slices keep cycling, as on the WC.
- **Per-slice routing and rate** (`pass_rate` subpatch).
  - The mode boundaries send `gt_gsel` (glitch or shuffle this slice?), then `gt_slice` last. On `gt_slice`,
    `pass_rate` decides:
    - **glitched:** `g = 1`, `smax = 24`, `Rs = k·step`. The clock sends `gt_k`, the slice index in the beat
      (`k mod div`, 0 at a clock).
    - **pass-through, T < 0, not frozen:** a slice-locked read.
      - `gt_snap` gives `B = c`: the next write index, i.e. the write head itself.
      - Also sent: `D = 1`, no degrade, `Rs = 0`, `smax = −1`, `g = 1`.
      - The writer's dummy `outlet~` → the reader's third `inlet~` forces writer-before-reader DSP order. So with
        rate ≤ 2^(−1/12), even `tabread4~`'s 2-sample look-ahead only touches samples already written.
      - Zero added latency at each slice start. Freezing mid-slice sends `g = 0`, because the buffer ahead now holds
        old audio.
    - **otherwise:** `g = 0` (live).
  - Rate: `gt_rate = 2^(clip(T + Rs, −48, smax)/12)`. T comes from Pitch and is recomputed live.
- **Reader.**
  - Index:
    - `p` = time counter (`sig~ 1` into `rpole~`). `pr` = read counter: `rpole~` of the rate signal, minus the
      current rate, so it starts at 0 and stays phase-continuous when the rate changes.
    - Decimation: `eff = pr − wrap~(pr/dec)·dmul`, where `dmul = dec` while degrading and 0 otherwise. That gives
      `floor(pr/dec)·dec` or plain `pr`, so interpolation survives when not decimating.
    - `idx = wrap((B + BUF + D·eff)/BUF)·BUF`, then `tabread4~` (an integer index returns that exact sample).
  - Bitcrush: `floor(x/q + 65536) − 65536`, times q, with `q = 2^bits/32768`.
  - Fade: 64-sample edge fade, `clip(p/64)·clip((len−1−max(p, pr))/64)`. A sped-up slice ends when its own region
    `[B, B+len)` is used up. It never reads beyond that region, so it never reads ahead of the writer, which leaves a
    staccato gap.
  - Wet gate g, with a 1.5 ms `line~`: `out = g·fade·crushed + (1−g)·live`.
  - The main patch then mixes it with dry by blend.
- **Randomness.** `[random 4096] < threshold`, with thresholds 0..4095 as on the WC. Every `[random]` is seeded from
  the time between load and the first clock.
- **Stutter order.** A Fisher-Yates shuffle of `[table gt_order 8]` with `[until]` loops (`shuffle` subpatch).
  `[v gt_sidx]` holds the slice index.

## Differences from the WC (intentional)

- The buffer is 43 s and beats can be up to 10 s; drift reach is a constant.
- Freeze and Force toggle on gate edges, because those Nebulae inputs latch.
- The mode switches live.
- After unfreeze the frozen beat plays on until a fresh beat is recorded. The WC instead resumes writing at the frozen
  position.
- Slices end MARGIN early and a beat ends with a GRACE wait, so clock jitter never cuts a slice at full level.
- The pass-through ↔ slice switch has a 1.5 ms ramp.

## Tests (`sim/test_04_*.pd`, scenarios in `tools/gen.py`)

The test input `beat_source` replaces `adc~`. On `gt_tclkon` it sends Reset pulses every 500 ms and restarts a
440 Hz ramp at each beat: odd beats ramp to 1.0, even beats to 0.5. "The previous beat" therefore shows up as swapped
levels in 50 ms peaks.

Pass `wav=` to the scenario. Output is recorded with `tabwrite~` and saved by `soundfiler` just before quitting:
`writesf~` drops audio in fast `-batch` runs. Checked:
- **glitch:** passthrough, then:
  - Force → previous beat;
  - ÷4 → four quarter ramps;
  - density 1 → reversed;
  - degrade → 16-sample holds on a 1/256 grid;
  - probability 0 → passthrough;
  - Start gate → glitch on that beat only.
- **stutter:** Force + 8 slices → scrambled; repeat 1 → one flat slice per beat; drift 1 → full-level material where
  the previous beat was half; probability 0 → passthrough.
- **freeze:** the pre-freeze beat loops with the input muted; live audio returns at the 2nd clock after unfreeze.
- **pitch** (÷4, Force), measured by zero crossings per slice:
  - +12 → 880 Hz with the slice's second half silent;
  - Speed +3 per repeat → 440/523/622/740 Hz;
  - −3 per repeat → 440/370/311/262 Hz;
  - −12 → 220 Hz.
  - A live Pitch change lands mid-beat; a Speed change lands at the next slice.
  - No force, Pitch −12 → pass-through slices at 220 Hz. Each starts at the live level of its boundary, with no
    pre-boundary audio. Pitch +12 → live 440 Hz. Pitch −12 + Freeze → live.
- **Clicks:** no sample jumps > 0.07 (0.035 on the quieter pitch render) except the test input's own ramp resets.
