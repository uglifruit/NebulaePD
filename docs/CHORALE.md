# chorale.instr: design notes

Built 2026-11-15. The owner chose:
- Pitch click = C2;
- a unison choir: Density = 1 to 8 voices (detuned, some an octave down); Source = chords, Reset = the next of
  8 chord shapes; Start = the vowel (ah → eh → ee → oh → oo);
- Blend only mixes the input in.

The rest was mine. Instrument `instr/chorale.instr`, tests `tools/chorale_sim.py`, guide
`docs/manual/17d_chorale.md`.

## Decisions for the owner to review
| # | Decided | Alternatives |
|---|---|---|
| 1 | **Source-filter, not FOF:** 8 voices (a band-limited saw through a 1.5 kHz one-pole each) summed, then one 5-formant bank per channel. Cheap, and the vowel moves for the whole choir at once | `fof` grains per voice (closer to a sung tone, 8× the cost) |
| 2 | **Formant data: the published tables** (bass, tenor, alto, soprano × a e i o u: 5 frequencies, levels, bandwidths), interpolated between neighbouring vowels | — |
| 3 | **Unison voicing: 0, 0, +12, 0, +12, 0, +12, −12** (voices 3, 5, 7 an octave up, 8 an octave down) | All on the note |
| 4 | **Chords: voice *i* on note *i* mod 4, voices 5–8 an octave up**; shapes as sc_swarm | Voice leading between chords |
| 5 | **Size = formant shift ±0.4 octave** (noon none) | Size = the register, continuous |
| 6 | **File = register** (bass → tenor → alto → soprano, starting on bass, which suits C2) | File = next vowel set |
| 7 | **Window = ensemble** (detune ±(Window² × 25) cents per voice + a slow wander of its own) | Window = vibrato |
| 8 | **Overlap = breath** (noise through the same formants) | — |
| 9 | **Speed = vowel drift** (a random spline round Start, none between the clicks) | Speed = vibrato rate |
| 10 | **Freeze = hold the vowel** | Freeze = hold the whole sound (a spectral freeze) |
| 11 | **Record = breathe** (each voice drops out for 0.6 s every 3–8 s, at its own random moments) | Record = sub voice |
| 12 | **Alt: width, vibrato depth (0–50 cents), reverb size and amount** | — |
| 13 | **Stick name `011_chorale.instr`** (Csound user yellow page, Record; `999_fw_backup`, `bt_storyteller`, `bt_test`, `pearls` one along) | — |

## Engine
- **instr 10:** Reset → chord, File → register; the vowel = Start × 4 + an `rspline` drift, held by Freeze.
- **instr 20.1–20.8 (voices):**
  - `vco2` saw at a k-rate frequency, with a k-rate vibrato: `vco2` won't take an a-rate frequency, and `pow`
    has no a-rate form;
  - `tone` 1.5 kHz; Density fade; breath gate;
  - out to a mono bus and a panned stereo pair.
- **instr 30:** noise for breath, the 5 formants as `reson` (peak-normalised) × level per channel, written out with
  a macro. Opcodes inside a k-rate loop would share one state. Then `reverbsc`, equal-power blend, `tanh`.
- `kr` can't be a variable name (it's the control rate): the Reset trigger is `krs`.
- The `.instr` text reaches Csound unchanged: the firmware's `instrparser.py` only takes out the `nebconfig` block.
  The macros and `\` continuations compile through `compileOrc` in 6.09.1.

## Tests (2026-11-15)
`wsl … tools/chorale_sim.py`: 16/16 pass on Csound 6.18. `python tools/chorale_sim.py m609`: 1/1 on 6.09.1.

| Scenario | Result |
|---|---|
| pitch | one voice: 65.37 Hz at the click, 130.74 at 0.8; rms 0.106, peak 0.30 |
| vowel | "ee" against "ah": 1.55–1.95 kHz over 0.9–1.2 kHz from −19.6 to +10.8 dB; 200–300 Hz over 500–700 Hz from −8.0 to +25.4 dB |
| register | the strongest harmonic near formant 1: 589 → 654 → 785 → 785 Hz (bass → tenor → alto → soprano) |
| shift | centroid 582 → 739 Hz (Size 0.1 → 0.9) |
| voices | spread round each harmonic 2.8 → 9.3 cents (1 → 8 voices); level −19.4 → −20.3 dB |
| chord | E2's line against C2's: −94 dB in unison, 0 dB in chord mode (major, after one Reset) |
| drift | formant bands move 8.3 dB past a click; 0.0 dB between the clicks; 0.0 dB frozen |
| breathe | level dips 3.9 → 6.4 dB |
| breath | +86 dB of air between the harmonics (from none) |
| sweep | 60 s of extremes: peak 0.92, no NaN; CPU 0.44× the factory looper |
| m609 | 6.09.1 compiles it; 65.37 Hz |

## Hardware questions
- Does the choir sound vocal enough with a saw source? FOF would cost more but sound more sung.
