export const REPO = "https://github.com/mizcausevic-dev/nostalgia-breakbeat-kit-studio";
export const PAGES = "https://mizcausevic-dev.github.io/nostalgia-breakbeat-kit-studio/";

export type Kit = {
  id: string;
  name: string;
  direction: string;
  bpm: number;
  effective: string;
  key: string;
  region: string;
  startBar: number;
  audio: string;
  midiZip: string;
  combinedMidi: string;
  gain: number;
  kickShare: number;
  quietRatio: number;
  centroidHz: number;
  blurb: string;
};

export const kits: Kit[] = [
  { id: "K01", name: "Freight", direction: "Warehouse Pressure", bpm: 128, effective: "128.000000", key: "A minor", region: "Hook statement", startBar: 24, audio: "audio/K01.m4a", midiZip: "midi-zips/K01-midi.zip", combinedMidi: "midi/K01/Nostalgia_K01_Arrangement_128BPM_KeyA-minor_64bar_Combined.mid", gain: 0.4845226794999056, kickShare: 0.4, quietRatio: 0.131, centroidHz: 9031, blurb: "Straight kick-and-snare weight, a sparse hook, and a hard return." },
  { id: "K02", name: "Rivet", direction: "Warehouse Pressure", bpm: 136, effective: "136.000145", key: "E minor", region: "Full pressure", startBar: 20, audio: "audio/K02.m4a", midiZip: "midi-zips/K02-midi.zip", combinedMidi: "midi/K02/Nostalgia_K02_Arrangement_136BPM_KeyE-minor_64bar_Combined.mid", gain: 0.5429299637692313, kickShare: 0.41, quietRatio: 0.784, centroidHz: 9496, blurb: "Faster pressure. The commercial uses the full-pressure region and the subtraction that follows." },
  { id: "K03", name: "Solvent", direction: "Acid Collision", bpm: 132, effective: "132.000132", key: "F-sharp minor", region: "Hook", startBar: 36, audio: "audio/K03.m4a", midiZip: "midi-zips/K03-midi.zip", combinedMidi: "midi/K03/Nostalgia_K03_Arrangement_132BPM_KeyFs-minor_64bar_Combined.mid", gain: 0.6494548224134606, kickShare: 0.44, quietRatio: 0.452, centroidHz: 9299, blurb: "Acid first, then the break. One region sits on a Phrygian flat two." },
  { id: "K04", name: "Catalyst", direction: "Acid Collision", bpm: 124, effective: "123.999992", key: "D minor", region: "Stab weight", startBar: 28, audio: "audio/K04.m4a", midiZip: "midi-zips/K04-midi.zip", combinedMidi: "midi/K04/Nostalgia_K04_Arrangement_124BPM_KeyD-minor_64bar_Combined.mid", gain: 0.5294802244157467, kickShare: 0.44, quietRatio: 0.124, centroidHz: 8588, blurb: "Swing on hats and bass. Reinforcement uses the ride bell, not the source ride." },
  { id: "K05", name: "Afterglow", direction: "Rave Memory", bpm: 130, effective: "130.000130", key: "C minor", region: "Relative lift", startBar: 24, audio: "audio/K05.m4a", midiZip: "midi-zips/K05-midi.zip", combinedMidi: "midi/K05/Nostalgia_K05_Arrangement_130BPM_KeyC-minor_64bar_Combined.mid", gain: 0.5164921865421319, kickShare: 0.62, quietRatio: 0.231, centroidHz: 9332, blurb: "Stab motif up front, then a relative-major lift before the breakdown." },
  { id: "K06", name: "Sodium", direction: "Rave Memory", bpm: 118, effective: "117.999902", key: "B-flat minor", region: "Peak", startBar: 32, audio: "audio/K06.m4a", midiZip: "midi-zips/K06-midi.zip", combinedMidi: "midi/K06/Nostalgia_K06_Arrangement_118BPM_KeyBb-minor_64bar_Combined.mid", gain: 0.6003310898730388, kickShare: 0.27, quietRatio: 0.088, centroidHz: 9806, blurb: "The sparsest opening in the set, and the loosest bass-to-kick alignment." },
  { id: "K07", name: "Rebar", direction: "Concrete Funk", bpm: 112, effective: "112.000060", key: "G minor", region: "Full groove", startBar: 12, audio: "audio/K07.m4a", midiZip: "midi-zips/K07-midi.zip", combinedMidi: "midi/K07/Nostalgia_K07_Arrangement_112BPM_KeyG-minor_64bar_Combined.mid", gain: 0.5684534194099974, kickShare: 0.51, quietRatio: 0.489, centroidHz: 9663, blurb: "Bass alone, then a dialogue with the break. The iv region is part of the answer." },
  { id: "K08", name: "Formwork", direction: "Concrete Funk", bpm: 116, effective: "116.000085", key: "F dorian", region: "Full", startBar: 32, audio: "audio/K08.m4a", midiZip: "midi-zips/K08-midi.zip", combinedMidi: "midi/K08/Nostalgia_K08_Arrangement_116BPM_KeyF-dorian_64bar_Combined.mid", gain: 0.6121873246602206, kickShare: 0.31, quietRatio: 0.228, centroidHz: 8352, blurb: "Opens without the kick. The only kit written in dorian." },
];

export const directions = ["Warehouse Pressure", "Acid Collision", "Rave Memory", "Concrete Funk"] as const;

export const numerals = [
  { symbol: "i", name: "tonic minor", bars: 416 },
  { symbol: "bVI", name: "lowered sixth, major", bars: 24 },
  { symbol: "IV", name: "major subdominant", bars: 24 },
  { symbol: "bIII", name: "relative major", bars: 18 },
  { symbol: "iv", name: "minor subdominant", bars: 18 },
  { symbol: "bII", name: "Phrygian second", bars: 12 },
];

export const checks = [
  ["01 · count", "192 identity audio files, 24 per kit, match the delivery manifest."],
  ["02 · names", "File names carry kit, role, requested BPM, key or KeyNA, bar length, and variation."],
  ["03 · wav", "48 kHz, 24-bit PCM. Durations follow the integer tempo. Peaks stay under the linear ceiling."],
  ["04 · midi", "Format 0 parts and a format 1 arrangement. Note-offs pair. Bass and acid stay monophonic."],
  ["05 · pitch", "Bass 28–60, hook 48–96, stabs 48–84, acid 36–84, atmosphere 36–96, with the stated voice counts."],
  ["06 · drums", "Channel 10 uses the published General MIDI map. Combined clashes are withheld only from the combined file."],
  ["07 · score", "Structural and harmonic regions each cover all 64 bars. Collections come from the score, not from an audio key detector."],
  ["08 · edits", "Source-to-edit references and slice maps resolve. V03 and the turnaround MIDI are labeled symbolic."],
  ["09 · sum", "Stem sum versus the demo. Largest absolute error 0.00000036. One shared trim, no limiter."],
  ["10 · identity", "Core breaks and primary bass lines are not shared audio across kits."],
];

export const pipeline = [
  ["01", "Compose", "code/nostalgia/kitdata.py", "Eight hand-written kits: breaks, bass, hooks, stabs, acid, atmosphere, fills, and a 64-bar arrangement each."],
  ["02", "Time", "ticks_to_samples()", "960 ticks per quarter. Tempo is integer microseconds per quarter. Sample positions are half-up from absolute ticks."],
  ["03", "Render", "code/nostalgia/render.py", "NumPy and SciPy voices at 48 kHz, 24-bit. The SuperCollider sketch was not executed."],
  ["04", "Export", "WAV · MIDI", "Loops, finite fills and FX, dry companions where the performance can be bypassed, stems, and a demo."],
  ["05", "Validate", "code/nostalgia/validate.py", "Reopens the files named in the delivery manifest. The run reported errors=0 and notes=9."],
  ["06", "Ship", "Vite · gh-pages", "This site plays the same excerpt files it offers for download. A deploy guard allows only web types onto gh-pages."],
];

export const stems = [
  { id: "CoreBreak", label: "Core break", pitch: "Channel 10", fidelity: "V01 and V02 MIDI match the notes. V03 is a slice edit, so its MIDI is symbolic." },
  { id: "Reinforcement", label: "Reinforcement", pitch: "Channel 10", fidelity: "May share drum pitches with the core break when the layer is deliberate." },
  { id: "AuxPerc", label: "Aux percussion", pitch: "Channel 10", fidelity: "The percussion map in the planning manifest is the note list." },
  { id: "Bass", label: "Bass", pitch: "28–60", fidelity: "One voice. The MIDI is the note list." },
  { id: "Hook", label: "Hook", pitch: "48–96", fidelity: "Up to two voices." },
  { id: "Stabs", label: "Stabs", pitch: "48–84", fidelity: "Up to eight voices." },
  { id: "Acid", label: "Acid", pitch: "36–84", fidelity: "One voice. Glide and accent are in the synth, not in overlapping notes." },
  { id: "Atmosphere", label: "Atmosphere", pitch: "36–96", fidelity: "Up to eight voices." },
  { id: "Fill", label: "Fills", pitch: "Channel 10", fidelity: "The turnaround MIDI does not recreate the slice edit." },
  { id: "FX", label: "FX", pitch: "Part file", fidelity: "A dry companion, where one exists, bypasses the waveshaper." },
] as const;

export const dawNotes = [
  {
    tool: "Ableton Live",
    body: "Drop the format 1 combined file on a MIDI track, or drop one format 0 part on its own track. Tempo and 4/4 sit on the conductor at tick 0. Channel 10 is General MIDI drum pitches. A Drum Rack does not assign those pitches for you: map 36 to a kick, 38 to a snare, and 42 to a hat, or use the WAV loops when you want the rendered drums.",
  },
  {
    tool: "FL Studio",
    body: "Import the MIDI onto the playlist. The notes arrive as a piano roll, including channel 10. They do not land on FPC pads unless you map them. If the requested BPM and the effective BPM differ, set the project from the effective tempo in the kit index. That is the integer in the file.",
  },
  {
    tool: "Logic Pro",
    body: "Drag the MIDI into the tracks area and let Logic split channels if you want drums apart from the pitched parts. The file has no program change, no controller, and no plugin preset. Pick the instrument yourself. For Core Break V03 and the turnaround, import the WAV. The MIDI for those two edits is symbolic.",
  },
] as const;
