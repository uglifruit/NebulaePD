# Bluetooth storyteller: the Nebulae as a Bluetooth keyboard

The goal: a granular-looper instrument that makes the Nebulae pair with a Windows PC **as a Bluetooth keyboard**,
then types, in chatty English, what is happening to it. For example: "[1:05] Someone just pushed the density up,
things are getting crowded." The plan was approved 2026-11-11. It comes in three stages, each tested on hardware
before the next:
1. **Probe:** can this Pi 4 run its Bluetooth chip without BlueZ?
2. **Keyboard:** pair with the PC; it types a hello line every 10 s.
3. **Storyteller:** `bt_storyteller.instr`, the granular looper plus the narrator. Built after 1–2 work.

Stages 1 and 2 are one instrument, `bt_test.instr`.

## Safety
- **Nothing is installed on the SD card** and the firmware is unchanged. Everything runs from RAM
  (`/dev/shm/neb_bt`) and from the stick's `bt_keyboard/` folder. Works on uf2 and on stock.
- **Bluetooth is on only while a bt instrument is loaded.** Loading another one switches the chip off within
  ~1 s. WiFi is never touched.
- **The chip's power line is never guessed.** The Pi 4 switches the Bluetooth chip through the Pi firmware's GPIO
  expander. Its other lines switch WiFi, the power LED, a global reset and the SD card power.
  - `btkbd` uses only the line the device tree names `BT_ON` on that expander. On this module's device tree it is
    line 0, firmware GPIO 128, the same line the kernel's own (disabled) Bluetooth node uses.
  - It refuses to run, touching nothing, unless every check passes:
    - the model is a Pi 4;
    - no console is on the Bluetooth UART;
    - the kernel isn't running Bluetooth;
    - `/dev/ttyAMA0` is uart0 on GPIO 32/33;
    - no other process has the UART open;
    - there is exactly one `BT_ON`;
    - the firmware file exists.
  - `bt/tests/test_btkbd_checks.py` proves this against 15 fake device trees, one of them matching this module's.
- If anything fails, the instrument still passes audio and plays one low tone.

## What it's made of
| Part | What it does |
|---|---|
| `bt/btkbd/` | `btkbd`, a classic Bluetooth HID keyboard on BTstack v1.8.3 (pinned), adapted from BTstack's archived Raspberry Pi port for the Pi 4 |
| `bt/run.sh` | started by the instrument through `systemd-run`: copies the programs into RAM, runs the probe, then the keyboard; saves the logs and the pairing to the stick |
| `instr/bt_test.instr` | stage 1–2 test: audio passes through, the Bluetooth state as quiet sounds |
| `tools/btbuild.sh` | WSL build: static ARM binary (any glibc), reproducible sha256; runs the keymap and device-tree tests |

`btkbd` in more detail:
- **UART:** the CYW43455 on `/dev/ttyAMA0`.
- **Firmware:** the card's `/usr/lib/firmware/updates/brcm/BCM4345C0.hcd` (checked in the SD image).
- **Flow control:** this module's device tree routes only TX/RX to the chip. If the Pi firmware has set GPIO 30/31
  to CTS/RTS, read-only from `/dev/gpiomem`, it uses flow control at 921,600 baud. Otherwise it runs without, at
  460,800, as Raspberry Pi OS's `btuart` does in that case.
- **Pairing:** "Just Works", so Windows asks for no PIN.
- **After pairing:** it is no longer discoverable and only reconnects to that PC.
- **Typing:** only characters that are identical on UK and US keyboards: letters, digits, space, Enter and
  `. , ! ? ( ) - : % '`.

## Stage 1–2 test: `bt_test.instr`
**Copy to the stick root** (from `firmware/dist/stage_bt/`):
- `bt_test.instr`;
- the **`bt_keyboard`** folder (`btkbd`, `run.sh`, `README.txt`).

**On the module:**
1. Load **`bt_test`** from the Csound user bank (Speed anticlockwise; check the cheat sheet).
2. Listen. Audio passes through, and every 4 s:
   - **two soft blips** = waiting to be paired: the probe passed and the keyboard is on;
   - **one long low tone** = failed: stop here and bring back `bt_keyboard/probe.txt` and `log.txt`.

**On the Windows PC:**
1. Go to Settings → Bluetooth & devices → Add device → Bluetooth.
2. Choose **Nebulae** (it may first show as "Nebulae" or as its address). No PIN is needed.
3. The module plays a **rising chime** when it connects.
4. Open Notepad and click into it. Every 10 s, **"Hello from the Nebulae. This is line N."** appears.

**Then check:**
- [ ] Load another instrument: within a few seconds the PC shows Nebulae as disconnected.
- [ ] Load `bt_test` again: **one soft blip** every 4 s (reconnecting), then the chime and the hello lines,
      without pairing again.
- [ ] Power the module off and on, then load `bt_test`: it reconnects by itself (the pairing is on the stick in
      `bt_keyboard/pairing.tlv`).
- [ ] The typed text is right on a UK layout (letters, digits, full stops).

**Bring back:** `bt_keyboard/probe.txt`, `bt_keyboard/log.txt`, and which sounds you heard.

**To pair with a different PC:** delete `bt_keyboard/pairing.tlv` on the stick and remove "Nebulae" from the
old PC.

## Stage 3: the storyteller, `bt_storyteller.instr`
**Owner's guide: `docs/STORYTELLER.md`** (pairing, reading it, `settings.txt`, editing the voice, logs).

The factory granular looper (copied verbatim by `tools/storyteller.py`) plus the storyteller's ears. Load it from
the Csound user bank; once the PC connects, open Notepad. Each observation is typed as two lines:

```
[1:39 heard 94 seconds ago: in -32 > -26 dB, 231 > 152 Hz, lows 78% > 93% / in -26 dB, out -33 dB, 153 Hz, lows 93%, calm]
I know this. I heard it 94 seconds ago. There is more weight underneath. The edges have softened.
```

- **The [data] line** is the underlying input:
  - the time since load;
  - what was noticed;
  - after the `/`, the input level, the output level, the input's brightness (spectral centroid, Hz), the share of
    low end (below 160 Hz), and the mood (calm or busy).

  `bt_keyboard/settings.txt` sets them to `full`, `short` (without the part after the `/`) or `off`, plus the
  pace (`pace`, seconds between observations, default 3.5) and the share of codas (`coda`, %). An empty file named
  `hide_data` still means `data = off`.
- **The poem line** comes from `bt/phrases.py`: 343 lines in 94 pools, picked like a shuffled deck so nothing
  repeats until a pool is used up. Edit or add lines freely, using only the characters listed at its top.
  `bt/tests/test_narrator.py` checks every line.

What it notices (`bt/narrator.py`):
| | |
|---|---|
| Knobs | each move as from > to, how long, reversals. Kinds: indecision (back and forth), small, big, to the top or bottom, back to an earlier setting, the first touch of each control, several at once. Pitch moves as intervals (octave, fifth, ...); speed through backwards, stopped and normal |
| CV | a control moving by itself: a wave (with its period), steps (a sequence: a jump after a plateau), or wandering |
| Buttons and gates | Freeze, Record, Source, File (next file), the hidden layer (Source held), Reset as a single press or a burst |
| Pulses | on the Reset gate and in the input's onsets: regular, loose or irregular, the tempo, faster or slower, stopped |
| Sound | a transient after calm or silence, silence (20 s, 60 s, then every 3 minutes), sound arriving, gradual brightening or darkening, more or less low end, louder or softer, the output louder than the input, frozen and alone |
| Memory | a sound heard more than 45 s before, back after something else: "I recognise this sound", and how it differs (lows, brightness, level, tempo) |
| Time | idle musings when nobody touches it; minutes together (5, 15, 30, ...) |

**Pacing.** One observation at a time, at least 3.5 s apart (`pace` in `settings.txt`) (1 s for urgent ones: transients, the greeting), and
never while the previous one is still being typed (about 28 characters a second). The most important pending
observation goes first; stale ones are dropped after 12 s.

**CPU.** The instrument's part (`instr 98`): three level followers, one low-pass filter, a 1024-point centroid FFT
four times a second, and change checks on 23 controls, written to a RAM file. `tools/story_sim.py` renders a scripted
150 s performance through the real instrument in Csound: **+7% CPU** over the plain looper (28.6 s against 26.7 s
of CPU for 150 s of audio on the PC), about 1% of one PC core. The state cues read the Bluetooth state from a
small file once a second through a GEN23 table, so no process is started (`bt_test` uses `system_i`).
`narrator.py` runs as its own process at a 10 Hz tick.

**Tests.**
- `python bt/tests/test_narrator.py` (30 tests): phrases, the pacing, the live file loop, Python 2 syntax, and every
  detector with scripted events.
- `wsl -u andy -- python3 tools/story_sim.py`: the whole chain in Csound 6.18, with the story it tells in
  `firmware/dist/story_sim/story.txt`.
- On the module, `run.sh` compiles `narrator.py` and `phrases.py` with the module's Python 2.7 before starting;
  a failure gives the low tone. A crash is written to `bt_keyboard/narrator.log`.

**Stage 3 test (owner).** Copy `bt_storyteller.instr` and the updated `bt_keyboard/` folder (now with
`narrator.py` and `phrases.py`) to the stick. Load `bt_storyteller`, wait for the chime, open Notepad. Then:
- [ ] turn knobs, slowly and quickly, back and forth;
- [ ] patch an LFO and a sequencer into CV inputs;
- [ ] send a clock to Reset;
- [ ] play something with a pulse into the input, then stop it for a minute;
- [ ] bring the first sound back.

Bring back `narrator.log` and `log.txt` from `bt_keyboard/`, and the Notepad text (or what felt wrong, slow or
dull).

## Licence
BTstack (bluekitchen) is free "solely for personal benefit", not for any commercial purpose (its LICENSE,
condition 4). That fits this private project; a product would need BlueKitchen's commercial licence. The
Bluetooth firmware is the card's own file and isn't redistributed.

## Status
- 2026-11-11: stages 1–2 built and tested offline:
  - `btkbd` builds (static ARM, 555 KB, reproducible sha256);
  - keymap test OK (256 checks);
  - device-tree checks OK (15 cases, including this module's real `bcm2711-rpi-4-b.dtb` layout);
  - `bt_test.instr` compiles in Csound 6.18, and its four state sounds were measured in a render.
  Awaiting the first hardware run.
- 2026-11-11, first hardware run: long low tone.
  - `probe.txt`: every check passed on the module;
    - the Pi firmware does set GPIO 30/31 to CTS/RTS, so it used flow control;
    - BT_ON was line 0 = GPIO 128 and was already on before btkbd ran.
  - Then the chip never answered BTstack's HCI Reset (resent every 200 ms) over 25 s.
  - Next: `btkbd --diag` (run by `bt_test` before the probe, written to `diag.txt`):
    - mailbox status checked, line config and state read back on every switch;
    - three power cycles with longer delays;
    - a raw HCI Reset at 115200 with and without flow, and at 921600 and 3000000, reporting CTS and the reply bytes.
  - Also: the chip gets 300 ms to boot after power-on before BTstack starts.
- 2026-11-11, second hardware run: **it works.** The owner's PC paired and Notepad shows "Hello from the Nebulae".
  - `diag.txt`: as found at boot, BT_ON is already high (output) and CTS is up, but the chip doesn't answer.
  - After a power cycle (200 ms off), it answers HCI Reset at 115200 within 100 ms, with and without flow. So
    the first build's 100 ms off with no wait before talking was the problem; it now gets 300 ms off and 300 ms
    to boot.
  - BTstack then reads BCM4345C0 (LMP subversion 0x6119), loads the firmware, and runs at 921600 with flow
    control. Address B8:27:EB:EA:85:1D. `pairing.tlv` was saved to the stick.
  - Found: a SIGTERM (systemctl stop, when bt_test is loaded again) killed btkbd with the chip still on. The
    cause is BTstack's btstack_signal.c, which waits for SIGINT only and replaces the mask per call. btkbd now
    uses its own signal pipe, so stopping is always a clean shutdown.
- 2026-11-11: **stage 3 built** (owner: poetic and responsive, showing the underlying data, a large pool of
  phrases; awareness of knobs, CVs, regular and irregular pulses; enough CPU left for the processing).
  - `bt_storyteller.instr` (generated by `tools/storyteller.py`), `bt/narrator.py`, `bt/phrases.py`.
  - `btkbd` now types `/ ; = + [ ] < > *` too (identical on UK and US layouts) and writes `state.code`.
  - Tested offline: `test_narrator.py` 24 OK; `story_sim.py` in Csound 6.18 tells a coherent 25-observation story
    of the scripted performance; +7% CPU.
  - Csound 6.11 checked in its source:
    - `fprintks` is line-buffered but has no `%s`, hence one format string per control;
    - `readfi` can't re-read a file from a reused instance, hence GEN23;
    - centroid, monitor, event_i, ftgentmp and strindex all exist.
  - Staged in `firmware/dist/stage_bt/` and copied to the stick (`pairing.tlv` kept). Awaiting hardware.
- 2026-11-11: **stage 3 works on hardware**: the owner loaded bt_storyteller and it narrated to the PC. No tuning
  notes or logs yet.
- 2026-11-12: owner's guide `docs/STORYTELLER.md`; `settings.txt` (data full/short/off, pace, coda); `run.sh`
  keeps the three previous `narrator.log` / `log.txt` (the stick's last log was a 7 s run that had overwritten
  the working session). Not yet on hardware.
