#!/usr/bin/env python3
"""Tests of bt/narrator.py and bt/phrases.py with scripted event streams (no Csound, no hardware).

  python bt/tests/test_narrator.py          (or: python -m unittest discover bt/tests)
"""
import io
import os
import random
import re
import string
import sys
import tokenize
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BT = os.path.dirname(HERE)
sys.path.insert(0, BT)
import narrator as N  # noqa: E402
import phrases as P  # noqa: E402


class Sim(object):
    """Events at the instrument's pace: a 4 Hz analysis frame; controls and onsets when asked."""

    def __init__(self, seed=3, connected=True):
        self.nar = N.Narrator(rng=random.Random(seed))
        self.nar.set_connected(connected)
        self.t = 0.0
        self.out = []
        self.level, self.cent, self.low, self.outlevel = -30.0, 500.0, 0.3, -30.0
        self.ctl = {}
        self.next_frame = 0.0

    def run(self, secs, each=None):
        end = self.t + secs
        while self.t < end:
            if each:
                each(self, self.t)
            if self.t >= self.next_frame:
                self.next_frame += 0.25
                self.nar.feed("a %.3f %.1f %.1f %.0f %.3f" % (self.t, self.level, self.outlevel, self.cent, self.low))
            o = self.nar.tick(self.t)
            if o:
                self.out.append((self.t, o))
            self.t = round(self.t + 0.05, 3)
        return self

    def k(self, name, v):
        if self.ctl.get(name) is None or abs(self.ctl[name] - v) > 0.003:
            self.ctl[name] = v
            self.nar.feed("k %.3f %s %.4f" % (self.t, name, v))

    def onset(self, db=14.0):
        self.nar.feed("o %.3f %.1f" % (self.t, db))

    def text(self):
        return "".join(o for t, o in self.out)


def settle(sim, secs=2.0):
    return sim.run(secs)


class TestPhrases(unittest.TestCase):
    def pools(self):
        for name in dir(P):
            v = getattr(P, name)
            if name.isupper() and isinstance(v, list):
                yield name, v
            elif name.isupper() and isinstance(v, dict):
                for k, lst in v.items():
                    yield "%s[%s]" % (name, k), lst

    FIELDS = dict(name="the swarm", n=3, period="4 seconds", interval="a fifth", dir="up", dur="20 seconds",
                  what="the Reset gate", bpm=120, ago="2 minutes", diff="It is louder now.", mins=15)

    def test_only_safe_characters(self):
        for name, pool in self.pools():
            for line in pool:
                out = N.fill(line, **self.FIELDS)
                bad = [c for c in out if c not in N.SAFE]
                self.assertFalse(bad, "%s: %r has %r" % (name, line, bad))

    def test_every_placeholder_fills(self):
        fields = self.FIELDS
        for name, pool in self.pools():
            for line in pool:
                out = N.fill(line, **fields)
                self.assertNotIn("{", out, "%s: %r" % (name, line))
                for key in re.findall(r"\{(\w+)\}", line):
                    self.assertIn(key.lower(), fields, "%s: unknown field {%s}" % (name, key))

    def test_pool_is_large(self):
        total = sum(len(p) for n, p in self.pools())
        self.assertGreater(total, 300, "a large pool of phrases")

    def test_every_knob_has_up_down_and_names(self):
        for k in N.KNOBS:
            self.assertIn(k, P.UP)
            self.assertIn(k, P.DOWN)
            self.assertIn(k, P.NAMES)


class TestVoice(unittest.TestCase):
    def test_no_immediate_repeat_and_all_used(self):
        v = N.Voice(random.Random(1))
        pool = ["a", "b", "c", "d"]
        got = [v.pick("x", pool) for _ in range(40)]
        for a, b in zip(got, got[1:]):
            self.assertNotEqual(a, b)
        self.assertEqual(set(got[:4]), set(pool))


class TestStory(unittest.TestCase):
    def test_greeting_first(self):
        s = Sim().run(2)
        self.assertTrue(s.out)
        self.assertIn("connected]", s.out[0][1])
        self.assertTrue(any(g in s.out[0][1] for g in P.GREET))

    def test_nothing_typed_when_not_connected(self):
        s = Sim(connected=False)
        s.k("density", 0.3)
        s.run(1)
        s.k("density", 0.8)
        s.run(30)
        self.assertEqual(s.out, [])

    def test_knob_move_data_and_poem(self):
        s = Sim()
        s.k("density", 0.3)
        s.run(5)
        s.k("density", 0.5)
        s.run(0.2)
        s.k("density", 0.8)
        s.run(8)
        text = s.text()
        self.assertIn("density 0.30 > 0.80", text)
        self.assertIn("/ in -30 dB", text)        # the input data snapshot

    def test_indecision(self):
        s = Sim()
        s.k("size", 0.4)
        s.run(5)

        def wiggle(sim, t):
            if t < 9:
                sim.k("size", 0.4 + 0.15 * __import__("math").sin((t - 5) * 4.7))
        s.run(12, wiggle)
        self.assertIn("reversals", s.text())
        self.assertTrue(any(p in s.text() for p in [N.fill(x, name="") .split(".")[0] for x in P.INDECISION]))

    def test_octave_jump(self):
        s = Sim()
        s.k("pitch", 0.6)
        s.run(5)
        s.k("pitch", 0.8)
        s.run(6)
        self.assertIn("pitch +0.0 st > +12.0 st", s.text())
        self.assertTrue(any(x in s.text() for x in P.OCTAVE_UP))

    def test_lfo_is_found_with_its_period(self):
        import math
        s = Sim()
        s.k("overlap", 0.5)
        s.run(3)
        s.run(30, lambda sim, t: sim.k("overlap", 0.5 + 0.3 * math.sin((t - 3) * 2 * math.pi / 4.0)))
        m = re.search(r"overlap moving by itself: wave, period ([\d.]+) s", s.text())
        self.assertTrue(m, s.text())
        self.assertAlmostEqual(float(m.group(1)), 4.0, delta=0.4)

    def test_cv_steps(self):
        s = Sim()
        s.k("start", 0.2)
        s.run(3)
        seq = [0.2, 0.6, 0.35, 0.8, 0.5, 0.1]
        s.run(12, lambda sim, t: sim.k("start", seq[int((t - 3) * 2) % len(seq)]))
        self.assertIn("start moving by itself: steps", s.text())

    def test_regular_reset_pulse_and_tempo(self):
        s = Sim()
        state = {"next": 2.0}

        def gate(sim, t):
            if t >= state["next"]:
                state["next"] += 0.5           # 120 bpm
                sim.nar.feed("k %.3f reset 1" % t)
                sim.nar.feed("k %.3f reset 0" % (t + 0.01))
        s.k("reset", 0)
        s.run(12, gate)
        self.assertRegex(s.text(), r"the Reset gate: regular pulse, 120 bpm")

    def test_irregular_onsets(self):
        s = Sim()
        rng = random.Random(5)
        state = {"next": 2.0}

        def taps(sim, t):
            if t >= state["next"]:
                state["next"] += rng.uniform(0.2, 1.1)
                sim.onset(10.0)
        s.run(30, taps)
        self.assertIn("irregular pulse", s.text())

    def test_single_reset_and_burst(self):
        s = Sim()
        s.k("reset", 0)
        s.run(2)
        s.nar.feed("k %.3f reset 1" % s.t)
        s.nar.feed("k %.3f reset 0" % (s.t + 0.01))
        s.run(6)
        self.assertTrue(any(x in s.text() for x in P.RESET_ONE), s.text())
        for i in range(4):
            s.nar.feed("k %.3f reset 1" % (s.t + i * 0.2))
            s.nar.feed("k %.3f reset 0" % (s.t + i * 0.2 + 0.01))
        s.run(8)
        self.assertIn("reset x4", s.text())

    def test_silence_then_are_you_still_there(self):
        s = Sim()
        s.run(5)
        s.level = -80.0
        s.run(70)
        text = s.text()
        self.assertIn("in silent for 20 seconds", text)
        self.assertIn("in silent for 60 seconds", text)

    def test_transient_after_silence(self):
        s = Sim()
        s.level = -80.0
        s.run(6)
        s.onset(18.0)
        s.run(4)
        self.assertIn("onset +18 dB after silence", s.text())

    def test_brighter_gradually(self):
        s = Sim()
        s.run(3)

        def sweep(sim, t):
            sim.cent = 400.0 * (1.08 ** (t - 3))
        s.run(25, sweep)
        self.assertIn("centroid", s.text())
        self.assertTrue(any(x in s.text() for x in P.BRIGHTER), s.text())

    def test_recognition_with_difference(self):
        s = Sim()
        s.level, s.cent, s.low = -30.0, 300.0, 0.5
        s.run(20)
        s.level, s.cent, s.low = -20.0, 4000.0, 0.1       # something else for a while
        s.run(40)
        s.level, s.cent, s.low = -28.0, 260.0, 0.7        # the first sound back, with more lows
        s.run(20)
        self.assertIn("heard", s.text())
        self.assertTrue(any(x in s.text() for x in P.DIFF["lows_up"]), s.text())

    def test_pacing(self):
        """Never two observations closer than the gap (urgent ones excepted), never while still typing."""
        import math
        s = Sim()
        for name in N.KNOBS:
            s.k(name, 0.5)
        s.run(3)

        def busy(sim, t):
            for i, name in enumerate(N.KNOBS):
                sim.k(name, 0.5 + 0.4 * math.sin(t * (0.7 + i * 0.3)))
            if int(t * 10) % 13 == 0:
                sim.onset(15.0)
        s.run(60, busy)
        times = [t for t, o in s.out]
        for (t0, o0), t1 in zip(s.out, times[1:]):
            self.assertGreaterEqual(t1 - t0, min(1.0, len(o0) / N.CPS) - 1e-6)
            self.assertGreaterEqual(t1 - t0, len(o0) / N.CPS - 0.06)
        self.assertLess(len(s.out), 60 / 3.0)

    def test_output_is_always_safe(self):
        import math
        for seed in range(5):
            s = Sim(seed=seed)
            s.run(2)
            s.run(40, lambda sim, t: (sim.k("pitch", 0.6 + 0.2 * math.sin(t)), setattr(sim, "cent", 300 + 50 * t)))
            for t, o in s.out:
                self.assertFalse([c for c in o if c not in N.SAFE], o)

    def test_no_data_mode(self):
        nar = N.Narrator(rng=random.Random(1), show_data=False)
        nar.set_connected(True)
        out = nar.tick(1.0)
        self.assertNotIn("[", out)


class TestLiveLoop(unittest.TestCase):
    """narrator.py as on the module: tails a growing events file, types when connected, exits when it stops."""

    def test_tail_and_exit(self):
        import subprocess
        import tempfile
        import time
        d = tempfile.mkdtemp()
        ev, st, log = os.path.join(d, "events"), os.path.join(d, "state"), os.path.join(d, "narrator.log")
        with open(st, "w") as f:
            f.write("connected\n")
        open(ev, "w").close()
        p = subprocess.Popen([sys.executable, "-B", os.path.join(BT, "narrator.py"), "--events", ev, "--state", st,
                              "--log", log], stdout=subprocess.PIPE)
        t0 = time.time()
        with open(ev, "a") as f:
            for i in range(24):                              # 6 s of frames, then a knob move, then nothing
                f.write("a %.3f -30.0 -30.0 500 0.300\n" % (i * 0.25))
                if i == 2:
                    f.write("k %.3f density 0.3000\n" % (i * 0.25))
                if i == 8:
                    f.write("k %.3f density 0.9000\n" % (i * 0.25))
                f.flush()
                time.sleep(0.25)
        out, _ = p.communicate(timeout=20)
        took = time.time() - t0
        text = out.decode("ascii")
        self.assertIn("Hello", text)
        self.assertIn("density 0.30 > 0.90", text)
        self.assertLess(took, 6 + 4 + 3, "exits about 4 s after the events stop")
        with open(log) as f:
            self.assertIn("no events for 4 s", f.read())


class TestPython2Syntax(unittest.TestCase):
    """The module runs Python 2.7: no f-strings, nonlocal, keyword-only arguments or print statements' opposite."""

    def check(self, path):
        with io.open(path, encoding="ascii") as f:          # ASCII only
            src = f.read()
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
        for tok in toks:
            if tok.type == tokenize.STRING:
                self.assertFalse(re.match(r"^[rbuRBU]*[fF]", tok.string), "%s: f-string %s" % (path, tok.string))
            if tok.type == tokenize.NAME:
                self.assertNotIn(tok.string, ("nonlocal", "async", "await"), path)
        self.assertNotRegex(src, r"def \w+\([^)]*\*\s*,", "keyword-only arguments")
        self.assertIn("from __future__ import", src) if path.endswith("narrator.py") else None

    def test_narrator_and_phrases(self):
        self.check(os.path.join(BT, "narrator.py"))
        self.check(os.path.join(BT, "phrases.py"))


if __name__ == "__main__":
    unittest.main()
