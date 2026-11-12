# Pearls on the Nebulae: guide and test checklist

Pearls is Mutable Instruments **Beads**, ported to the Nebulae by XponentOneAudio (MIT). It has the original Beads
DSP, plus a few extras. In uf2 it is the Csound instrument **`pearls`** in the user bank (Speed anticlockwise). Its
provenance is in `docs/PEARLS.md`.

Beads in one paragraph: a granular processor. It records the audio input into a buffer all the time and plays
**grains** (short snippets) from it. Density decides how many and how regularly, Time how far back they read, Size how
long they are, Shape their envelope, and Pitch their pitch. Fully clockwise, Size turns it into a delay. Feedback,
dry/wet and reverb sit after the grains. Freeze stops the recording. Without input, Source turns it into a wavetable
synth.

Features marked *(new)* came in Pearls 5–8 and haven't been tested on hardware by their author yet. Please note
anything odd about them.

## 0. Before you start
- The stick root needs `pearls.instr` and the `csound_plugins` folder (with `libpearls.so`) from
  `firmware/dist/stage_uf2/2_install/`. Leave them there.
- Patch a stereo (or mono into left) **audio source into the inputs**: a sequence, a drum loop, a voice.
- Optional: a clock or trigger source for the Reset gate, and a V/oct sequence for Pitch CV.
- Optional for the sample tests: a few WAV files in the stick root (any format, any rate).

## 1. Install check
1. After installing uf2_1, power on with the stick in.
2. Load any instrument once. The first load installs the plugin and takes a few seconds longer, once.
3. On the PC, `neb_log.txt` on the stick should have a line
   `uf2: Csound plugin libpearls.so installed (9ccae0ddbba0): ['OK: pearls loaded and running (output rms …)']`.
   - "NOT installed, its check failed" → stop, bring the stick back.
   - No line at all → the `csound_plugins` folder is missing from the stick.

## 2. Panel

**Knobs and encoders** (each CV jack adds to its knob)

| Nebulae | Pearls (Beads) |
|---|---|
| **Start** | TIME: how far back in the buffer the grains read |
| **Size** | SIZE: grain length. Left of about 11 o'clock, grains play backwards (as Beads). **Fully clockwise = delay mode** |
| **Window** | SHAPE: grain envelope, from sharp to smooth |
| **Density** | DENSITY. **12 o'clock = no grains.** Clockwise = more, at random times. Anticlockwise = more, regularly |
| **Pitch** + 1 V/oct | PITCH, ±48 semitones. Click = unison (the recorded pitch) |
| **Overlap** | FEEDBACK |
| **Blend** | DRY/WET |
| **Speed** | REVERB amount: turn clockwise from speed 0. Click toggles a light reverb on/off |

**Buttons and gates** (the File button is the one Pearls' own notes in `pearls.instr` call "Next")

| Nebulae | Pearls |
|---|---|
| **Freeze** button | FREEZE on/off: stops recording, grains keep playing the buffer |
| **Freeze** gate | Frozen while the gate is high |
| **Reset** button | SEED: a tap plays one grain (in delay mode, a tap tempo). **Re-lock** the grain generator: hold 4 s and release, or press Freeze while holding |
| **Reset** gate | SEED input: each trigger plays a grain; a clock plays grains in time. Counts as patched while edges arrive (4 s timeout) |
| **File** button / gate | QUALITY, on release: hi-fi → cold digital → sunny tape → scorched cassette → hi-fi. **Hold 1.5 s**: restart the automatic input gain |
| **Source** button / gate | Wavetable synth mode on/off |
| **Record** button | TAP TEMPO *(new)*: tap 2+ times to clock the grains. Later single taps re-align the beat; hold 1 s to stop |
| **File held + Record** | PITCH SCALE *(new)*: off → chromatic → major → minor → major pent. → minor pent. → octaves + fifths → octaves → off |
| **EOL** out | A gate per grain (in delay mode, per delay tap) |

**LEDs**

| LED | Shows |
|---|---|
| Reset | Grain activity (dim while locked and idle) |
| Freeze | Frozen (button, gate, or after loading a sample) |
| File | Lit while pressed. **Slow blink**: the automatic gain is measuring the input (~5 s after start or a new input). Fast blink: loading or saving |
| Record | Tap-tempo beat (dim between beats) |
| Encoder LEDs, 1.5 s after a quality change | hi-fi = white, cold digital = cyan-green, sunny tape = amber, scorched cassette = purple |
| Pitch LEDs, 1.5 s after a scale change | off = white, chromatic = red, major = amber, minor = yellow, maj. pent. = green, min. pent. = cyan, oct + 5th = blue, octaves = magenta |
| All encoder LEDs after load/save | green = loaded, blue = saved, red = failed |

**Secondary layer: hold Source**

| Nebulae | Pearls |
|---|---|
| Start / Size / Window | Randomness of TIME / SIZE / SHAPE (fully anticlockwise = none) |
| Pitch encoder | Randomness of PITCH |
| Density | Input gain: fully anticlockwise = automatic (default), else 1×–40× manual |
| Overlap | Reversed grains *(new)*: anticlockwise = as Beads, clockwise = more reversed, all at fully clockwise |
| Blend | Stereo spread *(new)*: anticlockwise = as Beads, clockwise = wider |
| Speed encoder | The Nebulae input level (as usual) |
| Freeze | Randomness shape: off = even, on = mostly small with occasional big jumps |
| Record | Mono buffer: left input only, twice the time |
| File | **Load** the next WAV from the stick into the buffer *(new)* |
| Reset | **Save** the buffer to the stick as `pearls_001.wav`, … *(new)* |

Changing quality, mono or synth mode **clears the buffer**, as on Beads. While frozen, those changes wait until you
unfreeze, so a loaded sample is safe. Recording time is about 4 s (hi-fi stereo) up to about 32 s (scorched cassette
mono).

## 3. Test checklist
Tick each step. Where it says "expect", that's what Beads does.

**A. Basics**
- [ ] Load `pearls`. Audio passes through (Blend fully clockwise = all wet, so start at noon).
- [ ] File LED blinks slowly for a few seconds: the automatic gain is measuring.
- [ ] Density at 12 o'clock: no grains (dry only, plus reverb/feedback tails).
- [ ] Density a bit clockwise: random grains appear; further = denser. Reset LED flickers with grain activity.
- [ ] Density a bit anticlockwise: grains at a steady rate; further = faster.
- [ ] Start: grains read further back as you turn it.
- [ ] Size: short clicks → long smears. Left of ~11 o'clock: reversed grains.
- [ ] Window: grain envelope sharp → smooth.
- [ ] Pitch: grains transpose; click returns to unison. 1 V/oct into Pitch CV transposes in octaves.
- [ ] Overlap (feedback), Blend (dry/wet), Speed (reverb): each does what it says; Speed click toggles light reverb.

**B. Freeze**
- [ ] Freeze button: LED on, the buffer stops recording (stop the input: grains keep playing the old audio).
- [ ] Freeze again: recording resumes.
- [ ] A gate into Freeze: frozen while high, released when low.

**C. Seed (Reset)**
- [ ] Density at 12 o'clock, tap Reset: one grain per tap.
- [ ] A clock into Reset: grains in time. Density clockwise = chance of a grain per beat; anticlockwise = divides
  the clock.
- [ ] Unplug the clock: after ~4 s it goes back to its own grains.
- [ ] Hold Reset 4 s and release: the generator re-locks (Reset LED dim while idle).
- [ ] EOL out into a module/scope: a gate per grain.

**D. Quality (File)**
- [ ] Each File press steps hi-fi → cold digital → sunny tape → scorched cassette; the encoder LEDs flash the
  colour; the sound changes (cleaner → crunchier, longer buffer).
- [ ] While frozen, a File press waits until you unfreeze.
- [ ] Hold File 1.5 s: the slow blink restarts (gain re-measured).

**E. Delay mode**
- [ ] Size fully clockwise: it becomes a delay. Start = delay time, Overlap = feedback.
- [ ] Reset taps set the delay time (tap tempo).
- [ ] EOL gives a gate per delay tap.

**F. Synth mode (Source)**
- [ ] Source on, with no input: a wavetable synth. Pitch plays it (1 V/oct), Overlap (FEEDBACK) picks one of eight
  wavetable banks, Start (TIME) becomes a low-pass filter.
- [ ] Source off: back to processing the input (the buffer is cleared).

**G. Tap tempo (Record)** *(new)*
- [ ] Tap Record 3–4 times: grains (or the delay) follow that tempo; the Record LED blinks on the beat.
- [ ] One more tap later re-aligns the beat. Hold Record 1 s: the clock stops.

**H. Pitch scales (File held + Record)** *(new)*
- [ ] Each combo steps the scale; the Pitch LEDs flash its colour.
- [ ] With Pitch randomness up (Source + Pitch), random grain pitches land on scale notes.
- [ ] Pitch CV near a note boundary doesn't flicker between notes.

**I. Secondary layer (hold Source)**
- [ ] Start/Size/Window/Pitch randomness each add variation.
- [ ] Density fully anticlockwise = automatic gain; turned up = manual gain (louder input into the buffer).
- [ ] Overlap: more grains reversed *(new)*. Blend: wider stereo *(new)*.
- [ ] Record: mono buffer (left input only), noticeably longer.

**J. Samples and memory** *(new)*
- [ ] Source + File: loads the next WAV from the stick. Encoder LEDs green, Freeze LED on (loaded = frozen).
  Grains now play the sample. Press again for the next file.
- [ ] Source + Reset: saves the buffer. Blue flash; `pearls_001.wav` appears on the stick (check on the PC).
- [ ] With no WAVs or no stick: red flash, nothing breaks.
- [ ] Choose a quality, freeze a buffer, wait 10 s, power off and on, load `pearls`: same quality, the buffer comes
  back frozen. One Freeze press releases it.

**K. Living with other instruments**
- [ ] Switch to a Pd patch, a stock Csound instrument and an SC patch, then back to Pearls. Each loads.
- [ ] The granular looper and other Csound instruments behave as before (Pearls' gate and LED changes are only
  active for Pearls).

## 4. What to bring back
- Ticks and notes, especially for the *(new)* items and anything that clicks, drops out or feels laggy.
- The stick's `neb_log.txt` (the `uf2:` lines) and `neb_error.txt` if there is one.
- If something crashed or fell back to the granular looper, say what you did just before.
