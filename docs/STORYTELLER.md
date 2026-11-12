# bt_storyteller: the Nebulae tells your PC what is happening to it

**A proof of concept.** The sound is the factory **granular looper**, unchanged. Behind it, the Nebulae's Pi 4
switches on its own Bluetooth radio, pairs with your PC as a **Bluetooth keyboard**, and types what is happening to
it: knob moves, CV, buttons, pulses, sound and silence. Each observation comes as a line of raw data, then a line of
poetry. It proves the Nebulae can talk Bluetooth with nothing installed on the SD card, while an instrument runs at
full quality. Everything it needs comes from the USB stick and runs from RAM. Bluetooth is only on while this
instrument is loaded. The engineering is in `docs/BLUETOOTH.md`.

## 1. On the stick
| Where | What |
|---|---|
| Stick root | `bt_storyteller.instr` (the instrument; Csound user bank) |
| `bt_keyboard/` | `btkbd` (the keyboard program), `run.sh` (starts it), `narrator.py` (the storyteller), `phrases.py` (its voice), `settings.txt` (data lines, pace), `README.txt` |
| Written by the module | `pairing.tlv` (your PC), `narrator.log` (everything it typed), `log.txt` (the Bluetooth side), and the previous three runs of each as `.1`, `.2`, `.3` |

## 2. First time: pairing
1. Load **bt_storyteller**: hold Speed, Speed anticlockwise (Csound user bank), then find it with the Pitch pages
   (see the bank sheet, `nebulae_banks.txt` on the stick).
2. The looper plays as usual. Every few seconds you hear a **soft double blip**: it is waiting to pair.
3. On the PC: **Settings → Bluetooth & devices → Add device → Bluetooth → "Nebulae"**. No PIN is asked.
4. A **rising chime**: connected. The pairing is saved to the stick (`pairing.tlv`).
5. Open **Notepad** and click in it. **It types into whichever window has the focus**, so keep Notepad in front
   (and nothing important, like a terminal or a chat box).

After that it reconnects to the same PC by itself each time you load it. It is not discoverable once it has a PC,
so nobody else can pair with it.

A **low tone** means it failed. The looper keeps playing; `bt_keyboard/log.txt` says why.

To pair with a different PC: delete `pairing.tlv` from the stick and remove "Nebulae" from the old PC's Bluetooth
devices.

## 3. Playing it
The panel is the factory granular looper (see Qu-Bit's manual). Every control is also an input to the storyteller:

| It notices | How |
|---|---|
| **Knobs** | each move: from → to, how long it took, reversals. Indecision (back and forth), small, big, to the top or bottom, back to an earlier setting, the first touch of each knob, several at once. Pitch moves as intervals (an octave, a fifth); Speed through backwards, stopped, normal |
| **CV** | a knob moving by itself: a wave (with its period), steps (a sequence) or wandering |
| **Buttons and gates** | Freeze, Record, Source, File (next file), the hidden layer (Source held), Reset as one press or a burst |
| **Pulses** | on the Reset gate and in the input: regular, loose or irregular, the tempo, faster, slower, stopped |
| **Sound** | a sudden transient after calm, silence (20 s, 60 s, then every 3 min), sound arriving, brighter or darker, more or less low end, louder or softer, its own voice louder than the input, frozen and alone |
| **Memory** | a sound it heard over 45 s ago coming back: "I recognise this sound", and what is different now |
| **Time** | musings when nobody touches it; how long you have been together |

Things to try: turn a knob slowly, then quickly, then back and forth. Patch an LFO and then a sequencer into a CV
input. Clock Reset regularly, then irregularly. Play into it, stop for a minute, then bring the first sound back.

## 4. Reading it
```
[1:39 heard 94 seconds ago: in -32 > -26 dB, 231 > 152 Hz, lows 78% > 93% / in -26 dB, out -33 dB, 153 Hz, lows 93%, calm]
I know this. I heard it 94 seconds ago. There is more weight underneath. The edges have softened.
```
- **The data line**, in brackets: the time since the instrument loaded (m:ss), then what it noticed. After the `/`
  is the sound at that moment: input level, output level, brightness (the spectral centroid, in Hz), the share of
  low end (below 160 Hz), and the mood (calm or busy, from how much has been touched in the last 30 s).
- **The poem**: a line from its voice (`phrases.py`), sometimes with a closing musing (a "coda").

It writes one observation at a time, at about 26 characters a second, and drops anything that has gone stale
(after 12 s) rather than fall behind.

## 5. Settings: how much data, how chatty
Edit `bt_keyboard/settings.txt` on the PC (Notepad is fine), put the stick back and reload the instrument:

| Line | Values | Default |
|---|---|---|
| `data = ` | `full`: time, what happened and the sound, as above. `short`: time and what happened only, e.g. `[1:05 density 0.42 > 0.71 in 0.8 s]`. `off`: poetry only | `full` |
| `pace = ` | seconds between observations: `1` = chatty, `10` = thoughtful, `30` = taciturn (urgent ones can still come after 1 s) | `3.5` |
| `coda = ` | percent of lines with a closing musing, `0` … `100` | `20` |

A misspelt line or value is ignored and keeps its default. The first line of `narrator.log` shows the settings it
used. (An empty file named `hide_data` in `bt_keyboard/` still works too: it is the same as `data = off`.)

## 6. Changing its voice: `phrases.py`
Everything it can say is in `bt_keyboard/phrases.py`: 343 lines in 94 pools. Open it in a text editor (Notepad, or
VS Code). Each pool is a list of lines in double quotes, separated by commas:

```python
TRANSIENT = ["Something has interrupted me.", "A shock. What was that?", ...]
```

- **Add, change or delete lines freely.** More lines = fewer repeats: it deals each pool like a shuffled deck, so
  nothing repeats until a pool is used up.
- **Fields** in `{braces}` are filled in: `{name}` / `{Name}` (the control's poetic name, from `NAMES`; capital =
  sentence start), `{dur}`, `{n}`, `{bpm}`, `{period}`, `{interval}`, `{dir}`, `{ago}`, `{diff}`, `{what}`, `{mins}`.
  Use only the fields a pool already uses (the comment above each pool says what it is for).
- `"\n"` inside a line breaks it into a verse.
- **Characters:** only letters, digits, space and `. , ! ? ( ) - : % ' / = + < > * ; [ ]`. These type the same on UK
  and US keyboards. Anything else (quotes inside a line, `@ # ~ | & _ ^`, accents) is typed as a space.
- Keep the pool names (the CAPITALS) and the brackets as they are.
- Some pools are worth knowing: `NAMES` (how it names each knob), `UP` / `DOWN` (per knob), `GREET` (its first
  words), `CODA` (the closing musings), `IDLE_SOUND` / `IDLE_SILENT` (when nobody touches it), `RECOGNISE` and
  `DIFF` (memory).

**If you break it**, the looper still plays, but it gives the low tone and types nothing; `log.txt` says
"narrator.py or phrases.py does not compile". Usually a missing comma or quote. To check on the PC first: in the
repo, `python bt/tests/test_narrator.py` checks every line, or at least `python -m py_compile phrases.py`.

## 7. Logs and what to bring back
- `narrator.log`: every observation it made, with times. `log.txt`: the Bluetooth side (pairing, connecting,
  shutting down). The three runs before are kept as `narrator.log.1` … `.3` and `log.txt.1` … `.3`, so a short
  test load doesn't wipe a good session.
- For tuning, bring back those files plus what felt wrong: too chatty, too slow, observations that ring false,
  lines that get tired.

## 8. Limits
- A keyboard can only type, so the PC never talks back. It can't read a reply.
- UK/US-safe characters only (no quotes or symbols).
- Tested with Windows 10 and a UK layout.
- The clock counts from when the instrument loaded (the module has no real-time clock).
- It runs only while `bt_storyteller` is loaded. Loading another instrument disconnects the PC and turns the radio
  off within a few seconds.
- CPU: the listening adds about 7 % to the looper, so the looper itself is unaffected.
- `bt_test` (the stage 1–2 check: pairing plus a hello line every 10 s) is still on the stick for diagnosing
  Bluetooth problems.
