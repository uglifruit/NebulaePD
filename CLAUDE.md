# CLAUDE.md

Read [`HANDOFF.md`](HANDOFF.md) before doing anything in this repo. It covers project status, the Nebulae facts that
constrain every patch, the generate → batch-test → commit workflow, tool gotchas, and a new-instrument checklist (§8).
Building the next instruments (the owner's shortlist)? Then read [`docs/NEXT_BUILDS.md`](docs/NEXT_BUILDS.md) next:
the current status, the build queue, and the engine rules.

Key rules:
- `.pd` files are generated: edit `tools/gen.py` or an instrument builder (`tools/gloop.py`, `tools/glitch.py`, `tools/spectral.py`, `tools/topo.py`, `tools/shimmer.py`, `tools/resonator.py`, `tools/chop.py`, `tools/vocoder.py`, `tools/topokits.py`, …),
  then run `python tools/gen.py`.
- Test offline (`pd -nogui -batch -r 48000`) before handing a patch to the owner, who tests on real hardware.
  - Record WAVs with `tabwrite~` + `soundfiler`, **not** `writesf~` (it drops audio in batch mode).
  - Check them with `tools/wavcheck.py` / `tools/wavpeaks.py`.
- Write for old vanilla Pd (the owner's unit runs 0.52.2; see HANDOFF.md §4).
- Custom firmware ([`docs/FIRMWARE.md`](docs/FIRMWARE.md)): edit `firmware/src` only, never `Code/scripts/`,
  `Code/localfiles/` or the boot-path Python files (the USB revert depends on them). Build with `tools/fwbuild.py`;
  run `firmware/tests/` first. Never hand the owner a build made from a provisional base.
- Offer design choices as options with a recommendation. Commit after changes. Push only when asked.
