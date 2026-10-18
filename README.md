# NebulaePD

Pure Data instruments for the [Qu-Bit Nebulae V2](https://www.qubitelectronix.com/) Eurorack module, plus notes and a
desktop test harness.

- `docs/ARCHITECTURE.md` — hardware/software architecture, constraints, open questions
- `docs/PROTOCOL.md` — control messages (TCP 3000 FUDI), ranges, button semantics
- `docs/DEPLOY.md` — loading patches on the module; testing on a PC
- `instr/` — Csound instruments (template + demos); notes in `docs/INSTR.md`
- `patches/` — `00_template.pd` (start here), `01_drone.pd` (demo using all main controls), `02_echo.pd` (stereo tape echo, below), `03_gloop.pd` (Gloop-style 4-head looper — user guide: `patches/03_gloop_README.md`)
- `lib/nebulae_controls.pd` — standalone control receiver (embedded as a subpatch in each instrument)
- `sim/` — `sim_controls.pd` GUI and `send_fudi.py` TCP sender for testing without hardware
- `tools/instr2csd.py` — wrap a `.instr` into a `.csd` like the module does, for desktop `csound -n` checks
- `tools/gen.py` — generates the `.pd` files above (`python tools/gen.py`); edit this or edit patches in Pd directly
- `reference/` — official Nebulae development PDF; `upstream/` — files copied from
  [QB_Nebulae_V2](https://github.com/Qu-Bit-Electronix/QB_Nebulae_V2) (MIT, © 2019 Qu-Bit Electronix; see `upstream/UPSTREAM_LICENSE`)

Local clones for study (gitignored): `external/QB_Nebulae_V2`, `external/NebulaePatches` (TheTechnobear).

Status: all patches load cleanly in Pd 0.57 headless. **03_gloop is confirmed working on a Pi 4 Nebulae (fw v2.1.2).**
00/01/02 have not been reported on hardware yet. New sessions: start with [`HANDOFF.md`](HANDOFF.md).

## 02_echo — stereo tape echo with freeze
Live-input effect. Vanilla objects only (`delwrite~`/`vd~`/`lop~`/`hip~`/`clip~`), chosen to work on old Pd versions.

| Control | Function |
|---|---|
| start | delay time, 10 ms – 2 s (exponential); changes glide over 250 ms like tape |
| size | feedback, 0 – 0.98 |
| density | tone: low-pass in the feedback loop, ~80 Hz – 12 kHz (plus a fixed 40 Hz high-pass) |
| overlap | wow depth, 0 – 8 ms |
| window | wow rate, 0.05 – 6 Hz |
| pitch | stereo spread: right delay = left × (1 + 0.5 × pitch); click position 0.6 gives a 1.3× offset |
| blend | dry/wet |
| freeze | holds the loop: input muted, feedback 1, filter bypassed — repeats sustain indefinitely |

Unused: speed, record, file, source, reset, all alt controls.
Desktop test: `pd -nogui -batch -r 48000 -open sim/test_02_echo.pd` renders a blip through it (prints L/R levels).
