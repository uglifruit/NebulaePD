# quartet.instr and somnus.instr: design notes

Built 2026-11-15. They're in the spirit of Neutral Labs' **Elmyra 2** (quartet) and Befaco's **Oneiroi** (somnus).
They're our own designs and names, written from the makers' manuals. The owner chose:
- for quartet: the buttons as touch pads, File = 11 programs, and a stereo reverb after (CPU 0.50× the factory
  looper, reverb included);
- for somnus: Blend morphs the sources; Record / randomise / undo; File = filter mode.

Guides `docs/manual/17ic_quartet.md`, `17id_somnus.md`; tests `tools/quartet_sim.py`, `tools/somnus_sim.py`. Stick
`019_quartet.instr`, `020_somnus.instr`.

## quartet decisions for review
| # | Decided | Alternatives |
|---|---|---|
| 1 | **Voices:** four instances on one morphing wavetable (8 waves, band-limited to 40 harmonics, `ftmorf`), the WAVE shared (Size) | A WAVE per voice (Elmyra's), no knobs for it |
| 2 | **Touch:** Record / Reset / Freeze momentary for voices 1–3, Source latches voice 4; the envelope on alt Density (5 ms .. 3 s attack, 50 ms .. 4.5 s release) | Pressure-sensitive (the Nebulae's gates are on/off) |
| 3 | **Tuning:** voice *n* at *n* × Start × 12 semitones, unquantised; alt Start past noon rounds to semitones | Per-voice tuning |
| 4 | **The 11 programs** (File; Density = amount): unison (±30 cents), subs (−1, −2 octaves), chord (7 shapes), fold, saturation, bit depth (12 → 1.5 bits), sample rate (`fold` ×1–81), tuned noise, DJ filter (LP below noon, HP above), dual wave (a second table further along), hard sync (`syncphasor`, ratio 1–8) | Elmyra's exact programs (described, not specified) |
| 5 | **The chain:** saturated mix (`tanh` ×1.6) → `zdf_ladder` (Window; alt Pitch = resonance) → delay (alt Overlap = time 10 ms–1.6 s, Overlap = feedback to ×2.2 held by `tanh`, alt Size = mix) → + your input → bite → reverb | Filter after the delay (an Elmyra option) |
| 6 | **Bite (Blend):** `tanh` drive ×1–31 plus a sine fold, through a low-pass that closes (18 kHz → 2.7 kHz) as it bites: our stand-in for the analogue OUCH (BITE/CHOKE) | CHOKE on its own knob (no knob left) |
| 7 | **LFO (Speed):** sine clockwise, sample & hold anticlockwise, ±2 octaves on the cutoff at the ends | Two LFOs |

## somnus decisions for review
| # | Decided | Alternatives |
|---|---|---|
| 1 | **The loop:** 5 s stereo (two tables, prefilled with white noise as the original), played at varispeed (Speed: 0 at noon, 1× at the clicks, 2× at the ends), start and length (7.645 ms = one C3 period .. 5 s) | — |
| 2 | **Recording** writes at the play position: old × alt Size + the input (or the output, with alt Record) | A separate record head |
| 3 | **Sources (Blend):** a stereo sine (±0.1 % detune), a 6-saw supersaw (alt Start = detune), a 2048-sample wavetable read from the loop (alt Start also moves where), the loop | Separate level knobs (Oneiroi's faders) |
| 4 | **Effects in series:** filter (`zdf_2pole_mode` LP/BP/HP, or a comb; File) → resonator (3 delay-line resonances: root, fifth, octave; tune 40–700 Hz on alt Pitch) → echo (left T, right 1.5 T, crossed feedback) → ambience (`reverbsc`, spacetime on alt Window, amount alt Blend) | A movable filter (Oneiroi's) |
| 5 | **Randomise (Reset):** offsets ±0.35 on Blend, start, length, filter, resonator, echo and detune, glided over 0.25 s and snapped exactly at the end. **Undo (Freeze)** restores the previous offsets: tested to 0.00 dB | Intensity and target choices (Oneiroi has both) |
| 6 | **No self-modulation:** no knob was left; the randomiser and Speed give the motion | An LFO on alt Speed's neighbour |

## Tests (2026-11-15)
- quartet: 17/17 on 6.18 + 6.09.1 (C2 exact; voices 1–3 at C2/G2/D3; envelopes; microtonal 4.8 vs chromatic 5
  semitones; wave; every program different, subs at f/2; filter; runaway delay; bite; LFO; input; reverb; sweep;
  CPU 0.50×, 0.42× with all four voices on in unison).
- somnus: 17/17 on 6.18 + 6.09.1 (sine C3; four different sources; the tiny loop C3 at 1×, C4 at 2×; stopped at
  noon; recording; LP/BP/HP/comb; resonances at 126/188/251 Hz; echoes 0.286 / 0.431 s; ambience; randomise and
  exact undo; sweep; CPU 0.47×).
- Found on the way: `poscil` can't change table while playing (`tablekt` for the dual wave); an exponential glide
  never quite arrives (it left the undo a few samples out in a noise-filled loop, so the glide now snaps).

## Hardware questions
- quartet: do the touch envelopes feel right? Which programs earn their place?
- somnus: is 5 s enough of a loop? Is the randomiser's range right?
