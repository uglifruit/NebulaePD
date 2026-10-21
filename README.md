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

Patches working - except Spectral, which clicks.
