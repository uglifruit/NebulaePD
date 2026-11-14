# SuperCollider instruments for the Nebulae (uf2)

These run in the **SC bank**: hold Speed, turn Speed clockwise **past Pd**, so the right Speed light turns **blue**.
Then press a lit button. Expect about 5–10 s of silence while SuperCollider starts.

| File | What it is | Needs |
|---|---|---|
| `01_sctest` | Test patch: a plucked saw for checking the controls | Reset to play |
| `02_sc_drift` | Evolving drone / pad | Nothing, it sounds at once |
| `03_sc_strike` | Plucked string with a resonant body | Reset (button or gate), or Record for auto-pluck |
| `04_sc_cloud` | Granular clouds from the audio input | Audio patched in |
| `05_sc_pattern` | Generative sequencer: lead, bell, bass, hat on Euclidean patterns in a scale | Nothing (its own tempo), or a 16th clock into Reset |
| `31-simple` | Technobear's example: a saw drone. **Loud: turn the output down first** | Nothing |

Each control's CV jack adds to its knob, as on every Nebulae instrument. Pitch follows 1 V/oct, and a Pitch click
returns it to the centre.

## 02_sc_drift: drone / pad
Five detuned voices, a morphing oscillator and a drifting resonant filter.

| Control | Does |
|---|---|
| Pitch + V/oct | Pitch, 1 V/oct (click = C4) |
| Start | Oscillator: saw → pulse → sine |
| Size | Detune spread: unison → wide |
| Density | Filter cutoff (80 Hz – 12 kHz) |
| Window | Filter resonance |
| Overlap | Drift depth: the filter and pulse width move |
| Speed (encoder) | Drift rate (slow ↔ fast) |
| Blend | Level |
| Freeze | Sub-octave on/off |
| Source | Chord: adds a fifth and an octave |
| Reset | Swell: the sound dips and blooms back |

Try: Start fully clockwise (sine), Density low, Freeze on for a deep sine drone. Start at noon (pulse), Window up,
Overlap up and Speed slow for a moving resonant pad.

## 03_sc_strike: plucked string
Karplus-Strong string with a pluck-position comb and a wooden body.

| Control | Does |
|---|---|
| Reset (button or gate) | Pluck. A clock or trigger sequence into Reset plays it |
| Pitch + V/oct | Pitch, 1 V/oct (click = C4). A sequencer into Pitch CV + a gate into Reset = a melody |
| Size | Decay (0.3 – 20 s) |
| Density | Brightness of the pluck |
| Window | Body: dry string → resonant wooden body |
| Start | Pluck position: thin (near the bridge) → round (middle) |
| Overlap | Second string: detune and stereo width |
| Record | Auto-pluck on/off (internal clock) |
| Speed (encoder) | Auto-pluck rate (0.5 – 16 per second) |
| Freeze | Sustain: the string rings on |
| Source | Chord: adds a fifth |
| Blend | Level |

## 04_sc_cloud: granular input
A 4-second buffer records the input all the time, and grains read it back pitched and scattered.

| Control | Does |
|---|---|
| Audio in | The source (stereo summed to mono) |
| Start | How far back the grains read (just recorded → 4 s ago) |
| Size | Grain length (20 – 500 ms) |
| Density | Grains per second (1 – 80). The last tenth gives random (dense) grains instead of regular |
| Window | Position scatter around Start |
| Pitch + V/oct | Grain pitch, 1 V/oct (click = original pitch) |
| Overlap | Stereo spread of the grains |
| Speed (encoder) | Pitch scatter: centre (1×) = none; either way = more random detune |
| Blend | Dry / wet |
| Freeze | Stop recording: the buffer holds what it has |
| Reset | A burst of grains |
| Source | Reverse: grains play backwards |

Try: patch a melody in, Blend fully wet, Density at noon, Size small, then Freeze and play with Start and Pitch.

## 05_sc_pattern: generative sequencer
The full guide is in the manual (`docs/manual/18_sc_pattern.md`); the design and the clock in `docs/SC_PATTERN.md`.
Pitch = root, Start = scale, Size = length, Density = hits, Overlap = mutation, Window = tone, Blend = space,
Speed = tempo (free) / swing (clocked); Reset = 16th clock (scheduled ahead: on time despite the 32 ms latency),
Freeze = lock, Record = mutate, File = home (held: store), Source = voice set B. Tests:
`python tools/sc_pattern_tests.py` (logic in sclang, an NRT render, and the live clock with real OSC pulses).

## How they were tested
`python tools/sc_nrt_tests.py` renders each patch in SuperCollider 3.10.4, the module's version, on the PC, with
scripted knob moves, and checks the audio:
- no NaN; peak under the limiter;
- drift: pitch at C4 and one octave up within 1.3 cents; the sub-octave; the swell;
- strike: each pluck in tune within 3 cents (C4, F#4, C3); the decay; auto-pluck rate; sustain;
- cloud: grains follow the input pitch; one octave up; no output once the input stops; Freeze holds the buffer.

`python tools/sc_osc_tests.py` runs each patch live in SC 3.10.4 on the PC. The firmware's own `scsender.py` drives
it, and the test reads every control back from the running synth. (This test found a bug in the first versions of
02–04: they stored the synth as `~neb.synth`, and every control was lost. Fixed 2026-11-11.)

PC and module renders matched exactly in the SC probe, so these results carry over. What only the module can tell:
CPU load, the 5 ms control timing, and how it feels.

## Writing your own
Copy `02_sc_drift.scd`. Every control arrives as OSC `/neb/<name> <value>` on port 3000 (Technobear-compatible).
The patch sends each one to the synth argument of the same name, so you only write the SynthDef and its mapping:
- `pitch` 0–1 with 0.6 = click: `60 + (pitch - 0.6) * 60` semitones = 1 V/oct;
- `speed` 0.625 = 1×, 0.5 = stop;
- the knobs 0–1;
- `freeze`, `record`, `source` are 0/1 latches;
- `reset` is a trigger, which the patch sends as `t_reset`.

`_`-prefixed `.scd` files are hidden from the selector (helpers). Check a new file with
`python tools/sctest.py check sc/x.scd`, then `python tools/sc_osc_tests.py sc/x.scd`.

Watch out with Events (`~neb = ()`): a key with the same name as an Event method calls the method instead. `synth`,
`set`, `play`, `stop`, `free`, `group` and `release` are all methods. Keep the Synth in a plain `~nebSynth`.
