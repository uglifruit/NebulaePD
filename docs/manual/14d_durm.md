# Durm: a four-voice drum machine

Eli Pechman's Pd drum machine ("DUUUUUUUURRRM"): a bass drum, snare, closed and open hi-hat, and a percussion
voice, each fired by a gate. All voices share the front-panel settings, but each voice takes them only when it's
triggered, and you can lock a voice's settings so the knobs stop affecting it. Speed runs one of four shared
effects. The inputs go through that effect, ducked by the drums.

**Bank:** Pd. Summarised from its author's manual (`Durm_Manual.pdf`).

## Triggers
| Jack / button | Fires |
|---|---|
| **Record** | Bass drum (always on the left output) |
| **File** (next) | Snare |
| **Source** | Closed hi-hat |
| **Reset** | Open hi-hat |
| **Freeze** | Percussion (four-operator phase modulation) |

The snare, hats and percussion go to the right output.

## Controls (the same knobs, a different job for each drum)
| Control | Bass drum | Snare | Hi-hats | Percussion |
|---|---|---|---|---|
| **Pitch** + 1 V/oct | pitch | pitch | pitch | base pitch |
| **Start** | pitch envelope decay | pitch envelope decay | envelope → pitch amount | harmonic ratio numerator |
| **Density** | pitch envelope amount | pitch envelope amount | oscillator spread | harmonic ratio denominator |
| **Size** | amplitude decay | amplitude decay | decay (closed = 1/10 of open) | amplitude decay |
| **Overlap** | brightness | brightness | noise low-pass | brightness |
| **Blend** | non-linearity (detune + filter overdrive) | noise feedback | wave: sine ↔ square | phase-modulation amount |
| **Window** | distortion | white noise mix | noise high-pass | waveform: sine ↔ tangent (saw-like) |
| **Speed** | the shared effect (below): left of noon one thing, right of noon another | | | |

## The shared effect (Speed; choose with alt Window)
| Effect | Left of noon | Right of noon |
|---|---|---|
| Trigger randomiser (at boot) | random skip | random ratchet |
| Compand / distort | compress | expand / distort |
| DJ-style filter | low-pass | high-pass |
| DJ-style downsampler | downsample | high-pass sample |

## Alt layer (hold Source)
| Control | Does |
|---|---|
| alt **Start / Density / Size / Overlap / Blend** | How much that setting is randomised on each hit (unlocked drums only) |
| alt **Window** | Choose the shared effect |
| alt **Pitch** | Bass drum's pitch range (keeps it low) |
| alt **Speed** | Audio input gain |
| alt **buttons** | Lock that drum's settings (Reset locks both hats). File and Reset don't show the lock state, so it may take a try or two |

## Quick start
1. Patch a drum sequencer's gates into Record (kick), File (snare), Source and Reset (hats), Freeze (perc).
2. Shape a drum, then lock it (hold Source, press its button) so the knobs move on to the next.
3. Turn Speed for the effect; raise the alt randomness for hits that vary.
