"""Reopen rendered Nostalgia files and check them.

True-peak, LUFS, and listening are not performed. RMS is sqrt(mean(x^2))
over every sample of every channel, then 20*log10. That is not a loudness
standard.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from .constants import (
    BAR_TICKS,
    CEILING,
    PERCUSSION_MAP,
    PITCH_LIMITS,
    SR,
    TAIL_SAMPLES,
    TARGET_PEAK,
    TPQ,
    encode_tempo,
    quantization_error,
    ticks_to_samples,
)
from .midiio import read_midi
from .render import DRUM_TRACK_ORDER, coalesce_drums
from .wavio import read_wav

ROOT = Path("/workspace")
NAME = re.compile(
    r"^Nostalgia_(K0[1-8])_([A-Za-z0-9]+)_(\d{3})BPM_"
    r"(KeyNA|Key(?:A|C|D|E|G|Bb|Fs)-minor|KeyF-dorian)_(\d{2})bar_([A-Za-z0-9]+)\.(wav|mid|json)$"
)


def main() -> int:
    delivery = json.loads((ROOT / "docs" / "delivery-manifest.json").read_text(encoding="utf-8"))
    errors: list[str] = []
    notes: list[str] = []
    review: list[str] = []
    if not delivery.get("complete"):
        errors.append("delivery manifest is not the full 8-kit set")
    mpqn128, _ = encode_tempo(128)
    if ticks_to_samples(64 * BAR_TICKS, mpqn128) != 5_760_000:
        errors.append("128 BPM 64-bar length is not 5760000 samples")

    identity_hashes: dict[str, str] = {}
    core_hashes: dict[str, str] = {}
    bass_hashes: dict[str, str] = {}
    for kit_id, kit in delivery.get("kits", {}).items():
        print(f"validate {kit_id}", flush=True)
        by_path = {}
        events_path = None
        arrangement_path = None
        slice_path = None
        transforms_path = None
        for record in kit["files"]:
            path = ROOT / record["path"]
            if not path.is_file():
                errors.append(f"missing {record['path']}")
                continue
            by_path[record["path"]] = record
            name = path.name
            if record.get("kind") in {"wav", "midi"} or name.startswith("Nostalgia_"):
                match = NAME.match(name)
                if match is None:
                    errors.append(f"name {name}")
                elif int(match.group(3)) != kit["summary"]["bpm_requested"]:
                    errors.append(f"bpm token {name}")
            if path.name.endswith("events.json") and "/data/" in record["path"]:
                events_path = path
            if path.name == "arrangement.json":
                arrangement_path = path
            if path.name.endswith("SliceMap.json"):
                slice_path = path
            if path.name == "transforms.json":
                transforms_path = path
            if record.get("kind") == "wav":
                _check_wav(record, path, kit, errors)
            elif record.get("kind") == "midi":
                _check_midi_file(record, path, kit, errors)
        if events_path and arrangement_path and slice_path and transforms_path:
            _check_music(kit_id, kit, events_path, arrangement_path, slice_path, transforms_path, by_path, errors, notes, review, identity_hashes, core_hashes, bass_hashes)
        else:
            errors.append(f"{kit_id} missing data files")

    if len(core_hashes) > 1 and len(set(core_hashes.values())) != len(core_hashes):
        errors.append("core V01 audio hash is shared by two kits")
    if len(bass_hashes) > 1 and len(set(bass_hashes.values())) != len(bass_hashes):
        errors.append("bass V01 audio hash is shared by two kits")
    identity_count = sum(1 for kit in delivery["kits"].values() for record in kit["files"] if record.get("identity"))
    if delivery.get("complete") and identity_count != 192:
        errors.append(f"identity files {identity_count} != 192")

    report = {
        "errors": errors,
        "notes": notes,
        "review": review,
        "identity_files": identity_count,
        "unperformed": ["true_peak", "integrated_loudness_lufs", "listening"],
        "rms_method": "sqrt(mean(x^2)) over all samples and channels equally; dBFS = 20*log10(rms)",
        "reconstruction": "reopened 24-bit stems, mono copied to both channels, sum compared with the demo",
    }
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "validation-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Validation report",
        "",
        "Checks below reopened the files named in the delivery manifest.",
        "",
        "RMS is sqrt(mean(x^2)) across every sample and every channel. It is not LUFS. True-peak was not measured. Nothing in this report is a listening note.",
        "",
        f"Identity audio files counted: {identity_count}.",
        "",
    ]
    if errors:
        lines.append("## Failures")
        lines.append("")
        lines.extend(f"- {item}" for item in errors)
    else:
        lines.append("## Result")
        lines.append("")
        lines.append("Implemented checks passed on the reopened files.")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.extend(f"- {item}" for item in notes)
    lines.append("")
    lines.append("## Not performed")
    lines.append("")
    lines.append("- True-peak (no oversampling meter).")
    lines.append("- Integrated loudness (no LUFS meter).")
    lines.append("- Listening. Rendering and signal analysis are not listening.")
    lines.append("")
    (ROOT / "docs" / "validation-report.md").write_text("\n".join(lines), encoding="utf-8")
    (ROOT / "docs" / "musical-review.md").write_text(
        "\n".join(
            [
                "# Musical review",
                "",
                "This is a score and signal review. It is not a listening session.",
                "",
                *review,
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"errors={len(errors)} notes={len(notes)}", flush=True)
    for item in errors[:40]:
        print("FAIL", item, flush=True)
    return 1 if errors else 0


def _check_wav(record: dict, path: Path, kit: dict, errors: list[str]) -> None:
    audio, sr, bits, channels = read_wav(str(path))
    if sr != SR or bits != 24:
        errors.append(f"{path.name} format {sr} {bits}")
    if channels != record.get("channels"):
        errors.append(f"{path.name} channels {channels} != {record.get('channels')}")
    if audio.shape[0] != record.get("frames"):
        errors.append(f"{path.name} frames {audio.shape[0]} != {record.get('frames')}")
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak >= 1.0 or peak > CEILING + 1e-4:
        errors.append(f"{path.name} peak {peak:.6f}")
    manifest_peak = record.get("peak")
    if manifest_peak is not None and abs(peak - manifest_peak) > 1e-3:
        errors.append(f"{path.name} peak disagrees with manifest {manifest_peak} vs {peak}")
    gain = record.get("output_gain", 1.0)
    shared_trim = record.get("loop_class") in {"arrangement_stem", "demonstration_mix"}
    if isinstance(gain, float) and gain < 0.8 and not shared_trim:
        errors.append(f"{path.name} output gain {gain:.3f} is doing too much safety scaling")
    bpm = kit["summary"]["bpm_requested"]
    mpqn, _ = encode_tempo(int(bpm))
    loop_class = record.get("loop_class")
    container = record.get("container_samples")
    tail = record.get("tail_samples")
    if loop_class == "true_loop":
        bars = int(NAME.match(path.name).group(5))
        expected = ticks_to_samples(bars * BAR_TICKS, mpqn)
        if audio.shape[0] != expected:
            errors.append(f"{path.name} loop length {audio.shape[0]} != {expected}")
        last = audio[-1] if audio.ndim == 1 else audio[-1]
        if float(np.max(np.abs(last))) > 1e-3:
            errors.append(f"{path.name} loop does not end near 0")
    if loop_class in {"finite_fill", "finite_fx", "audition_reference", "arrangement_stem", "demonstration_mix"}:
        if container is None or tail is None or audio.shape[0] != int(container) + int(tail):
            errors.append(f"{path.name} container/tail {container}+{tail} != {audio.shape[0]}")
    if record.get("identity") and peak < 1e-3:
        errors.append(f"{path.name} identity is silent")
    if loop_class in {"arrangement_stem", "demonstration_mix"}:
        musical = ticks_to_samples(64 * BAR_TICKS, mpqn)
        if container != musical or tail != TAIL_SAMPLES:
            errors.append(f"{path.name} stem grid {container} {tail}")


def _check_midi_file(record: dict, path: Path, kit: dict, errors: list[str]) -> None:
    parsed = read_midi(str(path))
    if parsed["division"] != TPQ:
        errors.append(f"{path.name} division {parsed['division']}")
    bpm = int(kit["summary"]["bpm_requested"])
    mpqn, _ = encode_tempo(bpm)
    if record.get("variant") == "Combined" or record.get("event_source") == "combined":
        if parsed["format"] != 1:
            errors.append(f"{path.name} not format 1")
        if parsed["tracks"][0]["tempo"] != mpqn or parsed["tracks"][0]["meter"] != (4, 4):
            errors.append(f"{path.name} conductor tempo/meter")
        if parsed["tracks"][0]["notes"]:
            errors.append(f"{path.name} conductor has notes")
        for track in parsed["tracks"][1:]:
            if track["tempo"] is not None or track["meter"] is not None:
                errors.append(f"{path.name} tempo outside conductor")
            if track["eot"] != 64 * BAR_TICKS:
                errors.append(f"{path.name} eot {track['eot']}")
    else:
        if parsed["format"] != 0:
            errors.append(f"{path.name} not format 0")
        track = parsed["tracks"][0]
        if track["tempo"] != mpqn or track["meter"] != (4, 4):
            errors.append(f"{path.name} tempo/meter")
        bars = int(NAME.match(path.name).group(5))
        if track["eot"] != bars * BAR_TICKS:
            errors.append(f"{path.name} eot {track['eot']} != {bars * BAR_TICKS}")
    _same_tick_order(path, errors)


def _same_tick_order(path: Path, errors: list[str]) -> None:
    blob = path.read_bytes()
    pos = 14
    while pos + 8 <= len(blob):
        if blob[pos : pos + 4] != b"MTrk":
            break
        length = int.from_bytes(blob[pos + 4 : pos + 8], "big")
        body = blob[pos + 8 : pos + 8 + length]
        pos += 8 + length
        cursor = 0
        tick = 0
        last_tick = -1
        last_kind = -1
        while cursor < len(body):
            delta, cursor = _vlq(body, cursor)
            tick += delta
            status = body[cursor]
            if status == 0xFF:
                kind = body[cursor + 1]
                size, cursor = _vlq(body, cursor + 2)
                cursor += size
                if kind == 0x2F and tick != last_tick:
                    pass
                continue
            if status & 0xF0 not in (0x80, 0x90):
                errors.append(f"{path.name} status {status:#x}")
                return
            kind = 0 if (status & 0xF0) == 0x80 or body[cursor + 2] == 0 else 1
            if tick == last_tick and kind < last_kind:
                errors.append(f"{path.name} note-on before note-off at {tick}")
                return
            last_tick = tick
            last_kind = kind
            cursor += 3


def _vlq(body: bytes, pos: int) -> tuple[int, int]:
    value = 0
    for _ in range(4):
        byte = body[pos]
        pos += 1
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            return value, pos
    raise ValueError("vlq")


def _pairs(notes: list[dict]) -> list[tuple]:
    return sorted((note["pitch"], note["start"], note["duration"], note["velocity"], note["channel"]) for note in notes)


def _event_pairs(events: list[dict]) -> list[tuple]:
    return sorted(
        (event["pitch"], event["performed_start_tick"], event["duration_ticks"], event["velocity"], event["channel"])
        for event in events
    )


def _active_peak(events: list[dict]) -> int:
    points = []
    for event in events:
        points.append((event["performed_start_tick"], 1))
        points.append((event["end_tick"], -1))
    points.sort(key=lambda item: (item[0], item[1]))
    current = 0
    peak = 0
    for _tick, delta in points:
        current += delta
        # Offs are sorted before ons at the same tick because -1 < 1.
        peak = max(peak, current)
    return peak


def _check_music(kit_id, kit, events_path, arrangement_path, slice_path, transforms_path, by_path, errors, notes, review, identity_hashes, core_hashes, bass_hashes):
    events = json.loads(events_path.read_text(encoding="utf-8"))
    arrangement = json.loads(arrangement_path.read_text(encoding="utf-8"))
    slices = json.loads(slice_path.read_text(encoding="utf-8"))
    transforms = json.loads(transforms_path.read_text(encoding="utf-8"))
    mpqn = int(arrangement["mpqn"])
    bpm = int(arrangement["bpm_requested"])
    for bars in (1, 4, 8, 16, 64):
        got = arrangement["quantization_error_samples"][str(bars)]
        expected = quantization_error(bars * BAR_TICKS, mpqn)
        if abs(got - expected) > 1e-9:
            errors.append(f"{kit_id} quantization {bars}")
    _partition(kit_id, arrangement["sections"], errors, "structural")
    _partition(kit_id, arrangement["harmony"], errors, "harmony")
    known_ids = {}
    for key, rows in events["assets"].items():
        for row in rows:
            known_ids[row["event_id"]] = key
        _limits(kit_id, key, rows, errors)
    for role, rows in events["arrangement"].items():
        for row in rows:
            known_ids[row["event_id"]] = f"arr:{role}"
        _limits(kit_id, f"arr-{role}", rows, errors)
    for row in transforms:
        if row.get("source_event_id") not in known_ids:
            errors.append(f"{kit_id} transform source {row.get('source_event_id')}")
        dest = row.get("dest_event_id")
        if dest is not None and dest not in known_ids:
            errors.append(f"{kit_id} transform dest {dest}")
    for name, grid in (("half_bar_grid", slices["half_bar_grid"]), ("quarter_bar_grid", slices["quarter_bar_grid"])):
        for item in grid:
            if item["start_sample"] != ticks_to_samples(item["start_tick"], mpqn):
                errors.append(f"{kit_id} {name} {item['slice_id']} sample map")
    for edit_name, rows in slices["edits"].items():
        if sum(1 for row in rows if row["reversed"]) != 1:
            errors.append(f"{kit_id} {edit_name} reverse count")
        for row in rows:
            if abs(row["sample_delta"]) > 1:
                errors.append(f"{kit_id} {edit_name} sample delta")
    role_events = {}
    for role in DRUM_TRACK_ORDER:
        role_events[role] = [SimpleNamespace(**row) for row in events["arrangement"][role]]
    kept, log = coalesce_drums(role_events)
    if log != arrangement["coalesce"]:
        errors.append(f"{kit_id} coalesce log drifted")
    combined = next(record for record in by_path.values() if record.get("event_source") == "combined")
    parsed = read_midi(str(ROOT / combined["path"]))
    for index, role in enumerate(("core", "reinf", "aux", "fill", "bass", "hook", "stabs", "acid", "atmos", "fx"), start=1):
        if role in kept:
            expect = sorted(
                (event.pitch, event.performed_start_tick, event.duration_ticks, event.velocity, event.channel)
                for event in kept[role]
            )
        else:
            expect = _event_pairs(events["arrangement"][role])
        got = _pairs(parsed["tracks"][index]["notes"])
        if got != expect:
            errors.append(f"{kit_id} combined {role} notes {len(got)} != {len(expect)}")
        part = next(
            record
            for record in by_path.values()
            if record.get("event_source") == "arrangement" and record.get("arrangement_role") == role
        )
        part_notes = _pairs(read_midi(str(ROOT / part["path"]))["tracks"][0]["notes"])
        if part_notes != _event_pairs(events["arrangement"][role]):
            errors.append(f"{kit_id} part {role} disagrees with events")
    for record in by_path.values():
        if record.get("event_source") != "asset":
            continue
        asset_key = record["asset_key"]
        got = _pairs(read_midi(str(ROOT / record["path"]))["tracks"][0]["notes"])
        if got != _event_pairs(events["assets"][asset_key]):
            errors.append(f"{kit_id} {asset_key} MIDI disagrees with events")
    # Reconstruction and section energy.
    stems = [record for record in by_path.values() if record.get("loop_class") == "arrangement_stem"]
    demo = next(record for record in by_path.values() if record.get("loop_class") == "demonstration_mix")
    if len({record["frames"] for record in stems + [demo]}) != 1:
        errors.append(f"{kit_id} stem lengths differ")
    else:
        acc = None
        core_audio = None
        for record in stems:
            audio, _sr, _bits, _ch = read_wav(str(ROOT / record["path"]))
            if record["role"] == "core":
                core_audio = audio
            up = audio if audio.ndim == 2 else np.stack((audio, audio), axis=1)
            acc = up if acc is None else acc + up
        demo_audio, _sr, _bits, _ch = read_wav(str(ROOT / demo["path"]))
        delta = float(np.max(np.abs(acc - demo_audio)))
        notes.append(f"{kit_id} stem-sum max abs error {delta:.8f}")
        if delta > 1e-4:
            errors.append(f"{kit_id} stem reconstruction {delta:.6f}")
        _section_energy(kit_id, arrangement, demo_audio, core_audio, mpqn, errors, review)
    for record in by_path.values():
        if record.get("identity") and record.get("kind") == "wav":
            previous = identity_hashes.get(record["sha256"])
            if previous:
                errors.append(f"duplicate identity audio {record['path']} and {previous}")
            else:
                identity_hashes[record["sha256"]] = record["path"]
        if record.get("role") == "core" and record.get("variant") == "V01":
            core_hashes[kit_id] = record["sha256"]
        if record.get("role") == "bass" and record.get("variant") == "V01":
            bass_hashes[kit_id] = record["sha256"]
        if record.get("variant", "").endswith("dry") and record.get("kind") == "wav":
            wet_variant = record["variant"][: -len("dry")]
            wet = next(
                (
                    item
                    for item in by_path.values()
                    if item.get("role") == record.get("role") and item.get("variant") == wet_variant and item.get("kind") == "wav"
                ),
                None,
            )
            if wet and wet["sha256"] == record["sha256"]:
                errors.append(f"{kit_id} dry duplicates {wet_variant}")
    _overlap(kit_id, events, bpm, review)
    core = next((record for record in by_path.values() if record.get("role") == "core" and record.get("variant") == "V01"), None)
    if core:
        audio, _sr, _bits, _ch = read_wav(str(ROOT / core["path"]))
        mono = audio if audio.ndim == 1 else audio.mean(axis=1)
        window = np.hanning(len(mono))
        spectrum = np.abs(np.fft.rfft(mono * window))
        freqs = np.fft.rfftfreq(len(mono), 1.0 / SR)
        centroid = float(np.sum(freqs * spectrum) / max(np.sum(spectrum), 1e-12))
        rms = float(np.sqrt(np.mean(np.square(mono))))
        review.append(
            f"- {kit_id} core V01 spectral centroid {centroid:.0f} Hz, RMS {20 * math.log10(max(rms, 1e-12)):.1f} dBFS. "
            "Centroid is a magnitude-weighted mean of one Hann-windowed FFT of the whole file, not a key estimate."
        )
    if arrangement["arrangement_gain"] < 0.5:
        notes.append(f"{kit_id} arrangement gain {arrangement['arrangement_gain']:.3f} is heavy")


def _partition(kit_id: str, regions: list[dict], errors: list[str], label: str) -> None:
    cursor = 0
    for region in regions:
        if region["start_bar"] != cursor:
            errors.append(f"{kit_id} {label} gap at {cursor}")
        cursor = region["end_bar"]
    if cursor != 64:
        errors.append(f"{kit_id} {label} ends at {cursor}")


def _limits(kit_id: str, key: str, rows: list[dict], errors: list[str]) -> None:
    if not rows:
        return
    role = key.split("-")[0]
    if role in {"arr"}:
        role = key.split("-", 1)[1]
    if role in {"source", "core", "reinf", "aux", "fill"} or key.startswith("arr-") and role in {"core", "reinf", "aux", "fill"}:
        for row in rows:
            if row["pitch"] not in PERCUSSION_MAP or row["channel"] != 10:
                errors.append(f"{row['event_id']} percussion routing")
            if row["performed_start_tick"] < 0:
                errors.append(f"{row['event_id']} negative")
        return
    if role == "fx" or key.startswith("fx") or key.startswith("arr-fx"):
        for row in rows:
            if not 28 <= row["pitch"] <= 60:
                errors.append(f"{row['event_id']} fx pitch")
        return
    if role not in PITCH_LIMITS:
        return
    lo, hi, limit = PITCH_LIMITS[role]
    for row in rows:
        if not lo <= row["pitch"] <= hi:
            errors.append(f"{row['event_id']} pitch {row['pitch']}")
    if _active_peak(rows) > limit:
        errors.append(f"{kit_id} {key} active notes exceed {limit}")
    if role in {"bass", "acid"} and _active_peak(rows) > 1:
        errors.append(f"{kit_id} {key} polyphony")


def _section_energy(kit_id, arrangement, demo, core, mpqn, errors, review) -> None:
    demo_m = demo if demo.ndim == 1 else demo.mean(axis=1)
    core_m = None if core is None else (core if core.ndim == 1 else core.mean(axis=1))
    loudest = 0.0
    dropout = None
    for region in arrangement["sections"]:
        start = ticks_to_samples(region["start_bar"] * BAR_TICKS, mpqn)
        end = ticks_to_samples(region["end_bar"] * BAR_TICKS, mpqn)
        rms = float(np.sqrt(np.mean(np.square(demo_m[start:end])))) if end > start else 0.0
        review.append(
            f"- {kit_id} {region['name']} bars {region['start_bar'] + 1}-{region['end_bar']}: demo RMS {20 * math.log10(max(rms, 1e-12)):.1f} dBFS"
        )
        roles = region["roles"]
        if "core" not in roles and region["end_bar"] - region["start_bar"] >= 4 and core_m is not None:
            inner_a = min(end, start + SR)
            inner = core_m[inner_a:end]
            if inner.size and float(np.sqrt(np.mean(np.square(inner)))) > 0.02:
                errors.append(f"{kit_id} core leaked into {region['name']}")
        if "core" in roles:
            loudest = max(loudest, rms)
        if "core" not in roles and region["end_bar"] - region["start_bar"] >= 4:
            dropout = rms if dropout is None else min(dropout, rms)
    if dropout is not None and loudest > 0:
        review.append(f"- {kit_id} quiet-region RMS / loudest core-region RMS = {dropout / loudest:.3f}")


def _overlap(kit_id: str, events: dict, bpm: int, review: list[str]) -> None:
    window = int(round(0.02 * bpm / 60.0 * TPQ))
    kicks = [
        event["performed_start_tick"]
        for role in ("core", "reinf")
        for event in events["arrangement"][role]
        if event["category"] == "kick"
    ]
    bass = events["arrangement"]["bass"]
    if not bass or not kicks:
        review.append(f"- {kit_id} kick/bass overlap not computed (missing part)")
        return
    close = 0
    for event in bass:
        start = event["performed_start_tick"]
        if any(abs(start - kick) <= window for kick in kicks):
            close += 1
    fraction = close / len(bass)
    review.append(
        f"- {kit_id} bass note-ons within 20 ms of a kick: {close}/{len(bass)} ({fraction:.2f}). Window is {window} ticks."
    )


if __name__ == "__main__":
    raise SystemExit(main())
