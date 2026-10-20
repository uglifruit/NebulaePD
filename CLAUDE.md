# CLAUDE.md

Read [`HANDOFF.md`](HANDOFF.md) before doing anything in this repo. It covers project status, the Nebulae facts that
constrain every patch, the generate → batch-test → commit workflow, tool gotchas, and a new-instrument checklist (§8).

Key rules:
- `.pd` files are generated: edit `tools/gen.py` or an instrument builder (`tools/gloop.py`, `tools/glitch.py`, `tools/spectral.py`, `tools/topo.py`, `tools/shimmer.py`, …),
  then run `python tools/gen.py`.
- Test offline (`pd -nogui -batch -r 48000`) before handing a patch to the owner, who tests on real hardware.
  - Record WAVs with `tabwrite~` + `soundfiler`, **not** `writesf~` (it drops audio in batch mode).
  - Check them with `tools/wavcheck.py` / `tools/wavpeaks.py`.
- Write for unknown-version vanilla Pd (see HANDOFF.md §4).
- Offer design choices as options with a recommendation. Commit after changes. Push only when asked.
