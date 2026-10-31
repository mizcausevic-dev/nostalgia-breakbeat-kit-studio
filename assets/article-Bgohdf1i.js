import{c as l,j as e,r as h,S as d,a as c}from"./index-BpGpvbrD.js";const m=`---
title: "Nostalgia keeps the break and the clock in the same file"
subtitle: "A technical tour of eight original breakbeat kits: 48 kHz WAV, 960-tick MIDI, and a validator that reopens what it wrote."
description: "How the Nostalgia construction kits encode tempo, derive breaks, export stems, and check the files they actually wrote. No listening claim is included."
keywords: "breakbeat construction kit, MIDI 960 PPQ, 48 kHz 24-bit WAV, stem reconstruction, acid sequence MIDI"
audience: "Technical readers"
slug: "technical"
tags: "Music Technology, MIDI, Audio Engineering, Breakbeat, Open Source"
canonical_path: "/articles/technical"
---

Nostalgia is an original breakbeat and big-beat construction kit. It is eight kits, not a sample pack of old records, and not a finished master. The renderer that produced the files on disk is Python, NumPy 2.5.4, and SciPy 1.18.1. A SuperCollider sketch sits in the repository and was not executed. SuperCollider was not installed in the environment that rendered the audio.

If you only need the inventory, it is short. Each kit has one integer tempo between 112 and 136 BPM, one key, a 4/4 meter, a 64-bar demonstration arrangement, 17 loop identities, and 7 finite identities. That is 24 identities per kit and 192 across the collection. Source breaks, dry companions, stop-context references, demos, stems, and MIDI are additional files. They are not additional identities.

This note is about the parts a session will trip over: time, breaks, MIDI honesty, gain, and the checks that were actually run.

## The clock is an integer

The MIDI tempo is the nearest integer number of microseconds per quarter note. That integer is the timing authority for the paired audio. Requested BPM and effective BPM are both recorded, because the integer tempo is not always the exact requested BPM.

At 128 BPM the integer is 468750 microseconds, and the effective tempo is 128 exactly. A 64-bar arrangement at that tempo is 5,760,000 samples at 48 kHz, before the tail. Other kits land a hair off the requested integer. Rivet’s effective tempo is 136.000145 BPM. Sodium’s is 117.999902 BPM. The kit index lists every value. Do not “fix” a loop by accumulating a rounded beat length. Sample positions are half-up conversions from absolute ticks:

\`ticks * 48000 * mpqn / (1_000_000 * 960)\`, then half-up to an integer.

The division is 960 ticks per quarter note. One bar in 4/4 is 3,840 ticks. C4 is MIDI note 60. Note starts are integers. Durations are positive integers. Velocities are 1 through 127. Every note has an explicit note-off. Performed start equals nominal start plus a timing offset, and the duration is measured from the performed start.

Where the ideal musical length falls between samples, the file does not promise a perfect sample-length loop. The quantization error is recorded. A 64-sample fade at the end of a loop export forces the file to end at zero. That fade is not a crossfade hiding a wrong downbeat. Arrangement stems do not use that fade. They keep the decay, then add a shared tail of 96,000 samples, which is 2 seconds at 48 kHz.

## What “original break” means here

Every kit has a 4-bar source break built from synthesized drums. The source ships as audio, MIDI, an event table, and a slice map. It is not a vintage recording, and the documentation does not call it one.

The three Core Break variations come from that source. The first two rearrange and edit note events, and their MIDI is a faithful record of those notes. The third variation, V03, is an audio slice edit. Its MIDI is symbolic. It does not recreate reversal, slice order as sound, or the timbre change that comes from cutting the waveform. The same distinction applies to the fragmented turnaround. If a receiving sampler needs the audio edit, use the WAV. If it needs the notes, use the MIDI and read the fidelity label before you assume they are the same performance.

Reinforcement drums may share General MIDI pitches with the core break when the layering is deliberate. K04 is the clearest example of a pitch that was kept distinct: the source ride is note 51, and reinforcement V02 uses the ride bell, note 53. Combined arrangement MIDI coalesces identical same-pitch, same-start hits and withholds non-identical clashes from the combined file only. The per-role MIDI files keep every hit. Nothing in the combined file should be treated as the full drum part if a clash was withheld. The repairs log for each kit lists notes whose gates were shortened so the same pitch would not overlap. Those are gate repairs. They are not deleted musical ideas.

Channel 10 is drums. Pitched parts use other channels. Individual parts are Standard MIDI File format 0. The combined arrangement is format 1 with a conductor track. Tempo and meter sit on the conductor at tick 0. Note-offs are written before note-ons that share a tick. Each track has one end-of-track event at the container boundary. Controllers, pitch bend, aftertouch, program changes, and SysEx are not in these files.

## Pitch limits are compositional

These limits apply to the notes, not to release tails inside the synthesizer:

- Bass: MIDI 28 through 60, one note at a time.
- Principal hook: 48 through 96, two notes.
- Rave stabs: 48 through 84, eight notes.
- Acid: 36 through 84, one note.
- Atmosphere: 36 through 96, eight notes.

Bass and acid MIDI do not contain overlapping notes. Acid glide and accent are behaviors of the synthesis voice. Velocity carries accent intent. A sampler or synth that receives the MIDI may treat velocity differently, and overlapping notes are not how this project represents a slide. The note list is the note list. The slide, where it exists, is in the audio and in the voice preset.

Dry exports bypass the waveshaper. The performance, the edit, and the alignment stay the same. A reversed slice does not have an identical dry twin. The source break is the reference for that case.

## The arrangement is a sum, then one trim

Each kit has a 64-bar demo, ten aligned stems, and a combined MIDI file for the note-defined roles. Stems share a start, a sample rate, a delivery length, and the two-second tail. Shorter material is padded. Stems are not normalized individually.

The demo is the linear sum of the stems after one shared trim. The trim target is about -1.0 dBFS, linear amplitude \`10 ** (-1/20)\`, approximately 0.891. The per-file ceiling used while rendering hits is about -0.5 dBFS, approximately 0.944. There is no limiter on the demo. K01 Freight needed a trim of 0.4845 to reach the target, which the validator notes as heavy. The other kits landed between 0.516 and 0.649. Relative levels inside a kit are the levels you hear. If K01 feels quieter than the sum of its raw voices, that is the shared trim, not a master bus.

On the reopened files, the maximum absolute error between the summed stems and the demo was 3.6e-7. That is floating-point agreement, not a loudness measurement.

Lowpass coefficients in the voices update every 64 samples. Oscillators are sample accurate. Filter phase delay is not compensated. Algorithmic latency is recorded as zero samples, with that filter note attached so you do not treat the voice as a linear-phase chain.

## What the validator did

\`python -m nostalgia.validate\` reopened the files named in the delivery manifest. It checked identity count, names, WAV format, durations, peaks against the linear ceiling, MIDI pairing and format, pitch and active-note limits, the percussion map, source-to-edit references, slice maps, and the structural and harmonic partitions. Each of those partitions covers all 64 bars. The harmonic collection is taken from the score, not from an audio key detector.

The run reported zero errors and nine notes. Eight notes are the stem-sum residuals. The ninth is the K01 trim.

RMS in the musical review is \`sqrt(mean(x^2))\` over every sample of every channel, then converted with \`20 * log10\`. It is not LUFS. True-peak was not measured. Nobody listened to the files as part of that check. A spectral centroid printed beside a core loop is a single Hann-windowed FFT of the whole file. It is not a key estimate.

A stop-and-return audition reference stacks one bar of Core Break V01, the stop fill, and another bar of the break, then multiplies the stack by 0.75 so the layered transients stay under the ceiling. That file is marked as a reference. It is not one of the 24 identities.

## Render it again

From the repository root, with Python 3.12:

\`\`\`bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
PYTHONPATH=code python3 -m nostalgia.render
PYTHONPATH=code python3 -m nostalgia.validate
\`\`\`

Rendering with no arguments writes all eight kits and replaces the delivery manifest with the full set. Rendering one kit id rewrites the manifest as a subset. Run the full set before you treat the manifest as complete.

Presets live in \`presets/synth-presets.json\`. Planning data, the delivery manifest, the kit index, and the validation report live in \`docs/\`. Per-kit event tables, transforms, slice maps, and arrangement regions live under \`kits/\`.

## What this does not settle

Technical agreement is not a musical verdict. The review document says so in its first lines. Loop a core break in a sampler, solo the bass against the kick, and decide whether the ghost notes are doing work. The files will not make that decision for you.

The project also does not state a license. Do not infer one from the presence of a construction kit, a validation report, or this article.

If you want the short version of the same evidence, open the method page on the launch site, then play an excerpt. The excerpts are eight seconds taken from a named region of the unmastered demo, with a short preview fade. They are not the loop files.
`;function u(i){const t=i.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/),s={};if(!t)return{meta:s,body:i};for(const n of t[1].split(`
`)){const a=n.indexOf(":");a<1||(s[n.slice(0,a).trim()]=n.slice(a+1).trim().replace(/^"|"$/g,""))}return{meta:s,body:t[2].trim()}}function o(i){return i.split(/(`[^`]+`|\*\*[^*]+\*\*)/g).map((t,s)=>t.startsWith("`")&&t.endsWith("`")?e.jsx("code",{children:t.slice(1,-1)},s):t.startsWith("**")&&t.endsWith("**")?e.jsx("strong",{children:t.slice(2,-2)},s):t)}function p(){const{meta:i,body:t}=h.useMemo(()=>u(m),[]),s=t.split(/\n{2,}/);return e.jsxs(e.Fragment,{children:[e.jsx(d,{home:!1}),e.jsxs("main",{id:"article",className:"mx-auto max-w-3xl px-4 py-16 sm:px-6",children:[e.jsx("p",{className:"eyebrow",children:"Technical readers"}),e.jsx("h1",{className:"mt-3 text-4xl font-semibold leading-tight tracking-tight sm:text-5xl",children:i.title}),i.subtitle&&e.jsx("p",{className:"mt-4 text-lg leading-8 text-[var(--muted)]",children:i.subtitle}),e.jsx("div",{className:"article-body mt-8",children:s.map((n,a)=>{if(n.startsWith("## "))return e.jsx("h2",{children:n.slice(3)},a);if(n.startsWith("# "))return e.jsx("h2",{children:n.slice(2)},a);if(n.startsWith("```")){const r=n.replace(/^```[a-z]*\n?/,"").replace(/```$/,"");return e.jsx("pre",{children:e.jsx("code",{children:r})},a)}return n.startsWith("- ")?e.jsx("ul",{children:n.split(`
`).map(r=>e.jsx("li",{children:o(r.replace(/^- /,""))},r))},a):e.jsx("p",{children:o(n)},a)})})]}),e.jsx(c,{home:!1})]})}l.createRoot(document.getElementById("root")).render(e.jsx(h.StrictMode,{children:e.jsx(p,{})}));
