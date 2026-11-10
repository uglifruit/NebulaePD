/*
01_sctest: the uf2 hardware test patch, and a minimal example of a Nebulae SuperCollider patch.
Technobear-compatible: the firmware sends every control as OSC /neb/<name> <value> to port 3000 (on change, and all
again once a second; reset only on change).

  Pitch   + V/oct  pitch, 1 V/oct (click = 0.6 = C4)
  Size             filter cutoff (200 Hz .. 8 kHz)
  Density          pluck decay (0.05 .. 2 s)
  Reset            pluck (button or gate)
  Freeze           drone on/off (holds the note)
  Blend            output level

Logs "SCTEST got /neb/<name>" the first time each control arrives (to sclang.log in /tmp/neb_sc on the module).
Top level uses ~variables, not var, so the file also runs after another script in one chunk (PC tests).
*/
~seen = Set.new;
~ctl = { |name, func|
	OSCdef(("sctest_" ++ name).asSymbol, { |msg|
		if(~seen.includes(name).not, { ~seen.add(name); ("SCTEST got /neb/" ++ name ++ " " ++ msg[1]).postln });
		func.value(msg[1]);
	}, ("/neb/" ++ name).asSymbol, recvPort: 3000);
};

s.waitForBoot({
	SynthDef(\sctest, { |out = 0, midi = 60, cutoff = 1500, decay = 0.4, drone = 0, amp = 0.3, t_pluck = 0|
		var env = EnvGen.ar(Env.perc(0.003, decay), t_pluck);
		var gate = Lag.kr(drone, 0.05);
		var sig = Saw.ar(midi.lag(0.003).midicps * [1, 1.003]) * 0.5;
		sig = RLPF.ar(sig, cutoff.lag(0.02), 0.3);
		Out.ar(out, sig * max(env, gate * 0.6) * amp.lag(0.05));
	}).add;
	s.sync;
	~synth = Synth(\sctest);
	~ctl.(\pitch, { |v| ~synth.set(\midi, 60 + (v * 60) - 36) });
	~ctl.(\size, { |v| ~synth.set(\cutoff, v.linexp(0, 1, 200, 8000)) });
	~ctl.(\density, { |v| ~synth.set(\decay, v.linexp(0, 1, 0.05, 2)) });
	~ctl.(\reset, { |v| if(v > 0.5, { ~synth.set(\t_pluck, 1) }) });
	~ctl.(\freeze, { |v| ~synth.set(\drone, v) });
	~ctl.(\blend, { |v| ~synth.set(\amp, v * 0.6) });
	"SCTEST 01_sctest running".postln;
});
