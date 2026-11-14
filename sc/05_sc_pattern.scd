/*
05_sc_pattern: a generative sequencer with its own four voices (pluck lead, FM bell, bass, noise hat).
Designed with the owner 2026-11-14 (docs/SC_PATTERN.md). MIT.

Each voice spreads its hits evenly over the pattern (Euclidean: Density sets how many), each hit plays with a
chance, and the pitched voices walk a scale. Patterns mutate, lock and come home, as in topo.

  Reset           clock: one pulse = one 16th. SC has 32 ms of output latency, so the patch measures the clock
                  and schedules each step ahead: notes land on the pulses. No clock = it runs on its own tempo.
  Pitch + V/oct   root (click = C3)
  Start           scale: major, minor, dorian, phrygian, lydian, mixolydian, major pentatonic, minor pentatonic
  Size            pattern length, 4 .. 32 steps
  Density         hits per voice
  Overlap         auto-mutation: at the end of every cycle, some notes and rotations change
  Window          tone: bright -> dark
  Blend           space (JPverb)
  Speed           free running: tempo (60 .. 240 BPM, 120 between the clicks); clocked: swing right of the
                  right click
  Freeze          lock: nothing changes (no mutation, the same chances every cycle)
  Record          mutate: a burst of changes (any press)
  File            short = back to home, held 1 s = this pattern becomes home
  Source          voice set B: square lead, glassy bell, sub bass, shaker
  alt (hold Source): Start / Size / Density / Overlap = the levels of pluck / bell / bass / hat,
    Window = octave spread of the upper voices, Blend = decay
*/
~neb = ();
~neb.name = \sc_pattern;

// ---- state ---------------------------------------------------------------------------------------------------------
~ctl = IdentityDictionary[\pitch -> 0.6, \start -> 0, \size -> 0.43, \density -> 0.5, \overlap -> 0.15,
	\window -> 0.4, \blend -> 0.25, \speed -> 0.5, \freeze -> 0, \source -> 0,
	\start_alt -> 0.7, \size_alt -> 0.6, \density_alt -> 0.75, \overlap_alt -> 0.6, \window_alt -> 0.3,
	\blend_alt -> 0.5];
~scales = [[0, 2, 4, 5, 7, 9, 11], [0, 2, 3, 5, 7, 8, 10], [0, 2, 3, 5, 7, 9, 10], [0, 1, 3, 5, 7, 8, 10],
	[0, 2, 4, 6, 7, 9, 11], [0, 2, 4, 5, 7, 9, 10], [0, 2, 4, 7, 9], [0, 3, 5, 7, 10]];
~voiceDefs = [\scp_pluck, \scp_bell, \scp_bass, \scp_hat];
~weights = [0.75, 0.4, 0.5, 1.2];          // hits per voice = round(density * weight * length)
~octaves = [12, 24, -12, 0];                 // above the root
~pans = [-0.3, 0.4, 0, 0.25];
~hitP = 0.85;                                // the chance a Euclidean hit plays
~maxLen = 32;
~k = 0;                                      // steps since the start (pattern step = ~k % length)

~newPattern = {
	~rot = Array.fill(4, { 32.rand });
	~deg = Array.fill(4, {
		var d = 0;
		Array.fill(~maxLen, { d = (d + [-2, -1, -1, 0, 1, 1, 2].choose + (if(0.12.coin, { [-4, 4].choose }, { 0 })))
			.clip(-3, 9); d })
	});
	~rollDice.();
};
~rollDice = { ~dice = Array.fill(4, { Array.fill(~maxLen, { 1.0.rand }) }) };
~storeHome = { ~home = [~rot.copy, ~deg.collect(_.copy)] };
~recallHome = { ~rot = ~home[0].copy; ~deg = ~home[1].collect(_.copy) };
// mutate: each note re-rolled (a step from its neighbour) with probability p, each rotation moved with q
~mutate = { |p, q|
	4.do { |v|
		~maxLen.do { |i|
			if(p.coin, { ~deg[v][i] = (~deg[v].wrapAt(i - 1) + [-2, -1, 1, 2].choose).clip(-3, 9) })
		};
		if(q.coin, { ~rot[v] = (~rot[v] + [-1, 1].choose) % 32 })
	};
};

// ---- the pattern: pure functions of the state and the controls (the NRT test calls these too) ----------------------
~len = { (4 + (~ctl[\size] * 28)).round.asInteger.clip(4, 32) };
~hits = { |v| (~ctl[\density] * ~weights[v] * ~len.()).round.asInteger.clip(0, ~len.()) };
~isHit = { |v, k|
	var n = ~hits.(v), len = ~len.();
	var i = (k + ~rot[v]) % len;
	(n > 0) and: { ((i * n) % len) < n }
};
~root = { 48 + ((~ctl[\pitch] - 0.6) * 60) };
~midi = { |v, k|
	var sc = ~scales[(~ctl[\start] * 8).floor.asInteger.clip(0, 7)];
	var d = ~deg[v][k];
	var spread = if(v < 2, { (~ctl[\window_alt] * 2.99).floor * 12 * (v + 1) / 2 }, { 0 });
	~root.() + ~octaves[v] + spread.round + sc.wrapAt(d) + (12 * d.div(sc.size))
};
// the events of pattern step k: [[def, [args]], ...]
~scpEvents = { |k|
	var out = [];
	var levels = [\start_alt, \size_alt, \density_alt, \overlap_alt].collect { |n| ~ctl[n] };
	var tone = 1 - ~ctl[\window];
	var decay = (~ctl[\blend_alt] - 0.5 * 2.3).exp;            // 0.3 .. 3
	4.do { |v|
		if(~isHit.(v, k) and: { ~dice[v][k] < ~hitP }, {
			var acc = if(k % 4 == 0, { 1 }, { 0.72 });
			var amp = levels[v].squared * acc * 0.5;
			out = out.add([~voiceDefs[v], [\freq, ~midi.(v, k).midicps, \amp, amp, \tone, tone, \decay, decay,
				\set, ~ctl[\source], \pan, ~pans[v]]]);
		});
	};
	out
};
// one step: at the end of a cycle mutate (unless locked) and re-roll the chances, then the step's events
~scpTick = {
	var len = ~len.(), k = ~k % len, ev;
	if((k == 0) and: { ~k > 0 } and: { ~ctl[\freeze] < 0.5 }, {
		~mutate.(~ctl[\overlap] * 0.3, ~ctl[\overlap] * 0.25);
		~rollDice.();
	});
	ev = ~scpEvents.(k);
	~k = ~k + 1;
	ev
};

// ---- the voices ------------------------------------------------------------------------------------------------------
~neb.defs = [
	SynthDef(\scp_pluck, { |out = 0, freq = 440, amp = 0.3, tone = 0.6, decay = 1, set = 0, pan = 0|
		var exc = WhiteNoise.ar(1) * EnvGen.ar(Env.perc(0.0005, 0.01));
		var a = Pluck.ar(exc, 1, 0.05, 1 / freq, decay * 1.5, tone.linlin(0, 1, 0.65, 0.15));
		var b = RLPF.ar(Pulse.ar(freq, 0.3), (freq * tone.linexp(0, 1, 1.5, 12)).clip(40, 16000), 0.5)
			* EnvGen.ar(Env.perc(0.002, decay * 0.6)) * 0.5;
		var sig = Select.ar(set > 0.5, [a, b]) * amp;
		Line.kr(0, 0, decay * 3 + 0.3, doneAction: 2);
		Out.ar(out, Pan2.ar(sig, pan));
	}),
	SynthDef(\scp_bell, { |out = 0, freq = 440, amp = 0.3, tone = 0.6, decay = 1, set = 0, pan = 0|
		var ratio = Select.kr(set > 0.5, [1.4, 3.5]);
		var env = EnvGen.ar(Env.perc(0.002, decay * 2, curve: -6), doneAction: 2);
		var mod = SinOsc.ar(freq * ratio) * freq * ratio * tone.linlin(0, 1, 0.4, 5) * env;
		Out.ar(out, Pan2.ar(SinOsc.ar(freq + mod) * env * amp * 0.7, pan));
	}),
	SynthDef(\scp_bass, { |out = 0, freq = 110, amp = 0.3, tone = 0.6, decay = 1, set = 0, pan = 0|
		var env = EnvGen.ar(Env.perc(0.005, decay * 0.8), doneAction: 2);
		var cut = (freq * tone.linexp(0, 1, 1.5, 10) * (1 + (env * 3))).clip(30, 12000);
		var a = RLPF.ar(Saw.ar(freq), cut, 0.3);
		var b = (SinOsc.ar(freq) + (SinOsc.ar(freq * 0.5) * 0.6)) * 0.6;
		Out.ar(out, Pan2.ar(Select.ar(set > 0.5, [a, b]) * env * amp, pan));
	}),
	SynthDef(\scp_hat, { |out = 0, freq = 440, amp = 0.3, tone = 0.6, decay = 1, set = 0, pan = 0|
		var env = EnvGen.ar(Env.perc(0.001, Select.kr(set > 0.5, [0.05, 0.15]) * decay), doneAction: 2);
		var n = WhiteNoise.ar(1);
		var a = HPF.ar(n, tone.linexp(0, 1, 4000, 9000));
		var b = BPF.ar(n, tone.linexp(0, 1, 2500, 6000), 0.5) * 2;
		Out.ar(out, Pan2.ar(Select.ar(set > 0.5, [a, b]) * env * amp * 0.5, pan));
	}),
	SynthDef(\scp_master, { |in = 16, out = 0, blend = 0.25|
		var dry = In.ar(in, 2);
		var mix = blend.lag(0.1);
		var wet = JPverb.ar(dry, 3, 0.5, 1.5);
		var sig = (dry * (1 - (mix * 0.5))) + (wet * mix);
		Out.ar(out, Limiter.ar(LeakDC.ar(sig), 0.95));
	})
];
~bus = 16;                                   // a private stereo bus (above the 2 outputs and 2 inputs)

~newPattern.();
~storeHome.();

// ---- live: the clock, the controls ----------------------------------------------------------------------------------
if(~nrtTest.isNil, {
	s.waitForBoot({
		~neb.defs.do(_.add);
		s.sync;
		~voices = Group.head(s);
		~nebSynth = Synth.after(~voices, \scp_master, [\in, ~bus, \blend, ~ctl[\blend]]);
		~lout = 0.032;                       // the module's output latency (jackd -p512 -n3, measured)
		~ahead = 0.030;                      // send each step this much before its latest moment (sclang stalls)
		~dt = 0.125;                         // seconds per 16th (external: measured; internal: from Speed)
		~ext = false;
		~lastPulse = nil;
		~nextGrid = SystemClock.seconds + 0.3;
		~lastFiredGrid = -100;
		~internalDt = { 60 / (120 * (2 ** ((~ctl[\speed] - 0.5).clip(-0.5, 0.5) * 4))) / 4 };
		~swing = { if(~ext, { ((~ctl[\speed] - 0.625) / 0.375).clip(0, 1) * 0.33 }, { 0 }) };
		~fire = { |grid|
			var k = ~k;
			var t = grid + (if(k.odd, { ~swing.() * ~dt }, { 0 }));
			var lat0 = t - ~lout - SystemClock.seconds;
			var lat = lat0.max(0);
			var ev = ~scpTick.();
			s.makeBundle(lat, {
				~lastNodes = ev.collect { |e| Synth.head(~voices, e[0], [\out, ~bus] ++ e[1]) };
			});
			~lastServerTime = SystemClock.seconds + lat;
			~lastFiredGrid = grid;
			if((~scpLog == true) and: { lat0 < 0 }, { ("SCPLOG late " ++ (lat0 * -1000).round(0.1)).postln });
			if(~scpLog == true, { ("SCPLOG fire " ++ k ++ " " ++ grid.round(0.0001) ++ " " ++ t.round(0.0001)
				++ " " ++ SystemClock.seconds.round(0.0001)).postln });
		};
		~onPulse = {
			var t = SystemClock.seconds, d;
			if(~lastPulse.isNil or: { (t - ~lastPulse) > max(2, 4 * ~dt) }, {
				~k = 0;                       // first pulse, or after a gap: step 1, now
				~ext = true;
				~pendDt = nil;
				// the last free-running step: not started on the server yet -> free its notes at their own
				// start time (same time stamp, later in order), then play step 1 now; already sounding from
				// 50 ms before the pulse on -> let it stand as step 1 (either way, no flam)
				if(~lastNodes.notNil and: { ~lastServerTime > SystemClock.seconds }, {
					var nodes = ~lastNodes;
					s.makeBundle(~lastServerTime - SystemClock.seconds, { nodes.do(_.free) });
					if(~scpLog == true, { ("SCPLOG cancel " ++ ~lastFiredGrid.round(0.0001)).postln });
					~fire.(t + ~lout);
				}, {
					if(~lastServerTime.notNil and: { (~lastServerTime + ~lout) > (t - 0.05) }, {
						~k = 1;
						~lastFiredGrid = t;
						if(~scpLog == true, { "SCPLOG standin".postln });
					}, {
						~fire.(t + ~lout);
					});
				});
				~nextGrid = t + ~dt;
			}, {
				// a phase-locked loop: the module's pulses jitter by a poll pass (5.3 ms, 4 % of a 16th at
				// 120 BPM), so each pulse nudges the tempo and the phase instead of setting them
				var e = t - ~lastFiredGrid;       // the pulse against the step already sent for it
				d = t - ~lastPulse;
				~ext = true;
				// late pulses (a stalled poll loop) are far likelier than early ones: match up to 60 % late
				if((e > (-0.4 * ~dt)) and: { e < (0.6 * ~dt) }, {
					if((d - ~dt).abs > (0.15 * ~dt), {
						// a tempo change only when two intervals in a row agree (one late pulse - a hiccup in
						// the poll loop - is not one): then follow at once; else just a capped phase nudge
						if(~pendDt.notNil and: { (d - ~pendDt).abs < (0.1 * d) }, {
							~dt = d.clip(0.03, 2);
							~nextGrid = t + ~dt;
							~pendDt = nil;
						}, {
							~pendDt = d;
							~nextGrid = ~lastFiredGrid + ~dt + (0.25 * e.clip(-0.1 * ~dt, 0.1 * ~dt));
						});
					}, {
						~pendDt = nil;
						~dt = (~dt + (0.2 * (d - ~dt))).clip(0.03, 2);
						~nextGrid = ~lastFiredGrid + ~dt + (0.5 * e);
					});
				}, {
					~dt = d.clip(0.03, 2);
					~fire.(t + ~lout);       // a pulse with no step sent for it (a much faster clock): now
					~nextGrid = t + ~dt;
				});
			});
			if(~scpLog == true, { ("SCPLOG pulse " ++ t.round(0.0001)).postln });
			~lastPulse = t;
		};
		~runner = Routine({
			loop {
				var now = SystemClock.seconds;
				if(~ext and: { ~lastPulse.notNil } and: { (now - ~lastPulse) > max(2, 4 * ~dt) }, {
					~ext = false;             // the clock stopped: carry on at the Speed tempo
				});
				if(~ext.not, { ~dt = ~internalDt.() });
				if(now >= (~nextGrid - ~lout - ~ahead), {
					~fire.(~nextGrid);
					~nextGrid = ~nextGrid + ~dt;
				});
				0.003.wait;
			}
		}).play(SystemClock);

		// controls: knobs and latches into ~ctl; alt values only once they move (pickup: the stored ones arrive
		// first when Source is held)
		[\pitch, \start, \size, \density, \overlap, \window, \speed].do { |n|
			OSCdef(("neb_" ++ n).asSymbol, { |msg| ~ctl[n] = msg[1] }, ("/neb/" ++ n).asSymbol, recvPort: 3000);
		};
		OSCdef(\neb_blend, { |msg| ~ctl[\blend] = msg[1]; ~nebSynth.set(\blend, msg[1]) }, '/neb/blend',
			recvPort: 3000);
		~altSeen = IdentityDictionary.new;
		[\start_alt, \size_alt, \density_alt, \overlap_alt, \window_alt, \blend_alt].do { |n|
			OSCdef(("neb_" ++ n).asSymbol, { |msg|
				var v = msg[1], now = SystemClock.seconds, a = ~altSeen[n];
				if(a.isNil or: { (now - a[1]) > 0.15 }, { a = [v, now, false] });      // a new stream
				if(a[2] or: { (v - a[0]).abs > 0.02 }, { a[2] = true; ~ctl[n] = v });
				a[1] = now;
				~altSeen[n] = a;
			}, ("/neb/" ++ n).asSymbol, recvPort: 3000);
		};
		OSCdef(\neb_freeze, { |msg| ~ctl[\freeze] = msg[1] }, '/neb/freeze', recvPort: 3000);
		OSCdef(\neb_source, { |msg| ~ctl[\source] = msg[1] }, '/neb/source', recvPort: 3000);
		~lastRec = nil;
		OSCdef(\neb_record, { |msg|
			if(~lastRec.notNil and: { msg[1] != ~lastRec }, { ~mutate.(0.3, 0.8); ~rollDice.() });
			~lastRec = msg[1];
		}, '/neb/record', recvPort: 3000);
		~fileDown = nil;
		OSCdef(\neb_filestate, { |msg|
			if(msg[1] > 0.5 and: { ~fileDown.isNil }, {
				~fileDown = SystemClock.seconds;
				~fileHeld = false;
				SystemClock.sched(1.0, { if(~fileDown.notNil, { ~storeHome.(); ~fileHeld = true }); nil });
			});
			if(msg[1] < 0.5 and: { ~fileDown.notNil }, {
				if(~fileHeld.not, { ~recallHome.() });
				~fileDown = nil;
			});
		}, '/neb/filestate', recvPort: 3000);
		~lastReset = 0;
		OSCdef(\neb_reset, { |msg|
			if(msg[1] > 0.5 and: { ~lastReset < 0.5 }, { ~onPulse.() });
			~lastReset = msg[1];
		}, '/neb/reset', recvPort: 3000);
		"05_sc_pattern running".postln;
	});
});
