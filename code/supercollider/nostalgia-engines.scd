// NOT EXECUTED.
// SuperCollider is not installed in the environment that rendered Nostalgia.
// The audio on disk was rendered by code/nostalgia/render.py (NumPy/SciPy).
// This file only sketches the same stock-voice ideas so a later SC session
// can see the signal flow. It is not a verified port and it was not run.

// Assumptions if someone runs it later, after checking their own install:
// SuperCollider 3.13 or newer, stock UGens only, 48 kHz, block size 64.
// Offline NRT from a written score. Do not assume a realtime Routine runs
// during NRT. Buffers and envelopes have to exist before the synths that use them.

(
SynthDef(\nostalgia_kick, { |out = 0, amp = 0.5, f0 = 180, f1 = 46, decay = 0.22|
	var trig = Impulse.kr(0);
	var pitch = f1 + (f0 - f1) * EnvGen.kr(Env.perc(0.001, 0.08), trig);
	var body = SinOsc.ar(pitch) * EnvGen.kr(Env.perc(0.001, decay), trig, doneAction: 2);
	var click = BPF.ar(WhiteNoise.ar, 2500, 0.4) * EnvGen.kr(Env.perc(0.0, 0.003), trig);
	Out.ar(out, (body + (click * 0.4)) * amp);
}).add;

SynthDef(\nostalgia_saw, { |out = 0, freq = 110, amp = 0.4, cutoff = 220, q = 1.5, gate = 1, drive = 1|
	// Glide, when used, is a lagged frequency inside the voice. The MIDI file stays note-only.
	var osc = LFSaw.ar(freq);
	var filtered = RLPF.ar(osc, cutoff.clip(30, 18000), (1 / q).clip(0.05, 1));
	var shaped = (filtered * drive).tanh / drive.tanh;
	var env = EnvGen.kr(Env.adsr(0.004, 0.12, 0.7, 0.02), gate, doneAction: 2);
	Out.ar(out, HPF.ar(shaped, 25) * env * amp);
}).add;
)
