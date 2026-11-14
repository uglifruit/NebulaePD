# morph.instr — design notes

Built 2026-11-14 **without a design walk-through** (the owner was away: "make auto decisions and carry on").
`instr/morph.instr`, tests `tools/morph_sim.py` (WSL Csound 6.18 + `m609` in 6.09.1), guide
`docs/manual/16_morph.md`. The owner's shortlist said "morph / scan"; both were built, morph first.

## Decisions for the owner to review
| # | Decided | Alternatives |
|---|---|---|
| 1 | **A = left input (live), B = a stick file** (through `mincer`, so B has stretch's speed/freeze/scrub), or the right input (Source), or a grab of A (Record) | A = left, B = right always (no files); A = file, B = input |
| 2 | **Blend = morph** (`pvsmorph`, amplitudes and frequencies together) | Blend = dry/wet with the morph position on another knob |
| 3 | **Overlap = cross**: crossfade (in the spectral domain) from the morph to `pvsvoc` cross-synthesis, A's partials under B's envelope, with +20 dB makeup at full | Separate amplitude / frequency morph amounts (tried first: amplitude-only morphing mostly gives B, not "A's notes in B's colour"); B's notes in A's colour |
| 4 | **Window = blur** (`pvsmooth`, 0.02–2 s) | Spectral smear (stretch's Window) |
| 5 | **Density = dry/wet** (loads at full wet) | Layers (as stretch); a spectral arpeggiator (`pvsarp`) on V/oct, as the idea list suggested |
| 6 | **Pitch = plain transpose** (`pvscale`) | Formant-keeping transpose (tried first: on simple spectra it moved the energy oddly) |
| 7 | **Speed / Start / Size = B's pointer**, stretch's map (centre frozen, clicks 1×) | B at normal speed only |
| 8 | **Freeze = hold A's spectrum** (`pvsfreeze`); B's freeze = Speed centre | Freeze both; Freeze B |
| 9 | **Record = B becomes the last N s of A** (until File) | Record = grab B from the right input |
| 10 | Alt: grab length, tone, reverb size/amount (as stretch) | — |
| 11 | Stick name **`007_morph.instr`** (Csound user, orange page, File; `999_fw_backup` and the rest move one along, Pearls to the yellow page) | — |

## Engine
- instr 1 (stretch's structure): file sample rates (`giRate[]`, the 6.11 mincer fix), a rolling recorder of A (two
  30 s buffers), B's source (file / grab), region, Speed → rate map, playhead with soft jumps.
- instr 90: B = `mincer` (2048, locked) at the file rate ratio, or the right input; `pvsanal` A and B (2048 / 512);
  `pvsfreeze` A; `pvsmorph` (Blend); `pvsvoc` B-envelope × A-frequencies; `pvsmorph` between the two (Overlap);
  `pvsmooth` (Window); `pvscale` (Pitch); `pvsynth`; makeup; tone shelf; `reverbsc`; dry/wet; `tanh`.
- An adaptive makeup (B's / A's level against the output) was tried for the cross side: it pumped and spiked on
  near-empty spectra, so the makeup is fixed (× 1 + 9 · Overlap).

## Tests (2026-11-14: 13/13 in 6.18, 1/1 in 6.09.1)
| Scenario | Result |
|---|---|
| morph | Blend 0 = A (439.8 Hz), 1 = B (659.9 Hz); Speed centre freezes B and it still sounds |
| cross | A's saw partials gated by B's noise envelope (on 0.054 rms, off 0), the 220 Hz harmonics carry 43 % of the energy; no discontinuities beyond the saw's own |
| freeze | A's 440 held after the input moved to 880 |
| pitch | +12: 440 → 880 |
| source | B = the right input (330 Hz) |
| grab | Record: B = A's earlier 550 after A moved on to 770 |
| full | everything moving for 70 s: rms 0.14, peak 0.92, no NaN, no clicks; CPU 0.79× the factory looper |
| m609 | Csound 6.09.1: compiles; B from a 44.1 kHz file in tune (659.9 Hz) |

## Hardware questions
- Levels: the cross makeup (+20 dB at full Overlap) with real material; the dry/wet default (full wet).
- CPU on the module (two analyses, one `mincer`, one resynthesis).
