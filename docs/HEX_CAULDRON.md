# hex.instr and cauldron.instr: design notes

Built 2026-11-15. They're in the spirit of Make Noise's **Strega** (hex) and **Bruxa** (cauldron), both made with
Alessandro Cortini. They're our own designs and names, written from the makers' manuals. The owner chose:
- two instruments sharing one core;
- names hex and cauldron;
- a stereo reverb after, if CPU allowed (it did: hex 0.40×, cauldron 0.37× the factory looper, reverb included);
- for hex: momentary touches, and Speed = agitation;
- for cauldron: Pitch = Time (1 V/oct), and the buttons are its self-patches plus a hold.

Guides `docs/manual/17ia_hex.md`, `17ib_cauldron.md`; tests `tools/hex_sim.py`, `tools/cauldron_sim.py`. Stick
`017_hex.instr`, `018_cauldron.instr`.

## The shared core (`TimeFilter`, in both files)
- **A clocked delay:** 1024 "stages" over Time, so a long Time runs a slow clock.
  - The repeats are held (`fold`) at the clock rate, so they turn grainy.
  - Below a 6 kHz clock, noise is added.
  - So the slow end grows an avalanche of noise, as a bucket-brigade (BBD) line does. (The original is analogue;
    ours imitates it.)
- **Three taps** (T, 0.707 T, 0.43 T) mix the output. The first tap alone feeds back, so the loop rings at 1 / T.
- **In the loop:**
  - everything poured in, and every pass, goes through **Filter** (a 2-pole zero-delay low-pass) and **Absorb**
    (a high-pass), then the clock's grain;
  - **Decay** goes to ×1.08, soft-limited (`tanh`), hence "infinity".
- **Two control signals out:** the activity (an rms envelope, 0–1, like Bruxa's CV Out) and the interference (the
  raw output sampled each block).
- **Pitch accuracy:**
  - the feedback is read and written in the same block (a block late, it added 0.67 ms to the loop);
  - the feedback tap is corrected for the two filters' phase at the loop frequency, faded out where that
    frequency falls outside their passbands;
  - tested at 50 / 100 / 200 Hz within 0.4 %;
  - with Absorb set near a low note, that note's pitch is pulled (it cuts the fundamental).

## hex decisions for review
| # | Decided | Alternatives |
|---|---|---|
| 1 | **Tones:** a triangle and square subharmonics at f/2 and f/3 (Start brings them in), then folding (sine of the triangle × up to 9) | More subharmonics; Strega's exact "tones" (not documented) |
| 2 | **Activation** = alt Start (constant) + Freeze held + alt Size × the activity × 2, capped at 1.5 | — |
| 3 | **Interference:** the experiment's output exponentially FMs the tonic: alt Density always, Record held strongly | Linear FM |
| 4 | **Time** on Size: 1.5 s fully anticlockwise → 1.5 ms clockwise (Strega's slow end is anticlockwise) | Time on Pitch (as cauldron) |
| 5 | **Agitation** (Speed): a rise/fall wave at a-rate, 1/60 Hz → ~1 kHz; clockwise rise 85 % of the cycle, anticlockwise 15 %; into the Filter, ±3 octaves × alt Overlap. Reset restarts it | A separate Angle knob |
| 6 | **Time modulation** (alt Pitch): the subharmonics wobble Time (Strega normals them there) | — |
| 7 | **File = hold** (toggle): Decay 1.02, nothing new poured in | — |
| 8 | **Blend:** the tones as they are ↔ the experiment | — |

## cauldron decisions for review
| # | Decided | Alternatives |
|---|---|---|
| 1 | **Time on Pitch:** 20 ms at the click, 1 V/oct; File = ×8 (to 3.6 s) | Time on Size |
| 2 | **Start = input level** (×0.25–×4, it saturates), **Size = the self-patches' depth** | — |
| 3 | **The manual's patches on the buttons (latching):** Record = Wow & Flutter (activity → Time), Source = Noise (interference → Absorb), Reset = Wind & Wave (interference → input, activity → Filter), Freeze = hold | Any patch on any button |
| 4 | **Speed = time modulation:** clockwise a sine wow, anticlockwise a random flutter (Bruxa's Time Modulation input) | — |
| 5 | **Mono experiment, stereo dry**, then the reverb (alt Blend / alt Window) | — |

## Tests (2026-11-15)
- hex: 18/18 on 6.18 + 6.09.1 (tonic C3/C4 exact; tones f/2, f/3, folding; activation; echoes at the set time;
  decay to infinity; Filter/Absorb; agitation; interference; input; hold; reverb; 60 s sweep; CPU 0.40×).
- cauldron: 15/15 on 6.18 + 6.09.1 compiles (pitch 49.97 / 99.81 / 200.05 Hz; long-range echoes 160 ms; decay;
  Filter/Absorb; input level; wow, noise, wind; hold; Speed; reverb; sweep; CPU 0.37×).

## Hardware questions
- Does the slow end's grain/noise feel like the originals'? Is the agitation range right?
- cauldron: are the self-patches useful latched, or would momentary suit better?
