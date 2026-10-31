# Nostalgia

Eight original breakbeat and big-beat construction kits, written as data, rendered to 48 kHz WAV and Standard MIDI Files, and checked by reopening the files. The browser lab plays eight-second excerpts of those demos.

## What's in the pack

- 8 kits, two each in Warehouse Pressure, Acid Collision, Rave Memory, and Concrete Funk
- 192 core identities, 24 per kit, plus source breaks, dry companions, stems, demos, and MIDI
- Tempos from 112 to 136 BPM, integer microseconds per quarter note, 960 ticks per quarter
- A kit index, a percussion map, a SHA-256 manifest of the preview files, and `validation_report.json`
- `nostalgia-excerpts.zip` for the preview audio, the captioned commercial, and that manifest

Conventions and the license for the kits are in [README_KIT_COLLECTION.md](README_KIT_COLLECTION.md) and [LICENSE-KITS.md](LICENSE-KITS.md). The code is MIT. The kits are royalty-free in your own music and are not licensed for redistribution as a sample pack.

The 24-bit stem WAVs are about 3.4 GB. They are not in this repository. GitHub and GitHub Pages cannot hold that set. The lab and the ZIP are the excerpts.

## Run the lab

```bash
npm ci
npm run dev
```

The lab serves at [http://127.0.0.1:43129](http://127.0.0.1:43129). `npm run build` writes `dist/`, including the article at `article.html`.

## Rebuild and check the audio

The renderer is Python, NumPy, and SciPy. A SuperCollider sketch is in `code/supercollider/` and was not executed.

```bash
pip install -r requirements.txt
PYTHONPATH=code python3 -m nostalgia.render
PYTHONPATH=code python3 -m nostalgia.validate
```

`validate` reopens the files named in `docs/delivery-manifest.json` and writes `docs/validation-report.json`. The last completed run reported `errors=0` and `notes=9`. True-peak, LUFS, and listening were not performed.

`scripts/deploy-gh-pages.sh` rebuilds `dist/`, refuses any file that is not a web asset, and publishes the `gh-pages` branch.

## Layout

| Path | What it is |
| --- | --- |
| `code/nostalgia/` | Score, synthesizer, WAV and MIDI writers, validator |
| `code/supercollider/nostalgia-engines.scd` | Unexecuted engine sketch |
| `docs/` | Kit index, percussion map, delivery manifest, validation report |
| `presets/synth-presets.json` | Voice settings used by the renderer |
| `src/` | Vite, React, and the excerpt lab |
| `article/` | Source for the long read |
| `public/audio/` | Eight-second demo excerpts |
| `public/midi/` | Format 0 parts and format 1 arrangements |
| `public/nostalgia-excerpts.zip` | The preview download |
