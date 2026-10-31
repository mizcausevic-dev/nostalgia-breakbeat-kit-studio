# Nostalgia kit collection

Eight kits. Each one has a single requested tempo, a single key, 4/4, and a 64-bar demonstration arrangement.

| Kit | Name | Direction | BPM | Effective BPM | Key |
| --- | --- | --- | --- | --- | --- |
| K01 | Freight | Warehouse Pressure | 128 | 128.000000 | A minor |
| K02 | Rivet | Warehouse Pressure | 136 | 136.000145 | E minor |
| K03 | Solvent | Acid Collision | 132 | 132.000132 | F-sharp minor |
| K04 | Catalyst | Acid Collision | 124 | 123.999992 | D minor |
| K05 | Afterglow | Rave Memory | 130 | 130.000130 | C minor |
| K06 | Sodium | Rave Memory | 118 | 117.999902 | B-flat minor |
| K07 | Rebar | Concrete Funk | 112 | 112.000060 | G minor |
| K08 | Formwork | Concrete Funk | 116 | 116.000085 | F dorian |

Effective BPM is `60_000_000 / mpqn`, where `mpqn` is the integer microseconds-per-quarter-note written into the MIDI tempo meta. Sample positions are half-up conversions from absolute ticks, not accumulated rounded beats. One bar is 3,840 ticks at 960 ticks per quarter note. C4 is MIDI note 60. Channel 10 is drums.

## What ships with a kit

Each kit has 24 core identities: 17 loops and 7 finite parts. The ten roles are Core Break, Reinforcement Drums, Auxiliary Percussion, Bass, Principal Synth Hook, Rave Stabs, Acid Sequence, Atmospheric Texture, Drum Fills and Break Edits, and Distorted FX.

Source breaks, dry companions, stop-context audition references, arrangement stems, the 64-bar demo, and MIDI are additional files. They are not additional identities.

Core Break V01 and V02 MIDI records the notes. V03 and the fragmented turnaround are audio edits. Their MIDI is symbolic and does not recreate reversal or slice order. Acid glide is in the synthesizer, not in overlapping MIDI notes.

## What the check did

The validator reopened the files named in the delivery manifest. The run reported zero errors and nine notes. Eight notes are stem-sum residuals, the largest absolute error 0.00000036. The ninth is K01’s shared arrangement trim of 0.4845, flagged as heavy. There is one shared linear trim and no limiter. Peak targets were a ceiling near 0.944 and an arrangement target near 0.891.

RMS in the review is `sqrt(mean(x^2))`, not LUFS. True-peak was not measured. Listening was not part of the check. The files were not imported into a commercial DAW in the environment that rendered them.

## Preview files

The excerpts on the site are eight seconds, not eight bars, with a 20 ms fade in and a 300 ms fade out that are not on the original demos. Start bar indexes, 0-based: K01 24, K02 20, K03 36, K04 28, K05 24, K06 32, K07 12, K08 32.

The commercial bed is K02 from bar index 20 through 36. Its fades and level are part of the picture, not of the kit demo.
