#!/usr/bin/env python3
"""Cut 8-second stem previews and measure demo loudness.

The previews use the same bar index, the same half-up tick mapping, and the
same 20 ms / 300 ms fades as the demo excerpts. They are not the 64-bar stems.

Loudness is ffmpeg's ebur128 filter (ITU-R BS.1770) with true-peak mode, run
on each full 64-bar demo WAV, including the 2-second tail. This script does
not rewrite the validator. The validator did not measure LUFS or true peak.
"""

from __future__ import annotations

import json
import re
import subprocess
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KITS_ROOT = ROOT.parent / "kits"
PUBLIC = ROOT / "public"
SR = 48_000
PREVIEW_SAMPLES = 8 * SR
FADE_IN = 0.020
FADE_OUT = 0.300

KITS = [
    ("K01", "Freight", 128, 24, "K01_Freight"),
    ("K02", "Rivet", 136, 20, "K02_Rivet"),
    ("K03", "Solvent", 132, 36, "K03_Solvent"),
    ("K04", "Catalyst", 124, 28, "K04_Catalyst"),
    ("K05", "Afterglow", 130, 24, "K05_Afterglow"),
    ("K06", "Sodium", 118, 32, "K06_Sodium"),
    ("K07", "Rebar", 112, 12, "K07_Rebar"),
    ("K08", "Formwork", 116, 32, "K08_Formwork"),
]

STEMS = [
    "CoreBreak",
    "Reinforcement",
    "AuxPerc",
    "Bass",
    "Hook",
    "Stabs",
    "Acid",
    "Atmosphere",
    "Fill",
    "FX",
]


def ticks_to_samples(ticks: int, mpqn: int) -> int:
    numer = ticks * SR * mpqn
    denom = 1_000_000 * 960
    return (numer + denom // 2) // denom


def start_sample(bpm: int, bar: int) -> int:
    mpqn = int(round(60_000_000 / bpm))
    return ticks_to_samples(bar * 3840, mpqn)


def demo_path(folder: str, kit: str, bpm: int) -> Path:
    matches = list((KITS_ROOT / folder / "demo").glob(f"Nostalgia_{kit}_Demo_{bpm}BPM_*.wav"))
    if len(matches) != 1:
        raise SystemExit(f"demo lookup failed for {kit}: {matches}")
    return matches[0]


def stem_path(folder: str, kit: str, stem: str) -> Path:
    matches = list((KITS_ROOT / folder / "stems").glob(f"Nostalgia_{kit}_Stem{stem}_*.wav"))
    if len(matches) != 1:
        raise SystemExit(f"stem lookup failed for {kit} {stem}: {matches}")
    return matches[0]


def measure(path: Path) -> dict[str, float]:
    proc = subprocess.run(
        [
            "ffmpeg",
            "-nostats",
            "-hide_banner",
            "-i",
            str(path),
            "-filter_complex",
            "ebur128=peak=true",
            "-f",
            "null",
            "-",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    text = proc.stderr.split("Summary:", 1)[-1]
    integrated = re.search(r"I:\s+(-?\d+\.\d+) LUFS", text)
    lra = re.search(r"LRA:\s+(-?\d+\.\d+) LU\b", text)
    peak = re.search(r"Peak:\s+(-?\d+\.\d+) dBFS", text)
    if not (integrated and lra and peak):
        raise SystemExit(f"could not parse ebur128 for {path}\n{text[-800:]}")
    return {
        "integratedLufs": float(integrated.group(1)),
        "lraLu": float(lra.group(1)),
        "truePeakDbfs": float(peak.group(1)),
    }


def cut(src: Path, dest: Path, start: int) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    fade_out_at = (PREVIEW_SAMPLES / SR) - FADE_OUT
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(src),
            "-af",
            f"atrim=start_sample={start}:end_sample={start + PREVIEW_SAMPLES},asetpts=PTS-STARTPTS,afade=t=in:st=0:d={FADE_IN},afade=t=out:st={fade_out_at}:d={FADE_OUT}",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            str(dest),
        ],
        check=True,
    )


def zip_dir(src: Path, dest: Path) -> None:
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(src.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(src.parent if src.name == "midi" else src).as_posix() if False else path.relative_to(src).as_posix())


def main() -> None:
    report: dict[str, object] = {
        "meter": "ffmpeg 6.1.1 ebur128 peak=true",
        "standard": "ITU-R BS.1770 integrated loudness, true peak oversampled by the filter",
        "scope": "Each full 64-bar demo WAV, stereo 48 kHz 24-bit, including the 2-second tail.",
        "notInValidator": "The file validator did not measure LUFS or true peak. These numbers were measured afterwards, on the same demo files.",
        "previewFades": "The 20 ms and 300 ms fades are not in these measurements.",
        "kits": {},
    }
    jobs: list[tuple[str, str, Path, Path, int]] = []
    for kit, _name, bpm, bar, folder in KITS:
        start = start_sample(bpm, bar)
        demo = demo_path(folder, kit, bpm)
        numbers = measure(demo)
        report["kits"][kit] = {**numbers, "startSample": start, "demo": demo.name}
        for stem in STEMS:
            src = stem_path(folder, kit, stem)
            dest = PUBLIC / "audio" / "stems" / f"{kit}-{stem}.m4a"
            jobs.append((kit, stem, src, dest, start))
        print(kit, numbers, "start", start, flush=True)

    out = PUBLIC / "data" / "loudness.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    (ROOT / "src" / "loudness.json").write_text(json.dumps(report, indent=2) + "\n")

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda job: cut(job[2], job[3], job[4]), jobs))
    print("stems", len(jobs), flush=True)

    midi = PUBLIC / "midi"
    all_zip = PUBLIC / "nostalgia-midi.zip"
    with zipfile.ZipFile(all_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(midi.rglob("*.mid")):
            archive.write(path, path.relative_to(midi).as_posix())
    kit_zip_dir = PUBLIC / "midi-zips"
    kit_zip_dir.mkdir(exist_ok=True)
    for kit, *_rest in KITS:
        dest = kit_zip_dir / f"{kit}-midi.zip"
        with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted((midi / kit).glob("*.mid")):
                archive.write(path, path.name)
    print("midi zips ready", flush=True)


if __name__ == "__main__":
    main()
