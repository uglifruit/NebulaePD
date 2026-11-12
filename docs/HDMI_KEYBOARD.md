# HDMI out and keyboard in: feasibility study (visualiser, tracker, live coding)

Written 2026-11-12. **Nothing is built.** It answers:
- does the Pi 4's HDMI show anything now?
- could it carry a visualiser?
- could HDMI plus a keyboard make a tracker or a live-coding instrument?

Facts marked *(verified)* come from the stock SD image (`SDImage/nebulae_stock_pi4.img`, read offline), the
module's inventories in `firmware/device/`, or the boot command line the module logged in
`bt_keyboard/log.txt`. Everything else is a reasoned estimate.

## 1. What HDMI shows today
- **The boot console and a login prompt, if a monitor is plugged in before power-on.**
  - *(verified)* The kernel command line has `console=tty1`, and `getty@tty1` is enabled. A screen would show the
    kernel's boot messages, then `Arch Linux (tty1)` and an `alarmpi login:` prompt.
  - Nothing of the Nebulae's own appears. Its app is a background service.
- **Nothing if the monitor is connected later.**
  - *(verified)* In the module's logged boot line, the firmware set `bcm2708_fb.fbwidth=0 fbheight=0`. No display
    was attached at that boot, so no framebuffer was set up.
  - `config.txt` has no `hdmi_force_hotplug`, so the Pi only drives HDMI when it finds a screen at power-on.
- **Display mode:**
  - *(verified)* `config.txt` loads no `vc4-kms-v3d` overlay, so it uses the **legacy firmware framebuffer**
    (`/dev/fb0`, 16-bit colour);
  - **the GPU is deliberately starved:** `gpu_mem=16` (the minimum), `gpu_freq=75` MHz, `core_freq=400`, and the
    ARM is held at 1.2 GHz (`arm_freq=1200`). It's probably done for heat and power on the Eurorack rail.
- **What's installed:**
  - *(verified)* Mesa 22.2, SDL2 2.24, libdrm, EGL/GLES, freetype, ncurses, Lua 5.4, `modetest`,
    `/opt/vc/bin/tvservice` and `vcgencmd`.
  - *(verified)* There is no `fbset`, `fbi` or tmux.
  - *(verified)* The kernel has `vc4.ko` (unused without the overlay), `uinput`, the HID drivers and its own
    Bluetooth modules (but no BlueZ daemon).

**Test it, zero risk:** with the module powered off, connect a monitor (micro-HDMI to HDMI; the port nearest the
USB-C is HDMI 0), then power on. Expect scrolling boot text, then the login prompt. Don't log in; there's nothing
to do there. Also check:
- Can you reach the micro-HDMI ports with the module in the case?
- Is a Pi USB port free besides the stick's?

## 2. A visualiser: feasible, no SD-card change
**How:**
- a small static C program, built and launched exactly like `btkbd` (the instrument starts it with `system_i`,
  and it runs from `/dev/shm`);
- it draws straight into `/dev/fb0` on another CPU core;
- the instrument sends it what to draw: levels, spectrum bins, onsets, control values, grain positions. It's
  the storyteller's "ears" again, written to a RAM file or sent over UDP (Pd's `[netsend -u]`, Csound's
  `fprintks` or OSC).

**Cost:**
- In CPU, a few per cent of one core at 640×360 and 30 fps. The firmware can scale a small framebuffer up to the
  monitor.
- The audio engines use essentially one core (Csound, Pd and scsynth are single-threaded), so there is room.

**What it could show:**
- a scope or spectrum;
- the grain cloud (each grain as a dot: position = Start, height = pitch, life = Size);
- the panel state, every knob and CV live, and the alt layer while Source is held;
- loop position and heads for gloop;
- the bank page and the selector;
- the storyteller's text, on screen instead of over Bluetooth.

**Things to handle:**
- the text console on tty1 also draws on `/dev/fb0` (the login prompt, a blinking cursor), so the program must
  switch that console into graphics mode (`KDSETMODE KD_GRAPHICS`) and back on exit;
- the screen must be connected at power-on (see above).

**Not possible without changing the SD card:** GPU-accelerated graphics (OpenGL/SDL with acceleration). That needs
the KMS overlay and more `gpu_mem` in `config.txt`, which breaks the "never touch the SD card" rule and the revert
story. CPU drawing is enough for everything above.

## 3. A keyboard: two ways in
| | USB keyboard | Bluetooth keyboard |
|---|---|---|
| How | The kernel already handles it. The program reads `/dev/input/event*` directly and grabs it (`EVIOCGRAB`), so the keys don't also reach the login prompt | **BTstack as a HID host**, the other side of what `btkbd` does now. BTstack has classic (`hid_host_demo`) and BLE (`hog_host_demo`) host examples |
| Needs | A free Pi USB port, or a small hub on the stick's port. The firmware mounts the stick as `/dev/sda1`, and a keyboard doesn't change that | Nothing new on the card. We already own the radio (BT_ON, firmware, UART: proven by the storyteller) |
| Pairing | none | once. With a screen, it shows the passkey for you to type on the keyboard, as a PC does. Most modern compact keyboards are BLE-only, so BLE (HOGP) support matters |
| Latency | ~1–8 ms | ~10–20 ms (fine for typing and for a tracker) |
| Work | small | moderate: a new mode in `btkbd`, plus testing with your keyboard(s) |

Both give raw key codes. The UK layout mapping is ours to write (the reverse of `bt/btkbd/keymap.c`).
Recommendation: **USB first** for development, then Bluetooth when the instrument deserves to be wireless.

## 4. A tracker instrument: feasible, a real project
- **Shape:**
  - the screen shows the pattern grid: rows of steps and channels of notes, instruments, volumes and effects,
    classic tracker style;
  - the keyboard edits it;
  - the panel performs it:
    - Speed = tempo or swing;
    - knobs = per-channel macros (filter, send, decay, mutes), or a "live column" that records knob moves into the
      pattern;
    - Reset = external clock / step;
    - Freeze / Record / File = play/stop, record, pattern chain.
  - Songs and samples are saved to the stick.
- **Engine:** the tracker program is the sequencer and the screen. A sound engine plays the notes. **SuperCollider
  fits best:**
  - it takes timestamped OSC bundles, so notes are scheduled sample-accurately in spite of its 32 ms latency;
  - one synth per note gives polyphony for free;
  - sample playback, FM7, the AY chip emulation (`docs/SC_IDEAS.md`) and the effects are all there;
  - sclang can start the tracker program itself.

  A Csound version is possible too (`system_i` launches it; score events or OSC carry the notes).
- **Timing:** the tracker keeps its own clock. External sync comes from the Reset gate, which the firmware polls
  every ~5.3 ms (measured), so a few ms of jitter on external clock, and none on the internal clock.
- **CPU:** UI and sequencing take a few per cent. 8 channels of samples and synths in scsynth are well within the
  budget.
- **Work:** the biggest of all our instruments so far:
  - text rendering (an embedded bitmap font);
  - the editor's feel;
  - a song file format;
  - the engine;
  - stick I/O.

  Done in stages, each one usable.

## 5. A live-coding environment: feasible, and cheaper than the tracker once the base exists
- **Shape:**
  - an on-screen editor (the same C program, editor mode) with SC code;
  - a key (e.g. Ctrl+Enter) sends the current block to **sclang**, which already runs on the module in the SC bank.
    sclang reads code from its standard input; that is how editor plug-ins drive it;
  - its output and errors show in a post pane;
  - SC's JITLib (`Ndef`, `Pdef`) is designed for exactly this: redefine a sound or a pattern while it plays;
  - the panel's knobs and CV arrive as OSC as usual, so code can use them;
  - a panic key stops all sound.
- **Why SC:** it is the only engine on the module made for live changes. Csound and Pd can't swap code cleanly
  while running in this firmware, and there is nothing like TidalCycles on the card.
- **Care needed:**
  - bad code can make sclang hang or exit. uf2 then falls back to the granular looper (by design, for crashes),
    so live-coding mode must tell the firmware a stop was on purpose, or restart sclang itself;
  - files are saved to the stick.
- **Relation to Technobear:** his `01-livecoding.scd` did this from a laptop over WiFi. Here it would need no
  laptop and no network.

## 6. Risks and unknowns
| Risk | Check |
|---|---|
| The HDMI or USB ports can't be reached with the module in a case, or the Pi's depth leaves no room for a cable | You look at it (cheap) |
| Power: a monitor draws nothing from the Pi, but a USB keyboard or hub draws 50–500 mA from the module's 5 V | Prefer a plain low-power keyboard; check the Nebulae's supply note in its manual |
| The screen is only set up when present at power-on | Live with it, or add `hdmi_force_hotplug=1`. That is an SD-card change, and only through a firmware update with a revert path |
| The firmware framebuffer with `gpu_mem=16` may refuse large modes | Probe it: H1 below reads `/sys/class/graphics/fb0/` and tries modes |
| The console fighting the program for the screen and keys | Solved by graphics mode + grabbing the keyboard (standard) |

## 7. Suggested stages
- **H0 (you, no code):** a monitor at power-on. Does the boot text appear? Can the ports be reached?
- **H1 `hdmi_probe` instrument:** a Csound instrument + a static helper, like the Bluetooth probe. It records
  the framebuffer size, modes, `tvservice -s` and `/dev/input` to the stick, draws a test card, and shows live
  input meters. No SD change.
- **H2 visualiser:** pick one: a grain-cloud view for the looper, or the storyteller on screen.
- **H3 keyboard:** USB reader first (it shows the keys typed on screen); Bluetooth HID host later.
- **H4:** the shared editor/text base, then **live coding** (smallest step from H3), then the **tracker**.

**Recommendation:** do H0 whenever a monitor is handy; it settles the physical question for free. If the ports
are reachable, H1 + H2 are small and fun. For the big one, build the screen + keyboard + text base once, then
**live coding first** (it reuses sclang and needs little new audio code), and the **tracker** as the full
instrument after.
