# plates.instr: design notes

Built 2026-11-15: an eight-voice drone in four pairs, in the spirit of an organismic eight-voice drone synth (our
own design and name). The owner chose:
- **the buttons are touch plates:** Record, Reset and Freeze touch pairs 1–3 while held (or while a gate is high),
  Source latches pair 4 on, **Density = Hold** (the level every voice drones at untouched);
- **neighbour FM + a hyper LFO** (two squares combined; File steps the logic);
- **Blend = distortion**;
- Pitch click = C2.

The rest was mine. Instrument `instr/plates.instr`, tests `tools/plates_sim.py`, guide
`docs/manual/17g_plates.md`. Stick `014_plates.instr`.

## Decisions for the owner to review
| # | Decided | Alternatives |
|---|---|---|
| 1 | **Voices:** each is a sine crossfading to a "sharp" wave (odd harmonics with some even ones, 24 partials) by Size | `squinewave` (cleaner, but 6.09 hasn't got it, so nothing here could test it); `vco2` (no audio-rate FM in 6.11) |
| 2 | **Pairs tuned by Start:** pair *p* sits *p* × Start × 12 semitones up (unison fully anticlockwise, fifths at 0.58, octaves fully clockwise) | Each pair tuned freely (more knobs than the panel has) |
| 3 | **Detune within a pair = alt Size** (0–40 cents, default 10: slow beating) | Detune on a main knob, sharp on alt |
| 4 | **The touches:** Record/Reset/Freeze use the firmware's *momentary* mode (on while held or gate high); Source latches. Swell in over alt Density's time (30 ms .. 2.5 s), out twice as slowly | All four momentary (Source can't be: holding it opens the alt layer) |
| 5 | **FM:** pair 4 → 3 → 2 → 1 within the block, pair 1 → 4 one block (0.67 ms) late, all exponential (×e^(±2.5 × Window²)). A pair only modulates while it sounds | Linear FM; a fixed routing matrix |
| 6 | **Hyper LFO:** A from Speed (0.05–30 Hz past the clicks, none between), B = A × (0.5 + 3.5 × alt Window); A OR B / A AND B / A + B on File. It gates the FM (10 % ↔ 100 %) and shakes the pitch (±0.25 semitone); clockwise hard squares, anticlockwise rounded | LFO targets on the alt layer |
| 7 | **Delay:** two lines (right = 1.5 × left; alt Start = time, 30 ms .. 1.2 s), Overlap = feedback (to 1.1, held by a tanh: it can run away) and mix; alt Overlap = the LFO on the time | One stereo delay |
| 8 | **Distortion (Blend):** asymmetric tanh, level-compensated; fully anticlockwise clean | — |
| 9 | **The input (alt Blend) goes into the delay and distortion** | Input on Blend (the owner chose distortion) |
| 10 | **Defaults:** fifths apart, a little sharp, Hold low (0.4), gentle FM, some delay and drive | — |

## Tests (2026-11-15)
`wsl … tools/plates_sim.py`: 16/16 on Csound 6.18. `python tools/plates_sim.py m609`: 1/1 on 6.09.1.

| Scenario | Result |
|---|---|
| hold | silent at Hold 0; droning at 1; C2 65.41 Hz |
| touch | Record, Reset, Freeze, Source bring in C2, G2, D3, A3 (Start 0.58), only that pair (others 91 dB down); released pairs fade |
| swell | to 70 % in 0.05 s → 1.94 s (alt Density 0 → 0.8) |
| sharp | 3rd harmonic −38 → −7 dB |
| detune | the pair's voices 40.0 cents apart at alt Size 1 |
| fm | energy over 800 Hz −79 → −21 dB (Window 0 → 0.7) |
| lfo | the FM band's envelope varies 0.14 → 0.44 past the click; A OR B 5.6 dB more FM than A AND B |
| delay | echoes ring on after a touch (−39 dB against none) |
| drive | 3rd harmonic −55 → −8 dB |
| input | alt Blend brings the input in |
| sweep | 60 s of extremes: bounded, no NaN; CPU 0.42× the factory looper |

## Hardware questions
- Do the touches feel like plates (swell times), and do sequencer gates into Record/Reset/Freeze play well?
- Is the FM chaos usable across Window, or does it need taming at the top?
