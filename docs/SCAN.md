# scan.instr — design notes

Built 2026-11-14 **without a design walk-through** (the owner was away: "make auto decisions and carry on").
`instr/scan.instr`, tests `tools/scan_sim.py` (WSL Csound 6.18 + `m609` in 6.09.1), guide `docs/manual/17_scan.md`.

## The opcode problem
The plan was Csound's `scanu` + `scans`. **They are not in the module's Csound 6.11.0** (`libcsound64.so.6.0` and
the plugin folder read from `SDImage/nebulae_stock_pi4.img`: no `scanu`, `scans` or `scanu2`; only `scanhammer`).
An instrument using them would not compile on the unit. So the mass-spring model is written out in orchestra
code: 64 masses on a ring, one update per k-cycle (ksmps 64 → 750 updates a second), semi-implicit Euler:

    a = (stiffness · (x[i-1] + x[i+1] - 2 x[i]) - centring · x[i]) / mass - damping · v[i];  v += a;  x += v

Stable for stiffness / mass < 1 (kept so by scaling the stiffness range with min(mass, 1)) and damping < 1. A guard
scales the ring back if any mass passes ±1.5 (bowing hard with no damping). The shape is written alternately into
two tables, crossfaded across each k-cycle with `interp` (the waveform glides between updates, as `scanu` does).

## Csound 6.09 differences found (also in docs/INSTR.md)
- **`copya2ftab` behaves differently in 6.09** (the read-back waveform differed: half the level, another pitch).
  Written-out `tablewkt` loops (guard-point mode 1) give identical results in 6.09 and 6.18.
- Labels inside `if … endif` blocks were avoided (`if kx == 0 kgoto skip` at top level, as the factory
  instruments do), although that turned out not to be the cause here.

## Decisions for the owner to review
| # | Decided | Alternatives |
|---|---|---|
| 1 | **Pitch = the oscillator, V/oct, click = C3** | C4 (as resonator) |
| 2 | **Start = strike position, Size = mass, Density = stiffness, Window = damping, Overlap = centring** (the string's physics on the panel) | Fewer physics knobs and a "material" macro knob |
| 3 | **Blend = dry/wet** (useful with Source) | Blend = output level |
| 4 | **Speed = a second voice** (detuned right of the clicks, an octave below left of them, none between) | Speed = update rate (a "time" control) |
| 5 | **Reset = strike, Record = bow (latching), Source = audio input drives the string, Freeze = hold the waveform, File = next strike shape** (4) | File = presets of the physics; Record = sample-and-hold the shape |
| 6 | Alt: strike strength, stereo width, bow pressure, tone, reverb size/amount | Alt = per-mass variations (heavier masses on one side) |
| 7 | 64 masses, 750 updates a second | 128 masses (4× the CPU); faster updates (ksmps 32: 2×) |
| 8 | Stick name **`008_scan.instr`** (Csound user, orange page, Source) | — |

## Tests (2026-11-14: 11/11 in 6.18, 1/1 in 6.09.1 with the same numbers)
| Scenario | Result |
|---|---|
| strike | a strike sounds (rms 0.118 from silence), dies away, peak 0.65; pitch 125.6 / 256.3 Hz at C3 / C4 (the split partials: within 5 %) |
| decay | −20 dB after 10.6 s (Window 0.1) vs 0.35 s (Window 0.9) |
| timbre | spectral centroid varies 2300–3450 Hz after a strike (the waveform moves) |
| bow | sustained at rms ≈ 0.095 for 8 s |
| input | Source off: the input doesn't reach the string; on: rms 0.043 |
| freeze | level steady (0.036) while the string would have decayed |
| sweep | 60 s of every knob at its extremes, strikes, bowing, input, freeze: bounded (soft clip), no NaN; CPU 0.4–0.5× the factory looper |
| m609 | 6.09.1: compiles; the strike sounds identically (rms 0.118, 125.6 Hz) |

## Hardware questions
- CPU on the module (the update loop is ~1300 opcode calls per k-cycle).
- Does the default sound (Size 0.4, Density 0.5, Window 0.4) make sense straight away? Level of a strike.
