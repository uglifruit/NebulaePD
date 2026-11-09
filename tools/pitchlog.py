#!/usr/bin/env python3
"""99_pitchlog: logs every `pitch` message the firmware sends, to measure the poll rate and the Pitch CV slew.

Builder (called from gen.py):  pitchlog_patch(Canvas, controls_canvas, test=None)
Analyzer:                      python tools/pitchlog.py neb_pitchlog.txt [--logical]

On the module: load 99_pitchlog, press Reset (high beep), feed a stepped V/oct (e.g. a 0 V <-> 3 V square at
~1 Hz) for the 20 s capture, wait for the end beeps (two higher beeps). Then load instr/fw_backup.instr, which
copies the log from /dev/shm (or /tmp) to the stick. Each Reset starts a new capture and overwrites the last one.

Log lines: `logical_ms real_ms pitch` (Pd's [timer] = scheduler time, [realtime] = wall clock).
"""
import sys

CAPTURE_MS = 20000
PATHS = ["/dev/shm/neb_pitchlog.txt", "/tmp/neb_pitchlog.txt"]


def pitchlog_patch(Canvas, controls_canvas, test=None):
    """test: dict(path=..., capture_ms=..., poll_ms=..., coeff=...) -> scripted pitch stream (one-pole steps, like
    the firmware), a Reset press at 1.2 s, the log written to `path`, then quit."""
    import gloop
    test = test or {}
    cap = test.get("capture_ms", CAPTURE_MS)
    paths = [test["path"]] if "path" in test else PATHS
    c = Canvas("#N canvas 0 50 1000 640 10;")
    c.text(10, 5, "99_pitchlog: Reset = start a %d s capture of every pitch message (logical ms - real ms - value). "
                  "Written to %s. Collect it with fw_backup.instr." % (cap // 1000, " and ".join(paths)))
    if not test:
        c.sub(10, 30, "nebulae_controls", controls_canvas())
    else:
        dsp = c.obj(10, 30, "loadbang")
        dm = c.msg(10, 52, "\\; pd dsp 1")
        c.connect(dsp, 0, dm, 0)
    # priming: ignore the Reset value that arrives at load
    lb = c.obj(700, 30, "loadbang")
    pd = c.obj(700, 52, "delay 1000")
    pm = c.msg(700, 74, "1")
    ps = c.obj(700, 96, "s pl_primed")
    c.connect(lb, 0, pd, 0)
    c.connect(pd, 0, pm, 0)
    c.connect(pm, 0, ps, 0)

    # start: clear the log, reset both clocks, open the gate, start the capture timer, beep
    rst = gloop.press(c, 10, 70, "reset", rising_only=True, primed="pl_primed")
    st = c.obj(10, 160, "t b b b b b")
    c.connect(rst, 0, st, 0)
    tf = c.obj(10, 420, "textfile")
    clr = c.msg(10, 190, "clear \\, add logical_ms real_ms pitch")
    c.connect(st, 4, clr, 0)
    c.connect(clr, 0, tf, 0)
    tim = c.obj(250, 330, "timer")
    rt = c.obj(330, 330, "realtime")
    c.connect(st, 3, tim, 0)
    c.connect(st, 3, rt, 0)
    on = c.msg(200, 190, "\\; pl_on 1 \\; pl_beep 880")
    c.connect(st, 2, on, 0)
    cd = c.obj(110, 220, f"delay {cap}")
    c.connect(st, 1, cd, 0)

    # end: close the gate, write the file(s), two higher beeps
    en = c.obj(110, 245, "t b b b")
    c.connect(cd, 0, en, 0)
    off = c.msg(110, 270, "\\; pl_on 0")
    c.connect(en, 2, off, 0)
    wr = c.msg(10, 380, " \\, ".join(f"write {p}" for p in paths))
    c.connect(en, 1, wr, 0)
    c.connect(wr, 0, tf, 0)
    b2 = c.msg(200, 270, "\\; pl_beep 1320")
    c.connect(en, 0, b2, 0)
    b2d = c.obj(200, 295, "delay 250")
    b2m = c.msg(200, 317, "\\; pl_beep 1320")
    c.connect(en, 0, b2d, 0)
    c.connect(b2d, 0, b2m, 0)

    # logging: value first (cold), then real time (cold), then logical time (hot) -> one line per message
    rp = c.obj(400, 160, "r pitch")
    sp = c.obj(400, 185, "spigot")
    ron = c.obj(470, 160, "r pl_on")
    c.connect(rp, 0, sp, 0)
    c.connect(ron, 0, sp, 1)
    tr = c.obj(400, 210, "t b b f")
    c.connect(sp, 0, tr, 0)
    pk = c.obj(250, 360, "pack f f f")
    c.connect(tr, 2, pk, 2)
    c.connect(tr, 1, rt, 1)
    c.connect(rt, 0, pk, 1)
    c.connect(tr, 0, tim, 1)
    c.connect(tim, 0, pk, 0)
    am = c.msg(250, 385, "add \\$1 \\$2 \\$3")
    c.connect(pk, 0, am, 0)
    c.connect(am, 0, tf, 0)

    # audio: the raw pitch as a sine during the capture (glide is audible), plus the beeps
    rp2 = c.obj(600, 160, "r pitch")
    m60 = c.obj(600, 185, "* 60")
    p24 = c.obj(600, 207, "+ 24")
    mt = c.obj(600, 229, "mtof")
    osc = c.obj(600, 251, "osc~")
    c.connect(rp2, 0, m60, 0)
    c.connect(m60, 0, p24, 0)
    c.connect(p24, 0, mt, 0)
    c.connect(mt, 0, osc, 0)
    ron2 = c.obj(700, 185, "r pl_on")
    lv = c.obj(700, 207, "* 0.1")
    lp = c.obj(700, 229, "pack f 20")
    ll = c.obj(700, 251, "line~")
    c.connect(ron2, 0, lv, 0)
    c.connect(lv, 0, lp, 0)
    c.connect(lp, 0, ll, 0)
    tone = c.obj(600, 280, "*~")
    c.connect(osc, 0, tone, 0)
    c.connect(ll, 0, tone, 1)
    rb = c.obj(820, 160, "r pl_beep")
    bt = c.obj(820, 185, "t b f")
    bo = c.obj(820, 251, "osc~")
    be = c.msg(880, 207, "0.2 5 \\, 0 20 150")
    bv = c.obj(880, 251, "vline~")
    c.connect(rb, 0, bt, 0)
    c.connect(bt, 1, bo, 0)
    c.connect(bt, 0, be, 0)
    c.connect(be, 0, bv, 0)
    beep = c.obj(820, 280, "*~")
    c.connect(bo, 0, beep, 0)
    c.connect(bv, 0, beep, 1)
    dac = c.obj(600, 320, "dac~ 1 2")
    for src in (tone, beep):
        c.connect(src, 0, dac, 0)
        c.connect(src, 0, dac, 1)

    if test:
        # firmware stand-in: every poll_ms, a one-pole (coeff) towards a 1 Hz square between 0.2 and 0.8
        poll, coeff = test.get("poll_ms", 4), test.get("coeff", 0.33)
        tlb = c.obj(10, 470, "loadbang")
        met = c.obj(10, 492, f"metro {poll}")
        c.connect(tlb, 0, met, 0)
        cnt = c.obj(10, 514, "f")
        inc = c.obj(50, 514, "+ 1")
        c.connect(met, 0, cnt, 0)
        c.connect(cnt, 0, inc, 0)
        c.connect(inc, 0, cnt, 1)
        per = int(1000 / poll)
        md = c.obj(10, 536, f"mod {per}")
        c.connect(cnt, 0, md, 0)
        mo = c.obj(10, 558, f"moses {per // 2}")
        c.connect(md, 0, mo, 0)
        lo = c.msg(10, 580, "0.2")
        hi = c.msg(60, 580, "0.8")
        c.connect(mo, 0, lo, 0)
        c.connect(mo, 1, hi, 0)
        x = c.obj(150, 600, "t b f")
        c.connect(lo, 0, x, 0)
        c.connect(hi, 0, x, 0)
        ax = c.obj(190, 622, f"* {coeff}")
        c.connect(x, 1, ax, 0)
        vy = c.obj(150, 644, "v pl_y")
        c.connect(x, 0, vy, 0)
        ay = c.obj(150, 666, f"* {1 - coeff}")
        c.connect(vy, 0, ay, 0)
        add = c.obj(150, 688, "+")
        c.connect(ax, 0, add, 1)
        c.connect(ay, 0, add, 0)
        out = c.obj(150, 710, "t f f")
        c.connect(add, 0, out, 0)
        vs = c.obj(250, 732, "v pl_y")
        c.connect(out, 1, vs, 0)
        sp_ = c.obj(150, 732, "s pitch")
        c.connect(out, 0, sp_, 0)
        for i, (ms, msg) in enumerate([(1200, "\\; reset 1"), (1250, "\\; reset 0"),
                                       (1200 + cap + 300, "\\; pd quit")]):
            d = c.obj(400 + i * 120, 470, f"delay {ms}")
            m = c.msg(400 + i * 120, 492, msg)
            c.connect(tlb, 0, d, 0)
            c.connect(d, 0, m, 0)
    return c


# ---------------------------------------------------------------------------------------------------------- analyzer
def load(path):
    rows = []
    with open(path) as f:
        for line in f:
            parts = line.replace(";", " ").split()
            try:
                rows.append(tuple(float(p) for p in parts[:3]))
            except ValueError:
                continue                    # header
    return [r for r in rows if len(r) == 3]


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * (len(xs) - 1) + 0.5))]


def transitions(t, v, min_jump=0.05, settle=5, eps=1e-4):
    """Settled level -> settled level moves larger than min_jump (0.05 = 3 semitones). A level is settled once
    `settle` consecutive samples change by < eps."""
    n, out, i = len(v), [], 1
    while i < n:
        if abs(v[i] - v[i - 1]) <= eps:
            i += 1
            continue
        s = i - 1                           # last sample before the move
        j, still = i, 0
        while j < n - 1 and still < settle:
            j += 1
            still = still + 1 if abs(v[j] - v[j - 1]) <= eps else 0
        e = j - still                       # first sample of the new level
        if still >= settle and abs(v[e] - v[s]) >= min_jump:
            out.append((s, e))
        i = j + 1
    return out


def analyze(path, logical=None):
    rows = load(path)
    if len(rows) < 10:
        sys.exit(f"{path}: only {len(rows)} samples")
    lt = [r[0] for r in rows]
    rt = [r[1] for r in rows]
    v = [r[2] for r in rows]
    span_l, span_r = lt[-1] - lt[0], rt[-1] - rt[0]
    if logical is None:
        logical = span_r < 0.5 * span_l     # offline -batch runs: wall clock ~ 0
    t = lt if logical else rt
    span = t[-1] - t[0]
    print(f"{path}: {len(rows)} messages over {span / 1000:.2f} s ({'logical' if logical else 'real'} clock; "
          f"logical span {span_l / 1000:.2f} s, real span {span_r / 1000:.2f} s)")
    d = [b - a for a, b in zip(t, t[1:])]
    print(f"  poll rate: {len(rows) / span * 1000:.1f} messages/s = {span / len(rows):.2f} ms per pass (mean)")
    print(f"  interval ms: median {pct(d, .5):.2f}  p5 {pct(d, .05):.2f}  p95 {pct(d, .95):.2f}  max {max(d):.2f}")
    hist = {}
    for x in d:
        b = round(x * 2) / 2                # 0.5 ms bins
        hist[b] = hist.get(b, 0) + 1
    top = sorted(hist.items(), key=lambda kv: -kv[1])[:6]
    print("  most common intervals (ms: count): " + ", ".join(f"{k:g}: {n}" for k, n in sorted(top)))
    tr = transitions(t, v)
    print(f"  {len(tr)} jumps >= 0.05 (3 semitones):")
    res = []
    for s, e in tr:
        v0, v1 = v[s], v[e]
        def reach(frac):
            for k in range(s, e + 1):
                if abs(v[k] - v0) >= frac * abs(v1 - v0) - 1e-9:
                    return k
            return e
        k90, k99 = reach(0.9), reach(0.99)
        res.append((k90 - s, t[k90] - t[s], k99 - s, t[k99] - t[s], e - s, t[e] - t[s]))
        print(f"    t={t[s] / 1000:7.3f} s  {v0:.4f} -> {v1:.4f} ({(v1 - v0) * 60:+.1f} st): "
              f"90% {k90 - s} polls / {t[k90] - t[s]:.1f} ms, 99% {k99 - s} / {t[k99] - t[s]:.1f} ms, "
              f"settled {e - s} / {t[e] - t[s]:.1f} ms")
    if res:
        print("  median: 90%% %d polls / %.1f ms, 99%% %d polls / %.1f ms, settled %d polls / %.1f ms" % (
            pct([r[0] for r in res], .5), pct([r[1] for r in res], .5), pct([r[2] for r in res], .5),
            pct([r[3] for r in res], .5), pct([r[4] for r in res], .5), pct([r[5] for r in res], .5)))
    return res


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    for p in args:
        analyze(p, logical=True if "--logical" in sys.argv else None)
