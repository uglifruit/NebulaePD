/*
06_sc_follow: it listens and plays along. Built 2026-11-14 while the owner was away (decisions to review in
docs/SC_FOLLOW.md). MIT.

The input's pitch (Tartini), key (KeyTrack) and beat (BeatTrack) are tracked; voices play a harmony in that key,
sustained under the input or arpeggiated in time.

  Pitch + V/oct   the harmony interval in scale steps: the click = a third above; one octave of V/oct = 7 steps
  Start           voice: FM bell / soft square / supersaw pad (three zones)
  Size            glide (sustained) / note length (arpeggio)
  Density         arpeggio: off (sustained harmony) -> on the beat -> 8ths -> 16ths of the detected beat
                  (or of the clock on Reset, while one comes)
  Overlap         harmony voices: one -> two (+ a third above it) -> three (+ the input an octave up)
  Window          tone
  Blend           dry <-> harmony (equal power)
  Speed           extra: right of the right click = a sub-octave, left of the left click = an octave up
  Freeze          hold: the last note and key carry on as a drone
  Record          harmony below instead of above (latching)
  Source          chromatic: parallel intervals (no key)
  Reset           clock for the arpeggio (one pulse = one step)
  File            next arpeggio order: up, down, up-down, random
  alt (hold Source): Start = how fast the key follows, Size = stereo width, Density = input gate threshold,
    Overlap = detune, Window = reverb size, Blend = reverb amount

Latency: what you play reaches the harmony after the tracker (about 40 ms) plus SC's 32 ms.
*/
~neb = ();
~neb.name = \sc_follow;
~neb.controls = [\speed, \pitch, \start, \size, \density, \overlap, \window, \blend, \freeze, \source, \record,
	\start_alt, \size_alt, \density_alt, \overlap_alt, \window_alt, \blend_alt];
~neb.def = SynthDef(\sc_follow, { |out = 0, speed = 0.5, pitch = 0.6, start = 0.5, size = 0.2, density = 0,
	overlap = 0, window = 0.5, blend = 0.6, freeze = 0, source = 0, record = 0, t_reset = 0, arpmode = 0,
	start_alt = 0.5, size_alt = 0.5, density_alt = 0.3, overlap_alt = 0.2, window_alt = 0.5, blend_alt = 0.2|
	var in = Mix(SoundIn.ar([0, 1])) * 0.5;
	// --- tracking
	var key = KeyTrack.kr(FFT(LocalBuf(4096), in), start_alt.linexp(0, 1, 0.5, 8), 0.5);
	var bt = BeatTrack.kr(FFT(LocalBuf(1024), in));
	var trk = Tartini.kr(in, 0.93, 2048, 0, 1024);
	var amp = Amplitude.kr(in, 0.01, 0.2);
	var on = (amp > density_alt.linexp(0, 1, 0.002, 0.2)) * (trk[1] > 0.85) * (trk[0] > 40);
	var hold = freeze > 0.5;
	var note = Gate.kr(trk[0].max(40).cpsmidi, on * (1 - hold));
	var heldKey = Gate.kr(key, 1 - hold);
	var level = Gate.kr(Lag.kr(amp * on, 0.05), 1 - hold);
	var tonic = heldKey % 12;
	var minor = heldKey >= 12;
	// --- harmony: the input's scale degree, plus the interval (diatonic), or parallel (chromatic)
	var maj = LocalBuf.newFrom([0, 2, 4, 5, 7, 9, 11]);
	var min = LocalBuf.newFrom([0, 2, 3, 5, 7, 8, 10]);
	var majInv = LocalBuf.newFrom([0, 0, 1, 1, 2, 3, 3, 4, 4, 5, 5, 6]);
	var minInv = LocalBuf.newFrom([0, 0, 1, 2, 2, 3, 3, 4, 5, 5, 6, 6]);
	var rel = note.round - tonic;
	var oct = (rel / 12).floor;
	var pc = rel - (oct * 12);
	var deg = Select.kr(minor, [Index.kr(majInv, pc), Index.kr(minInv, pc)]) + (oct * 7);
	var ivl = (((pitch - 0.6) * 35).round + 2) * (1 - (2 * (record > 0.5)));
	var toMidi = { |d| Select.kr(minor, [DegreeToKey.kr(maj, d, 12), DegreeToKey.kr(min, d, 12)]) + tonic };
	var semis = { |d| DegreeToKey.kr(maj, d, 12) };
	var chrom = source > 0.5;
	var h1 = Select.kr(chrom, [toMidi.(deg + ivl), note + semis.(ivl)]);
	var h2 = Select.kr(chrom, [toMidi.(deg + ivl + 2), note + semis.(ivl + 2)]);
	var h3 = note + 12;
	var glide = size.linexp(0, 1, 0.005, 0.4);
	var g2 = Lag.kr(overlap > 0.33, 0.05), g3 = Lag.kr(overlap > 0.66, 0.05);
	// --- arpeggio over [h1, h2, octave, h1 + octave]
	var arpOn = density > 0.25;
	var div = (density * 4).floor.clip(1, 3);
	var btrig = Select.kr(div - 1, [bt[0], bt[1], bt[2]]);
	var haveR = Sweep.kr(t_reset) < 2;
	var trig = Select.kr(haveR * (Sweep.kr(1) > 2), [btrig, t_reset]) * arpOn;
	var count = PulseCount.kr(trig);
	var iUp = count % 4;
	var iUd = Select.kr(count % 6, [0, 1, 2, 3, 2, 1]);
	var idx = Select.kr(arpmode, [iUp, 3 - iUp, iUd, TIRand.kr(0, 3, trig)]);
	var arpNote = Latch.kr(Select.kr(idx, [h1, h2, h3, h1 + 12]), trig);
	var arpEnv = EnvGen.kr(Env.perc(0.005, size.linexp(0, 1, 0.06, 0.8)), trig);
	// --- voices
	var zone = (start * 3).floor.clip(0, 2);
	var det = overlap_alt * 0.01;
	var voice = { |m|
		var f = m.midicps;
		Select.ar(zone, [
			PMOsc.ar(f, f * 2, window.linlin(0, 1, 0.3, 3)),
			RLPF.ar(Pulse.ar(f * [1 - det, 1 + det], 0.35).sum * 0.5, (f * window.linexp(0, 1, 2, 16)).clip(50, 16000), 0.6),
			LPF.ar(Saw.ar(f * [1 - det, 1, 1 + det]).sum / 3, (f * window.linexp(0, 1, 3, 24)).clip(50, 16000))
		])
	};
	var sus = [
		voice.(Lag.kr(h1, glide)),
		voice.(Lag.kr(h2, glide)) * g2,
		voice.(Lag.kr(h3, glide)) * g3
	];
	var arp = voice.(arpNote) * arpEnv;
	var lvl = Lag.kr(level, 0.02) * 4;
	var harm, sub, up, w, sig, rev, dry, wet;
	sus = sus * lvl * (1 - arpOn);
	arp = arp * Lag.kr(Gate.kr(level, trig), 0.02).max(level) * 4 * arpOn;
	sub = SinOsc.ar((note - 12).midicps) * lvl * ((speed - 0.625) / 0.375).clip(0, 1);
	up = PMOsc.ar((note + 12).midicps, (note + 12).midicps, 0.5) * lvl * 0.5 * ((0.375 - speed) / 0.375).clip(0, 1);
	w = size_alt;
	harm = [
		sus[0] + (sus[1] * (1 - w)) + (sus[2] * 0.5) + arp + sub + up,
		sus[0] + (sus[1] * (1 + w)) * 0.5 + (sus[2] * 0.5) + arp + sub + up
	] * 0.5;
	rev = FreeVerb2.ar(harm[0], harm[1], 1, window_alt, 0.5);
	harm = harm + ([rev[0], rev[1]] * blend_alt.squared);
	dry = cos(blend.lag(0.05) * 0.5pi);
	wet = sin(blend.lag(0.05) * 0.5pi);
	sig = (SoundIn.ar([0, 1]) * dry) + (LeakDC.ar(harm) * wet);
	Out.ar(out, Limiter.ar(sig, 0.95));
});

if(~nrtTest.isNil, {
	s.waitForBoot({
		~neb.def.add;
		s.sync;
		~nebSynth = Synth(~neb.name);
		~neb.controls.do { |name|
			OSCdef(("neb_" ++ name).asSymbol, { |msg| ~nebSynth.set(name, msg[1]) }, ("/neb/" ++ name).asSymbol,
				recvPort: 3000);
		};
		OSCdef(\neb_reset, { |msg| if(msg[1] > 0.5, { ~nebSynth.set(\t_reset, 1) }) }, '/neb/reset',
			recvPort: 3000);
		~arpmode = 0;
		~lastFile = 0;
		OSCdef(\neb_filestate, { |msg|
			if(msg[1] > 0.5 and: { ~lastFile < 0.5 }, { ~arpmode = (~arpmode + 1) % 4; ~nebSynth.set(\arpmode, ~arpmode) });
			~lastFile = msg[1];
		}, '/neb/filestate', recvPort: 3000);
		"06_sc_follow running".postln;
	});
});
