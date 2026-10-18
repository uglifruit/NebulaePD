#!/usr/bin/env python3
"""Generates the .pd files in lib/, patches/ and sim/ (source of truth).

Run from the repo root:  python tools/gen.py
Instruments embed the control receiver as a [pd nebulae_controls] subpatch so each
patch is a single self-contained file (no abstraction paths to worry about on the Nebulae).
"""
import os

PRIMARY = "start size density overlap blend window pitch speed record file source reset freeze filestate sourcegate".split()
ALT = "start_alt size_alt density_alt overlap_alt blend_alt window_alt pitch_alt record_alt file_alt source_alt freeze_alt".split()


class Canvas:
    def __init__(self, header):
        self.header = header
        self.lines = []
        self.n = 0

    def add(self, line):
        self.lines.append(line)
        self.n += 1
        return self.n - 1

    def obj(self, x, y, text):
        return self.add(f"#X obj {x} {y} {text};")

    def msg(self, x, y, text):
        return self.add(f"#X msg {x} {y} {text};")

    def text(self, x, y, text):
        text = text.replace(",", " \\,").replace(";", " -")
        return self.add(f"#X text {x} {y} {text};")

    def raw(self, line):
        return self.add(line)

    def connect(self, a, o, b, i):
        self.lines.append(f"#X connect {a} {o} {b} {i};")

    def sub(self, x, y, name, canvas):
        """Embed another canvas as [pd name] subpatch."""
        self.lines.append(canvas.header.replace("%NAME%", name))
        self.lines.extend(canvas.lines)
        self.lines.append(f"#X restore {x} {y} pd {name};")
        self.n += 1
        return self.n - 1

    def render(self):
        return "\n".join([self.header.replace("%NAME%", "")] + self.lines) + "\n"


def controls_canvas(top=False):
    """netreceive 3000 -> route -> [s name]; plus DSP-on at load."""
    c = Canvas("#N canvas 0 50 900 520 10;" if top else "#N canvas 0 50 900 520 %NAME% 0;")
    c.text(10, 5, "Nebulae control receiver (FUDI over TCP 3000). Use [r name] elsewhere.")
    nr = c.obj(10, 30, "netreceive 3000")
    r1 = c.obj(10, 80, "route " + " ".join(PRIMARY))
    r2 = c.obj(10, 230, "route " + " ".join(ALT))
    c.connect(nr, 0, r1, 0)
    for i, name in enumerate(PRIMARY):
        s = c.obj(10 + (i % 8) * 105, 130 + (i // 8) * 30, f"s {name}")
        c.connect(r1, i, s, 0)
    c.connect(r1, len(PRIMARY), r2, 0)
    for i, name in enumerate(ALT):
        s = c.obj(10 + (i % 6) * 140, 290 + (i // 6) * 30, f"s {name}")
        c.connect(r2, i, s, 0)
    # DSP on shortly after load (unverified whether the Nebulae launcher already does this).
    lb = c.obj(600, 30, "loadbang")
    d = c.obj(600, 55, "delay 300")
    m = c.msg(600, 80, "\\; pd dsp 1")
    c.connect(lb, 0, d, 0)
    c.connect(d, 0, m, 0)
    c.text(10, 380, "pitch: 0-1 modified log curve; x5 octaves for 1V/oct. clicks to 0.6. speed clicks 0.375-0.625.")
    c.text(10, 400, "speed_alt / reset_alt are consumed by the Nebulae (input gain / reset-all-alts); not routed here.")
    return c


def smooth(c, x, y, src, ms=20):
    pk = c.obj(x, y, "pack f %d" % ms)
    ln = c.obj(x, y + 25, "line~")
    c.connect(src, 0, pk, 0)
    c.connect(pk, 0, ln, 0)
    return ln


def drone_patch():
    c = Canvas("#N canvas 0 50 1000 700 10;")
    c.text(10, 5, "01_drone: demo instrument. pitch=osc pitch(27.5-880Hz), overlap=detune, window=lowpass,")
    c.text(10, 20, "density=tremolo rate(0-20Hz), size=tremolo depth, blend=dry(adc)/wet(osc).")
    c.sub(780, 5, "nebulae_controls", controls_canvas())

    # pitch -> freq signal
    rp = c.obj(10, 60, "r pitch")
    m1 = c.obj(10, 85, "* 60")
    m2 = c.obj(10, 110, "+ 21")
    m3 = c.obj(10, 135, "mtof")
    for a, b in [(rp, m1), (m1, m2), (m2, m3)]:
        c.connect(a, 0, b, 0)
    fl = smooth(c, 10, 160, m3, 30)

    # overlap -> detune ratio signal
    ro = c.obj(200, 60, "r overlap")
    d1 = c.obj(200, 85, "* 0.02")
    d2 = c.obj(200, 110, "+ 1")
    c.connect(ro, 0, d1, 0)
    c.connect(d1, 0, d2, 0)
    dl = smooth(c, 200, 160, d2)

    o1 = c.obj(10, 220, "phasor~")
    mul = c.obj(200, 220, "*~")
    o2 = c.obj(200, 250, "phasor~")
    c.connect(fl, 0, o1, 0)
    c.connect(fl, 0, mul, 0)
    c.connect(dl, 0, mul, 1)
    c.connect(mul, 0, o2, 0)
    sm = c.obj(10, 290, "+~")
    c.connect(o1, 0, sm, 0)
    c.connect(o2, 0, sm, 1)
    # remove DC (two phasors 0..1 summed -> 0..2) and scale
    ac = c.obj(10, 315, "-~ 1")
    sc = c.obj(10, 340, "*~ 0.25")
    c.connect(sm, 0, ac, 0)
    c.connect(ac, 0, sc, 0)

    # window -> lowpass
    rw = c.obj(400, 60, "r window")
    w1 = c.obj(400, 85, "* 110")
    w2 = c.obj(400, 110, "+ 20")
    w3 = c.obj(400, 135, "mtof")
    for a, b in [(rw, w1), (w1, w2), (w2, w3)]:
        c.connect(a, 0, b, 0)
    # lop~ cutoff as a float: a signal cutoff inlet needs Pd 0.50+, and the module's Pd version is unknown
    lp = c.obj(10, 370, "lop~")
    c.connect(sc, 0, lp, 0)
    lp2 = c.obj(10, 395, "lop~")
    c.connect(lp, 0, lp2, 0)
    c.connect(w3, 0, lp, 1)
    c.connect(w3, 0, lp2, 1)

    # tremolo: lfo rate from density, depth from size
    rd = c.obj(600, 60, "r density")
    t1 = c.obj(600, 85, "* 20")
    c.connect(rd, 0, t1, 0)
    lfo = c.obj(600, 120, "osc~")
    c.connect(t1, 0, lfo, 0)
    l1 = c.obj(600, 145, "+~ 1")
    l2 = c.obj(600, 170, "*~ 0.5")
    c.connect(lfo, 0, l1, 0)
    c.connect(l1, 0, l2, 0)
    rs = c.obj(800, 60, "r size")
    sl = smooth(c, 800, 90, rs)
    dep = c.obj(600, 200, "*~")
    c.connect(l2, 0, dep, 0)
    c.connect(sl, 0, dep, 1)
    inv = c.obj(600, 225, "*~ -1")
    one = c.obj(600, 250, "+~ 1")
    c.connect(dep, 0, inv, 0)
    c.connect(inv, 0, one, 0)
    am = c.obj(10, 430, "*~")
    c.connect(lp2, 0, am, 0)
    c.connect(one, 0, am, 1)

    # blend dry/wet
    rb = c.obj(400, 300, "r blend")
    bl = smooth(c, 400, 330, rb)
    wet = c.obj(10, 470, "*~")
    c.connect(am, 0, wet, 0)
    c.connect(bl, 0, wet, 1)
    inv2 = c.obj(400, 370, "*~ -1")
    one2 = c.obj(400, 395, "+~ 1")
    c.connect(bl, 0, inv2, 0)
    c.connect(inv2, 0, one2, 0)
    adc = c.obj(200, 440, "adc~ 1 2")
    dryl = c.obj(200, 470, "*~")
    dryr = c.obj(300, 470, "*~")
    c.connect(adc, 0, dryl, 0)
    c.connect(one2, 0, dryl, 1)
    c.connect(adc, 1, dryr, 0)
    c.connect(one2, 0, dryr, 1)
    sl_ = c.obj(10, 520, "+~")
    sr_ = c.obj(300, 520, "+~")
    c.connect(wet, 0, sl_, 0)
    c.connect(dryl, 0, sl_, 1)
    c.connect(wet, 0, sr_, 0)
    c.connect(dryr, 0, sr_, 1)
    dac = c.obj(10, 570, "dac~ 1 2")
    c.connect(sl_, 0, dac, 0)
    c.connect(sr_, 0, dac, 1)
    return c


def test_source():
    """Stand-in for [adc~ 1 2] in test builds: a 50 ms 440 Hz blip at t=0.5 s on both outlets."""
    s = Canvas("#N canvas 0 50 400 300 %NAME% 0;")
    lb = s.obj(10, 10, "loadbang")
    d = s.obj(10, 35, "delay 500")
    m = s.msg(10, 60, "1 \\, 0 5 50")
    ln = s.obj(10, 85, "line~")
    osc = s.obj(100, 85, "osc~ 440")
    mul = s.obj(10, 115, "*~")
    o1 = s.obj(10, 145, "outlet~")
    o2 = s.obj(80, 145, "outlet~")
    s.connect(lb, 0, d, 0)
    s.connect(d, 0, m, 0)
    s.connect(m, 0, ln, 0)
    s.connect(ln, 0, mul, 0)
    s.connect(osc, 0, mul, 1)
    s.connect(mul, 0, o1, 0)
    s.connect(mul, 0, o2, 0)
    return s


def level_printer(c, x, y, sig, label):
    """Test builds: print the RMS dB of a signal every 100 ms."""
    e = c.obj(x, y, "env~ 4096 4800")
    p = c.obj(x, y + 25, f"print {label}")
    c.connect(sig, 0, e, 0)
    c.connect(e, 0, p, 0)


def echo_patch(test=False):
    """02_echo: stereo tape-style echo with freeze. Vanilla objects only, all old enough for any Pd 0.4x."""
    c = Canvas("#N canvas 0 50 1100 760 10;")
    c.text(10, 5, "02_echo: stereo tape echo with freeze. start=time 10ms-2s, size=feedback, density=tone (loop lowpass),")
    c.text(10, 20, "overlap=wow depth, window=wow rate, pitch=stereo spread (R longer), blend=dry/wet, freeze=hold loop.")
    c.sub(950, 5, "nebulae_controls", controls_canvas())

    # --- control -> smoothed signals ---
    # time: 10 * exp(start * ln 200) ms, slow glide for tape-like repitch
    rs = c.obj(10, 50, "r start")
    t1 = c.obj(10, 75, "* 5.298")
    t2 = c.obj(10, 100, "exp")
    t3 = c.obj(10, 125, "* 10")
    for a, b in [(rs, t1), (t1, t2), (t2, t3)]:
        c.connect(a, 0, b, 0)
    tsig = smooth(c, 10, 150, t3, 250)

    # spread: right time = left time * (1 + 0.5 * pitch)
    rp = c.obj(160, 50, "r pitch")
    p1 = c.obj(160, 75, "* 0.5")
    p2 = c.obj(160, 100, "+ 1")
    c.connect(rp, 0, p1, 0)
    c.connect(p1, 0, p2, 0)
    psig = smooth(c, 160, 150, p2, 250)
    tr = c.obj(160, 205, "*~")
    c.connect(tsig, 0, tr, 0)
    c.connect(psig, 0, tr, 1)

    # wow: osc~ at window*6 Hz (+0.05), depth overlap*8 ms
    rw = c.obj(310, 50, "r window")
    w1 = c.obj(310, 75, "* 6")
    w2 = c.obj(310, 100, "+ 0.05")
    c.connect(rw, 0, w1, 0)
    c.connect(w1, 0, w2, 0)
    lfo = c.obj(310, 125, "osc~")
    c.connect(w2, 0, lfo, 0)
    ro = c.obj(420, 50, "r overlap")
    o1 = c.obj(420, 75, "* 8")
    c.connect(ro, 0, o1, 0)
    osig = smooth(c, 420, 100, o1, 50)
    wow = c.obj(310, 160, "*~")
    c.connect(lfo, 0, wow, 0)
    c.connect(osig, 0, wow, 1)
    tl_ = c.obj(10, 240, "+~")
    c.connect(tsig, 0, tl_, 0)
    c.connect(wow, 0, tl_, 1)
    tr_ = c.obj(160, 240, "+~")
    c.connect(tr, 0, tr_, 0)
    c.connect(wow, 0, tr_, 1)

    # feedback gain: fb + frz*(1 - fb)   (frozen -> 1)
    rf = c.obj(560, 50, "r size")
    f1 = c.obj(560, 75, "* 0.98")
    c.connect(rf, 0, f1, 0)
    fb = smooth(c, 560, 100, f1, 30)
    rz = c.obj(700, 50, "r freeze")
    frz = smooth(c, 700, 100, rz, 30)
    fz1 = c.obj(560, 160, "*~")
    c.connect(fb, 0, fz1, 0)
    c.connect(frz, 0, fz1, 1)
    fz2 = c.obj(640, 160, "+~")
    c.connect(fb, 0, fz2, 0)
    c.connect(frz, 0, fz2, 1)
    fbg = c.obj(560, 190, "-~")
    c.connect(fz2, 0, fbg, 0)
    c.connect(fz1, 0, fbg, 1)
    # input gain and "not frozen" gain: 1 - frz
    nf1 = c.obj(700, 160, "*~ -1")
    nf = c.obj(700, 190, "+~ 1")
    c.connect(frz, 0, nf1, 0)
    c.connect(nf1, 0, nf, 0)

    # tone: density -> loop lowpass cutoff (float inlet for old-Pd compatibility)
    rd = c.obj(840, 50, "r density")
    d1 = c.obj(840, 75, "* 95")
    d2 = c.obj(840, 100, "+ 40")
    d3 = c.obj(840, 125, "mtof")
    for a, b in [(rd, d1), (d1, d2), (d2, d3)]:
        c.connect(a, 0, b, 0)

    # blend: wet = blend, dry = 1 - blend
    rb = c.obj(840, 170, "r blend")
    wet = smooth(c, 840, 195, rb, 30)
    dr1 = c.obj(840, 250, "*~ -1")
    dry = c.obj(840, 275, "+~ 1")
    c.connect(wet, 0, dr1, 0)
    c.connect(dr1, 0, dry, 0)

    adc = c.sub(10, 290, "testsrc", test_source()) if test else c.obj(10, 290, "adc~ 1 2")
    dac_ins = []
    # --- per-channel echo ---
    for ch, (x, tsigc) in enumerate([(10, tl_), (420, tr_)]):
        name = "echo_" + ("l" if ch == 0 else "r")
        ing = c.obj(x, 330, "*~")                 # input * (1 - frz)
        c.connect(adc, ch, ing, 0)
        c.connect(nf, 0, ing, 1)
        sm = c.obj(x, 360, "+~")                  # input + feedback
        c.connect(ing, 0, sm, 0)
        cl = c.obj(x, 390, "clip~ -1 1")
        c.connect(sm, 0, cl, 0)
        dw = c.obj(x, 420, f"delwrite~ {name} 2500")
        c.connect(cl, 0, dw, 0)
        vd = c.obj(x + 150, 330, f"vd~ {name}")
        c.connect(tsigc, 0, vd, 0)
        # loop: filtered (when running) or raw (when frozen)
        lp = c.obj(x + 150, 360, "lop~ 8000")
        c.connect(vd, 0, lp, 0)
        c.connect(d3, 0, lp, 1)
        hp = c.obj(x + 150, 390, "hip~ 40")
        c.connect(lp, 0, hp, 0)
        g1 = c.obj(x + 150, 420, "*~")             # filtered * (1 - frz)
        c.connect(hp, 0, g1, 0)
        c.connect(nf, 0, g1, 1)
        g2 = c.obj(x + 250, 420, "*~")             # raw * frz
        c.connect(vd, 0, g2, 0)
        c.connect(frz, 0, g2, 1)
        lpsum = c.obj(x + 150, 450, "+~")
        c.connect(g1, 0, lpsum, 0)
        c.connect(g2, 0, lpsum, 1)
        fbm = c.obj(x + 150, 480, "*~")            # * feedback gain
        c.connect(lpsum, 0, fbm, 0)
        c.connect(fbg, 0, fbm, 1)
        c.connect(fbm, 0, sm, 1)
        # output mix
        wm = c.obj(x + 150, 530, "*~")
        c.connect(vd, 0, wm, 0)
        c.connect(wet, 0, wm, 1)
        dm = c.obj(x, 530, "*~")
        c.connect(adc, ch, dm, 0)
        c.connect(dry, 0, dm, 1)
        o = c.obj(x, 560, "+~")
        c.connect(dm, 0, o, 0)
        c.connect(wm, 0, o, 1)
        oc = c.obj(x, 590, "clip~ -1 1")
        c.connect(o, 0, oc, 0)
        dac_ins.append(oc)
    dac = c.obj(10, 640, "dac~ 1 2")
    c.connect(dac_ins[0], 0, dac, 0)
    c.connect(dac_ins[1], 0, dac, 1)
    if test:
        level_printer(c, 10, 680, dac_ins[0], "L")
        level_printer(c, 420, 680, dac_ins[1], "R")
        # scripted knob moves (start 0.642 = 300 ms echo); `test` overrides; freeze at 1.2 s; quit at 6 s
        knobs = dict(start=0.642, size=0.6, density=0.8, overlap=0, window=0, pitch=0, blend=0.5, freeze=0)
        knobs.update(test if isinstance(test, dict) else {})
        frz_at = knobs.pop("freeze_at", 1200)
        wav = knobs.pop("wav", None)
        lb = c.obj(600, 600, "loadbang")
        if wav:  # also record the output for offline inspection
            wsf = c.obj(10, 730, "writesf~ 2")
            c.connect(dac_ins[0], 0, wsf, 0)
            c.connect(dac_ins[1], 0, wsf, 1)
            wd = c.obj(300, 705, "delay 350")
            wm = c.msg(300, 730, f"open -bytes 4 {wav} \\, start")
            c.connect(lb, 0, wd, 0)
            c.connect(wd, 0, wm, 0)
            c.connect(wm, 0, wsf, 0)
        m0 = c.msg(600, 625, " ".join(f"\\; {k} {v}" for k, v in knobs.items()))
        d1 = c.obj(800, 625, f"delay {frz_at}")
        m1 = c.msg(800, 650, "\\; freeze 1")
        d2 = c.obj(950, 625, "delay 6000")
        m2 = c.msg(950, 650, "\\; pd quit")
        for a, b in [(lb, m0), (lb, d1), (d1, m1), (lb, d2), (d2, m2)]:
            c.connect(a, 0, b, 0)
    return c


def template_patch():
    c = Canvas("#N canvas 0 50 700 400 10;")
    c.text(10, 5, "00_template: controls + audio passthrough. Copy and build on this.")
    c.sub(10, 30, "nebulae_controls", controls_canvas())
    a = c.obj(10, 80, "adc~ 1 2")
    d = c.obj(10, 120, "dac~ 1 2")
    c.connect(a, 0, d, 0)
    c.connect(a, 1, d, 1)
    c.text(10, 160, "Use [r density] [r pitch] etc. anywhere in this patch.")
    return c


def sim_patch():
    c = Canvas("#N canvas 0 50 760 420 10;")
    c.text(10, 5, "Desktop control simulator. Sends the same names as the Nebulae via [s name] (no TCP needed).")
    c.text(10, 20, "Open in the same Pd session as an instrument, or use sim/send_fudi.py over TCP 3000.")
    names = "start size density overlap blend window pitch speed".split()
    for i, n in enumerate(names):
        x = 10 + i * 85
        v = c.raw(f"#X obj {x} 50 vsl 25 150 0 1 0 0 empty empty {n} 0 -9 0 10 -262144 -1 -1 0 1;")
        s = c.obj(x, 220, f"s {n}")
        c.connect(v, 0, s, 0)
    for i, n in enumerate("record file source freeze".split()):
        x = 10 + i * 85
        t = c.raw(f"#X obj {x} 260 tgl 20 0 empty empty {n} 25 10 0 10 -262144 -1 -1 0 1;")
        s = c.obj(x, 290, f"s {n}")
        c.connect(t, 0, s, 0)
    b = c.msg(360, 260, "1")
    ps = c.obj(360, 290, "s reset")
    c.connect(b, 0, ps, 0)
    c.text(400, 262, "<- reset (momentary)")
    return c


def write(path, canvas):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="\n") as f:
        f.write(canvas.render())
    print("wrote", path)


def gloop_basic_test(wav=None):
    """Record a 1 s loop with a blip 0.2 s in; head 1 plays it; then select head 2 (Source tap) at 2x speed."""
    return dict(wav=wav, steps=[
        (10, "\\; blend 1"),
        (1100, "\\; record 1"),
        (1300, "\\; gl_blip bang"),
        (2100, "\\; record 0"),
        (4500, "\\; source 1 \\; h2_vol 1"),
        (4600, "\\; speed 0.8125"),
        (7000, "\\; pd quit"),
    ])


def gloop_full_test(wav=None):
    """1 s loop (blip at 0.2) -> overdub a blip at 0.7 -> head 1 size 0.5 -> reverse -> degrade -> clear."""
    return dict(wav=wav, steps=[
        (10, "\\; blend 1"),
        (1100, "\\; record 1"),
        (1300, "\\; gl_blip bang"),
        (2100, "\\; record 0"),
        (3550, "\\; record 1"),
        (3800, "\\; gl_blip bang"),
        (4600, "\\; record 0"),
        (6000, "\\; size 0.5"),
        (8000, "\\; speed 0.375"),
        (9500, "\\; blend_alt 0.6"),
        (12000, "\\; record_alt 1"),
        (13000, "\\; pd quit"),
    ])


def gloop_grid_test(wav=None):
    """1 s loop -> grid 4 + size 0.3 (snaps to 0.25) -> pan hard right -> jitter + wobble."""
    return dict(wav=wav, steps=[
        (10, "\\; blend 1"),
        (1100, "\\; record 1"),
        (1300, "\\; gl_blip bang"),
        (2100, "\\; record 0"),
        (3000, "\\; file_alt 1"),
        (3100, "\\; size 0.3"),
        (5000, "\\; overlap 1"),
        (6500, "\\; density 0.5 \\; window_alt 1"),
        (9000, "\\; pd quit"),
    ])


if __name__ == "__main__":
    import gloop
    write("lib/nebulae_controls.pd", controls_canvas(top=True))
    write("patches/00_template.pd", template_patch())
    write("patches/01_drone.pd", drone_patch())
    write("patches/02_echo.pd", echo_patch())
    write("patches/03_gloop.pd", gloop.gloop_patch(Canvas, controls_canvas))
    write("sim/sim_controls.pd", sim_patch())
    write("sim/test_02_echo.pd", echo_patch(test=True))
    write("sim/test_02_echo_spread.pd", echo_patch(test=dict(pitch=1, overlap=0.5, window=0.5, freeze_at=99999)))
    write("sim/test_03_gloop.pd", gloop.gloop_patch(Canvas, controls_canvas, level_printer=level_printer,
                                                    test=gloop_basic_test()))
