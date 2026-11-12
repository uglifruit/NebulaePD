# pearls — Mutable Instruments Beads on the Nebulae

Pearls is Mutable Instruments **Beads**, ported to the Nebulae by XponentOneAudio (MIT), with the original Beads DSP
and a few extras. It is a granular processor: it records the input into a buffer all the time and plays **grains**
(short snippets) from it. Density decides how many and how regularly, Time how far back they read, Size how long
they are, Shape their envelope, and Pitch their pitch. Fully clockwise, Size turns it into a delay. Feedback,
dry/wet and reverb come after the grains. Freeze stops the recording. With no input, Source turns it into a
wavetable synth.

It is in the **Csound user bank** as `pearls`. It needs `pearls.instr` and the `csound_plugins` folder (with
`libpearls.so`) on the stick. The first load after installing uf2 installs the plugin and takes a few seconds
longer. Features marked *new* came in Pearls 5–8 and haven't been tested on hardware by their author yet.

## Knobs and encoders
Each CV jack adds to its knob.

| Nebulae | Pearls (Beads) |
|---|---|
| **Start** | TIME: how far back in the buffer the grains read |
| **Size** | SIZE: grain length. Left of about 11 o'clock, grains play backwards. **Fully clockwise = delay mode** |
| **Window** | SHAPE: grain envelope, from sharp to smooth |
| **Density** | DENSITY. **12 o'clock = no grains.** Clockwise = more, at random times. Anticlockwise = more, regularly |
| **Pitch** + 1 V/oct | PITCH, ±48 semitones. Click = unison |
| **Overlap** | FEEDBACK |
| **Blend** | DRY/WET |
| **Speed** | REVERB amount: turn clockwise from 0. Click toggles a light reverb on/off |

## Buttons and gates
| Nebulae | Pearls |
|---|---|
| **Freeze** button / gate | FREEZE: stops recording, the grains keep playing the buffer (the gate holds it while high) |
| **Reset** button | SEED: a tap plays one grain (in delay mode, tap tempo). **Re-lock** the grain generator: hold 4 s and release, or press Freeze while holding |
| **Reset** gate | SEED input: each trigger plays a grain; a clock plays grains in time (counts as patched while edges arrive, 4 s timeout) |
| **File** button / gate | QUALITY, on release: hi-fi → cold digital → sunny tape → scorched cassette → hi-fi. **Hold 1.5 s**: restart the automatic input gain |
| **Source** button / gate | Wavetable synth mode on/off |
| **Record** button | TAP TEMPO *new*: tap 2+ times to clock the grains; later taps re-align; hold 1 s to stop |
| **File held + Record** | PITCH SCALE *new*: off → chromatic → major → minor → major pent. → minor pent. → octaves + fifths → octaves → off |
| **EOL** out | A gate per grain (in delay mode, per delay tap) |

## LEDs
| LED | Shows |
|---|---|
| Reset | Grain activity (dim while locked and idle) |
| Freeze | Frozen (button, gate, or after loading a sample) |
| File | Lit while pressed. **Slow blink**: the automatic gain is measuring the input (~5 s after start or a new input). Fast blink: loading or saving |
| Record | Tap-tempo beat |
| Encoder LEDs, after a quality change | hi-fi = white, cold digital = cyan-green, sunny tape = amber, scorched cassette = purple |
| Pitch LEDs, after a scale change | off = white, chromatic = red, major = amber, minor = yellow, maj. pent. = green, min. pent. = cyan, oct + 5th = blue, octaves = magenta |
| All encoder LEDs after load/save | green = loaded, blue = saved, red = failed |

## Secondary layer (hold Source)
| Nebulae | Pearls |
|---|---|
| Start / Size / Window | Randomness of TIME / SIZE / SHAPE (fully anticlockwise = none) |
| Pitch encoder | Randomness of PITCH |
| Density | Input gain: fully anticlockwise = automatic (default), else 1×–40× manual |
| Overlap | Reversed grains *new*: more reversed towards clockwise |
| Blend | Stereo spread *new* |
| Speed encoder | The Nebulae input level (as usual) |
| Freeze | Randomness shape: off = even, on = mostly small with occasional big jumps |
| Record | Mono buffer: left input only, twice the time |
| File | **Load** the next WAV from the stick into the buffer *new* (it loads frozen) |
| Reset | **Save** the buffer to the stick as `pearls_001.wav`, … *new* |

Changing quality, mono or synth mode **clears the buffer**, as on Beads. While frozen, those changes wait until
you unfreeze, so a loaded sample is safe. Recording time runs from about 4 s (hi-fi stereo) to about 32 s
(scorched cassette, mono). The quality and a frozen buffer survive a power cycle.

## Quick start
1. Patch audio in. Blend at noon. Watch the File LED blink slowly for a few seconds (gain measuring).
2. Density a little clockwise: random grains. A little anticlockwise: a steady stream.
3. Turn Start (how far back), Size (short clicks to long smears; left of 11 o'clock = reversed) and Window.
4. Freeze, then play with Pitch and Start on the frozen buffer.
5. Size fully clockwise for the delay; Reset taps set its time.
6. Tap File through the four qualities; hold Source + File to load a WAV from the stick.
