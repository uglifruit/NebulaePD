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


def controls_canvas(top=False, extra_alt=()):
    """netreceive 3000 -> route -> [s name]; plus DSP-on at load. extra_alt: more alt names to route (06_topo routes
    speed_alt, the Nebulae's input gain, for swing because it has no audio input)."""
    alt = ALT + list(extra_alt)
    c = Canvas("#N canvas 0 50 900 520 10;" if top else "#N canvas 0 50 900 520 %NAME% 0;")
    c.text(10, 5, "Nebulae control receiver (FUDI over TCP 3000). Use [r name] elsewhere.")
    nr = c.obj(10, 30, "netreceive 3000")
    r1 = c.obj(10, 80, "route " + " ".join(PRIMARY))
    r2 = c.obj(10, 230, "route " + " ".join(alt))
    c.connect(nr, 0, r1, 0)
    for i, name in enumerate(PRIMARY):
        s = c.obj(10 + (i % 8) * 105, 130 + (i // 8) * 30, f"s {name}")
        c.connect(r1, i, s, 0)
    c.connect(r1, len(PRIMARY), r2, 0)
    for i, name in enumerate(alt):
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
    """1 s loop (blip 0.2 s in) on head 1 -> head 2 (Source on) at 2x -> pause head 2 (File) -> head 4 (Source+Freeze)
    at 2x -> Reset restarts all heads -> resume head 2 (File, after selecting it again)."""
    return dict(wav=wav, steps=[
        (10, "\\; blend 1"),
        (1100, "\\; record 1"),
        (1300, "\\; gl_blip bang"),
        (2100, "\\; record 0"),
        (4500, "\\; source 1 \\; h2_vol 1"),
        (4600, "\\; speed 0.8125"),
        (6000, "\\; filestate 1"),
        (6050, "\\; filestate 0"),
        (7000, "\\; freeze 1 \\; h4_vol 1"),
        (7100, "\\; speed 0.85"),
        (8500, "\\; reset 1"),
        (8510, "\\; reset 0"),
        (9500, "\\; freeze 0"),
        (9600, "\\; filestate 1"),
        (9650, "\\; filestate 0"),
        (11000, "\\; pd quit"),
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


def gloop_pitch_test(wav=None):
    """Heads 1+2 on a 1 s loop. Head 2 (Source on): Source+Pitch from 0.5 (baseline) to 0.75 = +12 -> 2x.
    Then an alt-reset jump to 0 (ignored). Then Pitch encoder +12 (0.8) -> ALL heads x2: head 1 0.5 s, head 2 0.25 s."""
    return dict(wav=wav, steps=[
        (10, "\\; blend 1"),
        (1100, "\\; record 1"),
        (1300, "\\; gl_blip bang"),
        (2100, "\\; record 0 \\; h2_vol 1"),
        (3000, "\\; source 1"),
        (3500, "\\; pitch_alt 0.5"),
    ] + [(3520 + i * 20, f"\\; pitch_alt {0.5 + 0.025 * (i + 1):g}") for i in range(10)] + [   # turned like an encoder
        (5000, "\\; pitch_alt 0"),
        (6000, "\\; pitch 0.8"),
        (8500, "\\; pd quit"),
    ])


GT_ALL0 = "\\; blend 1 \\; size 0 \\; density 0 \\; window 0 \\; overlap 0 \\; start 0"


def glitch_glitch_test(wav=None):
    """Clock every 500 ms from 1.2 s (ramps: odd beats 1.0, even 0.5). Passthrough -> Record (force): each beat = the
    previous one -> /4 -> reverse every slice -> degrade -> no force, prob 0 = passthrough -> Start gate on/off."""
    return dict(wav=wav, steps=[
        (10, GT_ALL0),
        (1200, "\\; gt_tclkon 1"),
        (3450, "\\; record 1"),
        (5450, "\\; size 0.7"),
        (7450, "\\; density 1"),
        (9450, "\\; window 1 \\; overlap 1"),
        (11450, "\\; record 0 \\; density 0 \\; window 0 \\; overlap 0 \\; size 0"),
        (12450, "\\; start 1"),
        (13450, "\\; start 0"),
        (14500, "\\; pd quit"),
    ])


def glitch_stutter_test(wav=None):
    """Stutter: Source on + Record (force), 8 slices -> scrambled eighths. Then repeat 1 (one slice per beat), then
    drift 1 (slices from earlier beats), then shuffle prob 0 without force = passthrough."""
    return dict(wav=wav, steps=[
        (10, GT_ALL0 + " \\; source 1"),
        (1200, "\\; gt_tclkon 1"),
        (3450, "\\; record 1 \\; size 1"),
        (6450, "\\; overlap 1"),
        (8450, "\\; overlap 0 \\; density 1"),
        (10450, "\\; record 0 \\; density 0"),
        (11500, "\\; pd quit"),
    ])


def glitch_freeze_test(wav=None):
    """Glitch force /1, freeze at 3.45 s then mute the input: the beat before the freeze keeps repeating (one level).
    Unfreeze + unmute at 6.45 s: live alternating beats return within two beats."""
    return dict(wav=wav, steps=[
        (10, GT_ALL0 + " \\; record 1"),
        (1200, "\\; gt_tclkon 1"),
        (3450, "\\; freeze 1"),
        (3550, "\\; gt_tmute 1"),
        (6450, "\\; freeze 0 \\; gt_tmute 0"),
        (9000, "\\; pd quit"),
    ])


def glitch_pitch_test(wav=None):
    """Glitch force /4 (440 Hz input): Pitch +12 -> 880 Hz staccato slices; Speed right click (0.625) = flat 440;
    Speed 0.71875 (+3/repeat) -> 440/523/622/740; Speed left click (-3/repeat) -> falling; Pitch -12 -> 220 Hz. Then no force (all pass-through): Pitch -12 ->
    slice-locked 220 Hz (each slice restarts at the live position); Pitch +12 -> live 440 (untransposed);
    Pitch -12 + Freeze -> live 440."""
    return dict(wav=wav, steps=[
        (10, GT_ALL0 + " \\; record 1 \\; size 0.7 \\; pitch 0.6 \\; speed 0.5"),
        (1200, "\\; gt_tclkon 1"),
        (3450, "\\; pitch 0.8"),
        (5450, "\\; pitch 0.6 \\; speed 0.625"),
        (6450, "\\; speed 0.71875"),
        (7450, "\\; speed 0.375"),
        (9450, "\\; speed 0.5 \\; pitch 0.4"),
        (10450, "\\; record 0"),
        (12450, "\\; pitch 0.8"),
        (13450, "\\; pitch 0.4 \\; freeze 1"),
        (14500, "\\; pd quit"),
    ])


SP0 = ("\\; blend 1 \\; density 1 \\; size 1 \\; window 0 \\; overlap 0 \\; start 0 \\; speed 0.5 \\; pitch 0.6 "
       "\\; sp_flat 1")


def spectral_calib_test(wav=None):
    """Flat gains (sp_flat): 440 Hz sine from 0.5 s = passthrough at unity (latency from the onset). Blend 0.5 at
    2 s must not comb (dry is latency-aligned), blend 0 at 2.5 s = dry."""
    return dict(wav=wav, steps=[
        (10, SP0),
        (500, "\\; sp_tsin 0.5"),
        (2000, "\\; blend 0.5"),
        (2500, "\\; blend 0"),
        (3500, "\\; pd quit"),
    ])


def spectral_bands_test(wav=None):
    """Chord + noise, ~11 bands, probability 0.5, snap smoothing. Clock re-rolls every 500 ms from 1 s; random
    re-rolls every frame at 4 s; sparse + slow smoothing at 6 s; dense at 8 s."""
    return dict(wav=wav, steps=[
        (10, SP0 + " \\; sp_flat 0 \\; density 0.5 \\; size 0.3 \\; sp_tchd 0.5 \\; sp_tnse 0.1"),
        (1000, "\\; sp_tclk 1"),
        (4000, "\\; start 1 \\; sp_tclk 0"),
        (6000, "\\; start 0 \\; window 0.8 \\; density 0.2 \\; sp_tclk 1"),
        (8000, "\\; density 0.9"),
        (10000, "\\; pd quit"),
    ])


def spectral_freeze_test(wav=None):
    """Flat gains, chord. Normal freeze at 1.5 s, input muted at 2 s (level drops: live phase of nothing).
    Unfreeze + chord at 3.5 s. Sealed (Source) at 4 s, freeze at 4.5 s, mute at 5 s (level holds)."""
    return dict(wav=wav, steps=[
        (10, SP0 + " \\; sp_tchd 0.5"),
        (1500, "\\; freeze 1"),
        (2000, "\\; sp_tchd 0"),
        (3500, "\\; freeze 0 \\; sp_tchd 0.5"),
        (4000, "\\; source 1"),
        (4500, "\\; freeze 1"),
        (5000, "\\; sp_tchd 0"),
        (7000, "\\; pd quit"),
    ])


def spectral_pitch_test(wav=None):
    """Flat gains, 440 Hz sine, sealed. Freeze at 1.5 s, mute at 1.8 s. Pitch +12 at 2.5 s (880), -12 at 4 s (220).
    Unfreeze, unseal, sine back and Pitch +7 at 5.5 s: live 659 Hz."""
    return dict(wav=wav, steps=[
        (10, SP0 + " \\; sp_tsin 0.5 \\; source 1"),
        (1500, "\\; freeze 1"),
        (1800, "\\; sp_tsin 0"),
        (2500, "\\; pitch 0.8"),
        (4000, "\\; pitch 0.4"),
        (5500, "\\; freeze 0 \\; source 0 \\; sp_tsin 0.5 \\; pitch 0.716667"),
        (7500, "\\; pd quit"),
    ])


def spectral_gather_test(wav=None):
    """Flat gains, Source OFF (gathered bins keep their own frequency anyway), sine 440 Hz. Gather (Record) at 1 s,
    switch the input to 660 Hz at 2 s: both sound, and the held 440 fades smoothly (it used to collapse into noise).
    Mute at 3 s: the gathered pair decays (-60 dB in ~7.7 s). Freeze at 4 s: it holds."""
    return dict(wav=wav, steps=[
        (10, SP0 + " \\; sp_tsin 0.4"),
        (1000, "\\; record 1"),
        (2000, "\\; sp_tfreq 660"),
        (3000, "\\; sp_tsin 0"),
        (4000, "\\; freeze 1"),
        (6000, "\\; pd quit"),
    ])


def spectral_tape_test(wav=None):
    """Flat gains. Tape mix (alt blend) turned up from 0 to 1 like a pot (pickup), then a 30 ms blip at 1 s: echoes
    every ~224 ms (default time), decaying by ~0.43 (default feedback) and darkening."""
    return dict(wav=wav, steps=[
        (10, SP0),
        (500, "\\; blend_alt 0"),
    ] + [(520 + i * 10, f"\\; blend_alt {0.1 * (i + 1):g}") for i in range(10)] + [
        (1000, "\\; sp_tblip bang"),
        (3000, "\\; pd quit"),
    ])


def spectral_drift_test(wav=None):
    """Noise, 8 bands, probability 0.4, snap. Speed click (+0.25 cycles/s) from 1 s: the open bands rise through the
    spectrum. Speed 0.5 at 5 s: they stop."""
    return dict(wav=wav, steps=[
        (10, SP0 + " \\; sp_flat 0 \\; density 0.4 \\; size 0.2 \\; sp_tnse 0.3"),
        (1000, "\\; speed 0.625"),
        (5000, "\\; speed 0.5"),
        (7000, "\\; pd quit"),
    ])


def spectral_recapture_test(wav=None):
    """Flat gains, 440 Hz sine, freeze at 1 s. Input to 660 Hz at 1.5 s (still 440: frozen). File pressed at 2.5 s:
    the freeze re-captures 660 Hz without unfreezing."""
    return dict(wav=wav, steps=[
        (10, SP0 + " \\; sp_tsin 0.5"),
        (1000, "\\; freeze 1"),
        (1500, "\\; sp_tfreq 660"),
        (2500, "\\; filestate 1"),
        (2550, "\\; filestate 0"),
        (3500, "\\; pd quit"),
    ])


TP0 = ("\\; start 0 \\; size 0.5 \\; density 0.5 \\; overlap 0 \\; window 0 \\; blend 0 \\; speed 0.5 \\; pitch 0.6 "
       "\\; freeze 0 \\; record 0 \\; filestate 0 \\; sourcegate 0")


def topo_voices_test(wav=None):
    """Each voice once (K S C CH OH P, 600 ms apart from 0.5 s), then an open hat choked by a closed hat 150 ms later."""
    hits = [(500 + 600 * i, f"\\; tp_trig_{v} 1") for i, v in enumerate(["K", "S", "C", "CH", "OH", "P"])]
    return dict(wav=wav, steps=[(10, TP0)] + hits + [(4100, "\\; tp_trig_OH 1"), (4250, "\\; tp_trig_CH 1"),
                                                     (5000, "\\; pd quit")])


def topo_sound_test(wav=None):
    """Sound knob: K at blend 0 twice (identical), K at blend 1; S at 1 then 0; CH at 0 then 0.5."""
    return dict(wav=wav, steps=[
        (10, TP0), (500, "\\; tp_trig_K 1"), (1000, "\\; tp_trig_K 1"), (1400, "\\; blend 1"), (1500, "\\; tp_trig_K 1"),
        (2000, "\\; tp_trig_S 1"), (2400, "\\; blend 0"), (2500, "\\; tp_trig_S 1"),
        (3000, "\\; tp_trig_CH 1"), (3400, "\\; blend 0.5"), (3500, "\\; tp_trig_CH 1"),
        (4000, "\\; pd quit"),
    ])


def topo_pattern_test(wav=None):
    """Locked, chaos 0, 16ths every 125 ms from 1.2 s (a 32-step cycle = 4 s): cycles 1-3 identical. Fill 0 for the
    4th cycle = silence, fill 1 for the 5th = busy."""
    return dict(wav=wav, steps=[
        (10, TP0 + " \\; freeze 1"), (1200, "\\; tp_tclk 1"),
        (13150, "\\; density 0.03"), (17150, "\\; density 1"), (21150, "\\; pd quit"),
    ])


def topo_mutate_test(wav=None):
    """Cycles of 4 s from 1.2 s (cycle k starts at 1.2 + 4(k-1) s). An action in cycle k shows in all of cycle k+1.
    Record (6 s) -> cycle 3 = B; File short (14 s) -> cycle 5 = A; Record (22 s) -> cycle 7 = C; File held 1.3 s
    (30 s) stores C, Record (31.5 s) -> cycle 9 = D; File short (38 s) -> cycle 11 = C. Window 1 (46 s) -> cycles
    13, 14 auto-mutated; Freeze (53.5 s) -> cycle 15 = cycle 14."""
    return dict(wav=wav, steps=[
        (10, TP0), (1200, "\\; tp_tclk 1"),
        (6000, "\\; record 1"), (14000, "\\; filestate 1"), (14100, "\\; filestate 0"),
        (22000, "\\; record 0"), (30000, "\\; filestate 1"), (31300, "\\; filestate 0"),
        (31500, "\\; record 1"), (38000, "\\; filestate 1"), (38100, "\\; filestate 0"),
        (46000, "\\; window 1"), (53500, "\\; freeze 1"), (61150, "\\; pd quit"),
    ])


def topo_groove_test(wav=None):
    """Swing 12/8 (alt Speed 23 -> 31 at 1.3 s: odd steps 125/3 = 41.7 ms late); length 8 (window_alt 0.5 -> 0.35 at 5.3 s,
    the second of the 4/8/16/32 zones); Source
    gate reset at 8 s (next step 0); drift at full speed from 10 s. At 14 s fill 0.15 and the hats fill offset
    -0.18 (density_alt swept 0.5 -> 0.32 like a knob): kick and snare stay, no hats."""
    return dict(wav=wav, steps=[
        (10, TP0), (1200, "\\; tp_tclk 1"), (1300, "\\; speed_alt 23"), (1310, "\\; speed_alt 31"),
        (5300, "\\; window_alt 0.5"), (5320, "\\; window_alt 0.35"),
        (8000, "\\; sourcegate 1"), (8005, "\\; sourcegate 0"),
        (10000, "\\; speed 1"), (14000, "\\; density 0.15")] + [
        (14000 + 5 * i, f"\\; density_alt {0.5 - 0.02 * i:g}") for i in range(10)] + [
        (17000, "\\; pd quit"),
    ])


def topo_meter_test(wav=None):
    """Odd meters only by clocked reset: Length stays 32, and a Source gate pulse every 12 steps (1.5 s, between
    clocks) from 1.2 s -> 12-step loops. Then the pulses stop -> back to 32."""
    pulses = []
    for k in range(1, 7):
        t = 1200 + 1500 * k - 60
        pulses += [(t, "\\; sourcegate 1"), (t + 5, "\\; sourcegate 0")]
    return dict(wav=wav, steps=[(10, TP0), (1200, "\\; tp_tclk 1")] + pulses + [(18000, "\\; pd quit")])


def topo_vanilla_test(wav=None):
    """Cycles of 4 s from 1.2 s (cycle k starts at 1.2 + 4(k-1) s); an action in cycle k shows in all of k+1.
    Record (6 s) -> cycle 3 = B; File held (10 s) stores B; Record (14 s) -> cycle 5 = C; File double-tap (22 s) ->
    cycle 7 = A (vanilla); File short (30 s) -> cycle 9 = B (home kept). Window 1 (38 s) -> cycles 11, 12 churn hard
    (8 re-draws per beat) at about the map's density."""
    return dict(wav=wav, steps=[
        (10, TP0), (1200, "\\; tp_tclk 1"), (6000, "\\; record 1"),
        (10000, "\\; filestate 1"), (11300, "\\; filestate 0"), (14000, "\\; record 0"),
        (22000, "\\; filestate 1"), (22050, "\\; filestate 0"), (22200, "\\; filestate 1"), (22250, "\\; filestate 0"),
        (30000, "\\; filestate 1"), (30100, "\\; filestate 0"), (38000, "\\; window 1"), (49150, "\\; pd quit"),
    ])


TOPO_TESTS = [("voices", topo_voices_test), ("sound", topo_sound_test), ("pattern", topo_pattern_test),
              ("mutate", topo_mutate_test), ("groove", topo_groove_test), ("meter", topo_meter_test),
              ("vanilla", topo_vanilla_test)]


SPECTRAL_TESTS = [("calib", spectral_calib_test), ("bands", spectral_bands_test), ("freeze", spectral_freeze_test),
                  ("pitch", spectral_pitch_test), ("gather", spectral_gather_test), ("tape", spectral_tape_test),
                  ("drift", spectral_drift_test), ("recapture", spectral_recapture_test)]


if __name__ == "__main__":
    import gloop
    import glitch
    import spectral
    import topo
    write("lib/nebulae_controls.pd", controls_canvas(top=True))
    write("patches/00_template.pd", template_patch())
    write("patches/01_drone.pd", drone_patch())
    write("patches/02_echo.pd", echo_patch())
    write("patches/03_gloop.pd", gloop.gloop_patch(Canvas, controls_canvas))
    write("patches/04_glitch.pd", glitch.glitch_patch(Canvas, controls_canvas))
    write("patches/05_spectral.pd", spectral.spectral_patch(Canvas, controls_canvas))
    write("patches/06_topo.pd", topo.topo_patch(Canvas, controls_canvas))
    write("sim/sim_controls.pd", sim_patch())
    write("sim/test_02_echo.pd", echo_patch(test=True))
    write("sim/test_02_echo_spread.pd", echo_patch(test=dict(pitch=1, overlap=0.5, window=0.5, freeze_at=99999)))
    write("sim/test_03_gloop.pd", gloop.gloop_patch(Canvas, controls_canvas, level_printer=level_printer,
                                                    test=gloop_basic_test()))
    # --wav DIR: also write WAV-recording variants DIR/t_<name>.pd -> DIR/t_<name>.wav (not committed; use a scratch dir)
    import sys
    wavdir = sys.argv[sys.argv.index("--wav") + 1].replace("\\", "/") if "--wav" in sys.argv else None
    for name, scen in [("glitch", glitch_glitch_test), ("stutter", glitch_stutter_test),
                       ("freeze", glitch_freeze_test), ("pitch", glitch_pitch_test)]:
        write(f"sim/test_04_{name}.pd", glitch.glitch_patch(Canvas, controls_canvas, test=scen()))
        if wavdir:
            write(f"{wavdir}/t_{name}.pd",
                  glitch.glitch_patch(Canvas, controls_canvas, test=scen(wav=f"{wavdir}/t_{name}.wav")))
    for name, scen in SPECTRAL_TESTS:
        write(f"sim/test_05_{name}.pd", spectral.spectral_patch(Canvas, controls_canvas, test=scen()))
        if wavdir:
            write(f"{wavdir}/s_{name}.pd",
                  spectral.spectral_patch(Canvas, controls_canvas, test=scen(wav=f"{wavdir}/s_{name}.wav")))
    for name, scen in TOPO_TESTS:
        write(f"sim/test_06_{name}.pd", topo.topo_patch(Canvas, controls_canvas, test=scen()))
        if wavdir:
            write(f"{wavdir}/d_{name}.pd", topo.topo_patch(Canvas, controls_canvas, test=scen(wav=f"{wavdir}/d_{name}.wav")))
