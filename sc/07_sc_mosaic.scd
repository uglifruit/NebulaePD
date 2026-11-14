/*
07_sc_mosaic: concatenative resynthesis. Built 2026-11-14 while the owner was away (decisions to review in
docs/SC_MOSAIC.md). MIT.

What you play into the inputs is rebuilt, piece by piece, out of another sound: every few milliseconds Concat
(sc3-plugins) finds the piece of the corpus that best matches the input right now (loudness, noisiness,
brightness) and plays it. Play a drum loop and it answers with matching bits of a choir; talk and a piano talks.

  Corpus          a stick file playing into a 10 s store (File = next file), or the input's own past (Source)
  Size            grain: 10 .. 250 ms pieces
  Density         match: anticlockwise = loose (random pieces), clockwise = strict (best match)
  Start           how far back in the store it looks (0.2 .. 10 s)
  Window          how wide the search is (a narrow slice -> all of it)
  Overlap         what counts as a match: loudness and noisiness (anticlockwise) <-> brightness and tilt (clockwise)
  Speed           the corpus's playback speed: centre = stopped (the store keeps what it has), the clicks = 1x
                  (left = backwards), the ends = 4x
  Pitch + V/oct   transpose the output (click = none)
  Blend           dry <-> mosaic
  Freeze          freeze the store: the corpus stops changing
  Record          also hear the corpus itself (alt Start = its level)
  Source          corpus = the input's own past instead of the file
  Reset           the file back to its start
  File            next stick file (wav, aif, flac)
  alt (hold Source): Start = corpus level (Record), Size = stereo width, Window = reverb size, Blend = reverb amount
*/
~neb = ();
~neb.name = \sc_mosaic;
~neb.controls = [\speed, \pitch, \start, \size, \density, \overlap, \window, \blend, \freeze, \source, \record,
	\start_alt, \size_alt, \window_alt, \blend_alt];
~neb.def = SynthDef(\sc_mosaic, { |out = 0, buf = 0, speed = 0.625, pitch = 0.6, start = 0.3, size = 0.35,
	density = 0.7, overlap = 0.4, window = 0.6, blend = 0.85, freeze = 0, source = 0, record = 0, t_reset = 0,
	start_alt = 0.5, size_alt = 0.3, window_alt = 0.5, blend_alt = 0.15|
	var in = Mix(SoundIn.ar([0, 1])) * 0.5;
	// Speed -> the corpus's rate: centre stopped, the clicks 1x (left = backwards), the ends 4x
	var kd = (speed - 0.5) / 0.125;
	var ad = kd.abs;
	var rate = Select.kr(ad > 1, [ad * (ad > 0.04), (1 + ((ad - 1) * 1)).min(4)]) * kd.sign;
	var file = PlayBuf.ar(1, buf, BufRateScale.kr(buf) * rate.lag(0.05), t_reset, 0, 1);
	var src = Select.ar(source > 0.5, [file, in]);
	var seek = start.linexp(0, 1, 0.2, 10);
	var conc = Concat.ar(in, src, 10, seek, seek * window.linlin(0, 1, 0.05, 1), size.linexp(0, 1, 0.01, 0.25),
		freeze > 0.5, 1 - overlap, 1, overlap * 2, overlap, (1 - density).squared);
	// the input's dynamics: Concat plays each piece at the corpus's own level, so the output takes the input's
	// envelope (gain = input level / piece level, 20 ms, at most x4)
	var lvl = (Amplitude.kr(in, 0.005, 0.05) / (Amplitude.kr(conc, 0.005, 0.05) + 0.002)).clip(0, 4).lag(0.02);
	var ratio = (2 ** (((pitch - 0.6) * 60).clip(-36, 36) / 12)).lag(0.01);
	var piece = conc * lvl;
	var shifted = Select.ar(ratio > 0.999 * (ratio < 1.001), [PitchShift.ar(piece, 0.08, ratio, 0, 0.004), piece]);
	var mon = file * (record > 0.5) * start_alt.lag(0.05);
	var mono = shifted + mon;
	var wet = [mono, DelayC.ar(mono, 0.02, size_alt.lag(0.1) * 0.015)];
	var rev = FreeVerb2.ar(wet[0], wet[1], 1, window_alt, 0.5);
	var b = blend.lag(0.05);
	var sig;
	wet = LeakDC.ar(wet + (rev * blend_alt.squared));
	sig = (SoundIn.ar([0, 1]) * cos(b * 0.5pi)) + (wet * sin(b * 0.5pi));
	Out.ar(out, Limiter.ar(sig, 0.95));
});

if(~nrtTest.isNil, {
	s.waitForBoot({
		var dir = ~mosaicDir ? "/home/alarm/audio";
		~neb.def.add;
		~files = (dir +/+ "*").pathMatch.select { |p|
			[".wav", ".aif", ".aiff", ".flac"].any { |e| p.toLower.endsWith(e) }
		}.sort;
		~fileIdx = 0;
		~buf = if(~files.size > 0, { Buffer.readChannel(s, ~files[0], channels: [0]) },
			{ Buffer.alloc(s, s.sampleRate, 1) });
		s.sync;
		~nebSynth = Synth(~neb.name, [\buf, ~buf]);
		~neb.controls.do { |name|
			OSCdef(("neb_" ++ name).asSymbol, { |msg| ~nebSynth.set(name, msg[1]) }, ("/neb/" ++ name).asSymbol,
				recvPort: 3000);
		};
		OSCdef(\neb_reset, { |msg| if(msg[1] > 0.5, { ~nebSynth.set(\t_reset, 1) }) }, '/neb/reset',
			recvPort: 3000);
		~lastFile = 0;
		OSCdef(\neb_filestate, { |msg|
			if(msg[1] > 0.5 and: { ~lastFile < 0.5 } and: { ~files.size > 1 }, {
				~fileIdx = (~fileIdx + 1) % ~files.size;
				Buffer.readChannel(s, ~files[~fileIdx], channels: [0], action: { |nb|
					var old = ~buf;
					~buf = nb;
					~nebSynth.set(\buf, nb, \t_reset, 1);
					SystemClock.sched(0.5, { old.free; nil });
					("sc_mosaic corpus " ++ ~files[~fileIdx].basename).postln;
				});
			});
			~lastFile = msg[1];
		}, '/neb/filestate', recvPort: 3000);
		("07_sc_mosaic running (" ++ ~files.size ++ " files)").postln;
	});
});
