// SuperCollider probe, stage 2: realtime through jackd. A C-E-G-C arpeggio, 4 notes a second, for about 6 s on
// both outputs. See sc/probe/run.sh.
(
s = Server.default;
s.options.numInputBusChannels = 2;
s.options.numOutputBusChannels = 2;
s.options.sampleRate = 48000;
s.options.blockSize = 64;
s.options.memSize = 16 * 8192;
s.options.ugenPluginsPath = "/tmp/sc/plugins";
SystemClock.sched(50, { "SCPROBE: RT timeout".postln; 1.exit; nil });
s.waitForBoot({
	"SCPROBE: server booted".postln;
	{
		var env = EnvGen.kr(Env.linen(0.05, 5.5, 0.4), doneAction: 2);
		var note = Duty.kr(0.25, 0, Dseq([60, 64, 67, 72, 67, 64], inf));
		(SinOsc.ar(note.midicps) * Decay2.kr(Impulse.kr(4), 0.005, 0.2) * 0.3 * env) ! 2
	}.play;
	SystemClock.sched(7, {
		"SCPROBE: RT done".postln;
		s.quit;
		SystemClock.sched(1, { 0.exit; nil });
		nil
	});
}, 100, { "SCPROBE: boot failed".postln; 1.exit });
)
