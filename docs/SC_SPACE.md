# 08_sc_space: design notes

Built 2026-11-14 **without a design walk-through**: the owner was away ("auto choose sensible options"). Every
choice below was mine, and each lists alternatives. Patch `sc/08_sc_space.scd`, tests `tools/sc_space_tests.py`
(NRT) and `python tools/sc_osc_tests.py sc/08_sc_space.scd` (live OSC), guide `docs/manual/19_sc_space.md`.

## Decisions for the owner to review
| # | Decided | Alternatives |
|---|---|---|
| 1 | **Greyhole (diffuse delays) into JPverb (reverb), in series; alt Start = the balance** (delays only ↔ reverb only) | Parallel; two separate patches; a fixed balance |
| 2 | **Start = delay time 20 ms – 1.4 s** (Greyhole tops out near 1.43 s), **Overlap = delay feedback, Density = diffusion** | Start = pre-delay; Density = reverb early diffusion |
| 3 | **Size = room size for both engines** | Separate sizes (alt) |
| 4 | **Window = reverb decay 0.3 – 60 s** (JPverb's t60, scaled ÷1.4 to what it actually rings) | 0.3 – 30 s |
| 5 | **Pitch = tone (damping), click = neutral** | Pitch = shimmer interval in V/oct; Pitch = low/high-cut tilt |
| 6 | **Speed = movement** (modulation depth and rate; gentle between the clicks) | Speed = delay-time multiplier (tape-style) |
| 7 | **Freeze = a spectral freeze of the space (`PV_MagFreeze`)**, the input shut out, the reverb ringing on underneath. JPverb caps its t60 at 60 s (−1 dB/s), so it can't hold on its own | Freeze = JPverb at its longest (slowly fading); a looped buffer of the last seconds |
| 8 | **File held = momentary freeze** (as shimmer, vocoder) | File = next preset |
| 9 | **Record = duck** (under the dry input; alt Density = depth, at most −30 dB; alt Window = release) | Duck on by default; Record = "kill dry" |
| 10 | **Source = shimmer** (an octave up, fed back into the reverb; alt Blend = amount) | Source = reverse swell; shimmer with a fifth |
| 11 | **Reset = clear** (input shut, decay and feedback down for 0.4 s, back after 0.7 s; also lets go of a frozen hold) | Reset = tap the delay time |
| 12 | **Alt: balance, width, duck depth + release, bass decay, shimmer amount** | Low/high cut |
| 13 | **Stick: `08_sc_space.scd`** (SC orange page, Source; `31-simple` moves to Reset) | — |

## Engine
- `Greyhole.ar(send, delayTime, damp, size, diff, feedback, modDepth, modFreq)`. Its echoes come at
  delayTime + about 0.065 s × size (measured: 0.315 s for 0.25 s at size 1), and its delay tops out near 1.43 s.
- `JPverb.ar(in, t60, damp, size, 0.707, modDepth, modFreq, low, 1, 1, 500, 2000)`. It rings about 1.4× its t60
  argument (measured), so the patch divides by 1.4. Its t60 tops out at 60 s: 60, 100 and 1000 give identical
  output.
- **Freeze:** `IFFT(PV_MagFreeze(FFT(LocalBuf(2048), ch), on))` per channel, crossfaded in over 50 ms. Reset
  releases the snapshot (it re-freezes on the drained, silent space).
- **Shimmer:** `PitchShift` (ratio 2) of the reverb's output (`LocalIn`/`LocalOut`), back into its input.
- **Duck:** `Amplitude.kr` of the dry input × 8, clipped, × depth × 0.97.
- **Output:** mid/side width, `LeakDC`, equal-power blend, `Limiter` 0.95 (20 ms delay, measured).

## Tests (2026-11-14: all pass)
| Scenario | Result |
|---|---|
| decay | Window 0.3: T60 1.61 s (nominal 1.47); 0.7: 11.35 s (12.24) |
| delays | delays only, no diffusion, Start = 250 ms: echoes 0.34–0.38 s apart (+ Greyhole's 0.1 s at Size noon) |
| freeze | held: −15.4 dB at 4–5 s and at 12–13 s; a new 1 kHz tone doesn't go in; Reset while frozen: −61 dB, stays clear |
| duck | gaps over playing: −5.0 dB off, +25.5 dB on |
| clear | Reset: the tail drops 173 dB (to silence) in 0.3 s; a new burst sounds again |
| shimmer | 880 Hz in a 440 Hz tail: −56 dB under the fundamental off, −2 dB on |
| tone | tail centroid 1077 Hz (Pitch 0.2) → 9712 Hz (Pitch 0.9) |
| level | everything moving for 20 s, then everything at the top for 10 s: peak 0.950 (the limiter), no NaN |
| OSC (live) | all 17 controls reach the synth through the firmware's own sender |

**CPU (PC, NRT, 120 s, the parts alone):** JPverb 6.2 % of a core, Greyhole 4.7 %, PitchShift 0.1 %, the FFT
freeze about 0. For comparison, FreeVerb2 (in 07_sc_mosaic) is 8.9 %. So sc_space costs about what
sc_mosaic does.

## Hardware questions
- CPU on the Pi (about 11 % of a PC core). If it's too heavy, the fallback is a lighter build with Greyhole
  only, or JPverb only, as separate patches.
