# scan.instr — design notes

Built 2026-11-14 **without a design walk-through** (the owner was away: "make auto decisions and carry on").
`instr/scan.instr`, tests `tools/scan_sim.py` (WSL Csound 6.18 + `m609` in 6.09.1), guide `docs/manual/17_scan.md`.

## The opcode problem
The plan was Csound's `scanu` + `scans`. **They are not in the module's Csound 6.11.0** (`libcsound64.so.6.0` and
the plugin folder read from `SDImage/nebulae_stock_pi4.img`: no `scanu`, `scans` or `scanu2`; only `scanhammer`).
An instrument using them would not compile on the unit. So the mass-spring model is written out in orchestra
code: 64 masses on a ring, one update per k-cycle (ksmps 64 → 750 updates a second), semi-implicit Euler:

    a = stiffness · (x[i-1] + x[i+1] - 2 x[i]) - centring · x[i] - damping · v[i];  v += a;  x = x (1 - leak) + v

Since 2026-11-17 the constants are set from rates in Hz (see "Fixed after hardware"): the wave speed is
R · 64 / 750 masses per update (R ≤ 2 Hz, so stiffness ≤ 0.03, far inside the stability limit of 1), and the
ring's mean motion is removed each update. A guard eases the ring back (≤ 0.5 % per update) if any mass passes
±0.6 (bowing hard with no damping). The shape is written alternately into
two tables, crossfaded across each k-cycle with `interp` (the waveform glides between updates, as `scanu` does).

## Csound 6.09 differences found (also in docs/INSTR.md)
- **`copya2ftab` behaves differently in 6.09** (the read-back waveform differed: half the level, another pitch).
  Written-out `tablewkt` loops give identical results in 6.09 and 6.18 (in guard-point mode, 2: mode 1, used
  until 2026-11-17, is wrap mode and left the guard point at 0).
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

## Fixed after hardware (2026-11-17)
**The owner: "very clicky/noisy, I don't think it's working correctly".** Two faults, both missed by the tests:
- **A click once per cycle of the note.** `tablewkt`'s last argument was 1, which is *wrap* mode, not guard-point
  mode (2). The guard point (the extra point after the last, which `poscil3` reads at the wrap) stayed at 0, so
  the waveform dropped to 0 once a cycle: a buzz at the pitch. Checked in 6.18 and 6.09: mode 1 leaves the guard
  at 0, mode 2 copies point 0 into it.
- **The note split in two.** A wave going round the ring R times a second moves harmonic n by n x R Hz, and a
  strike sends two, one each way. R was ~5 Hz at the defaults, so a C3 strike sounded at 125.6 and 135.9 Hz
  (+-4 %, with nothing on the note itself). The old pitch test allowed 5 %, calling it "the natural chorus".
  Scanned synthesis needs the motion slow next to the note, so the physics is now set in Hz: Size and Density
  give R = 0.02 .. 2 Hz (0.25 at the defaults), Overlap a centring wobble of 0.05 .. 3 Hz.

Knock-on changes, because the motion is now slow:
- Window sets a ring time, 60 s .. 0.4 s to -60 dB (8 s at the default), on the shape as well as the motion: a
  slow string damped only on its motion just freezes in place.
- The bow was a constant push on one mass, stepping to the next mass every 42 ms (a tick each time). It is now a
  random push either way, through a bell curve a few masses wide moving smoothly round the ring.
- The input was decimated to the update rate with no filter (aliasing) and kicked mass 0. Now its level
  (onsets harder) pushes through the same bell curve at Start.
- The ring's mean motion is removed each update (a push could build it up for ever), and the guard eases the
  string back at most 0.5 % per update instead of rescaling it in one step.

**Hardware 2026-11-19, the owner: "Scan is much improved."** Nothing more reported yet (see Hardware
questions).

## Tests (2026-11-17: 14/14 in 6.18; 6.09.1 compiles, the strike identical)
`wsl -u andy -- python3 /mnt/c/Users/andyu/Documents/NebulaePD/tools/scan_sim.py`; `python tools/scan_sim.py m609`.
The new checks fail on the 2026-11-14 build (in brackets).

| Scenario | Result |
|---|---|
| strike | rms 0.110, dies away; 130.7 / 261.5 Hz at C3 / C4 (within 1 %; was 125.6 / 256.3); the energy on the harmonics 11.7 / 20.7 dB over the rest (-28 / -23) |
| clean | sharpest corner against a sine (harmonic number squared): 41 / 23 / 16 at C2 / C3 / C5 after a strike, 26 bowing, limit 200 (8400 / 2500 / 210 / 6000) |
| decay | -20 dB after 4.2 s (Window 0.1) vs 0.2 s (Window 0.9) |
| timbre | a harmonic's level swings 24.5 dB in the 2.4 s after a strike (the centroid test it replaces hardly moves when the motion is slow) |
| bow | sustained, rms 0.08 .. 0.22 for 8 s; 33 dB on the harmonics |
| input | Source off: nothing; on: rms 0.098 |
| freeze | holds 0.088 steady; unfrozen the string has gone |
| sweep | 60 s of extremes: bounded, no NaN; CPU 0.58x the factory looper |
| m609 | 6.09.1: compiles, a strike at rms 0.110, 130.7 Hz |

## Hardware questions
- CPU on the module (the update loop is ~1300 opcode calls per k-cycle).
- Does the default sound (Size 0.4, Density 0.5, Window 0.4) make sense straight away? Level of a strike.
- After the 2026-11-17 fix: is the motion's range right (0.02 .. 2 trips round the ring a second)? Bow and input
  levels against a strike.
