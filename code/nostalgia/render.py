"""Offline render for the Nostalgia construction kits.

Python/NumPy/SciPy is the renderer that actually runs. SuperCollider is not
installed here. ``code/supercollider/nostalgia-engines.scd`` is an unexecuted
sketch of the same voices.

Timing authority is the integer MIDI tempo (microseconds per quarter). Sample
positions use ``ticks_to_samples`` (half-up, absolute). Bar lengths are not
accumulated from a rounded beat.

Loop exports fade the last 64 samples so the file ends at 0. Arrangement
stems use the unfaded render and keep decay that extends past the last bar of
a loop cycle. A 64-sample fade is not a crossfade across a bad downbeat.
"""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from . import __version__
from .compose import FILL_BARS, build_all, pitched_to_events
from .constants import (
    BAR_TICKS,
    BIT_DEPTH,
    CEILING,
    CONTROL_BLOCK,
    DRUM_GATE,
    PERCUSSION_MAP,
    PITCH_LIMITS,
    SR,
    TAIL_SAMPLES,
    TAIL_SECONDS,
    TARGET_PEAK,
    TPQ,
    encode_tempo,
    quantization_error,
    ticks_to_samples,
)
from .kitdata import ARRANGEMENTS, CUSTOM, KITS
from .midiio import MidiTrack, write_format0, write_format1
from .synth import (
    DrumKit,
    duck_bass,
    fade_end,
    fx_accent,
    fx_build,
    fx_release,
    low_noise_bed,
    midi_to_hz,
    mix_hit,
    render_monophonic,
    render_polyphonic,
)
from .wavio import write_wav

ROOT = Path("/workspace")
DRUM_EXTRA = int(0.85 * SR)
PITCH_EXTRA = int(0.55 * SR)
DRUM_ROLES = {"source", "core", "reinf", "aux", "fill"}
LOOP_FADE = 64

PAN = {
    "kick": 0.0,
    "snare": 0.0,
    "clap": 0.08,
    "ghost": -0.22,
    "rim": -0.28,
    "hat": 0.32,
    "open": 0.38,
    "crash": -0.12,
    "ride": 0.42,
    "bell": -0.18,
    "shaker": 0.48,
    "tamb": -0.4,
    "cowbell": 0.16,
    "conga": -0.3,
}

ROLE_TOKEN = {
    "source": "SourceBreak",
    "core": "CoreBreak",
    "reinf": "Reinforcement",
    "aux": "AuxPerc",
    "bass": "Bass",
    "hook": "Hook",
    "stabs": "Stabs",
    "acid": "Acid",
    "atmos": "Atmosphere",
    "fill": "Fill",
    "fx": "FX",
}

STEM_TOKEN = {role: f"Stem{token}" for role, token in ROLE_TOKEN.items() if role != "source"}
TRACK_NAME = {
    "core": "Core Break",
    "reinf": "Reinforcement Drums",
    "aux": "Auxiliary Percussion",
    "fill": "Drum Fills",
    "bass": "Bass",
    "hook": "Principal Synth Hook",
    "stabs": "Rave Stabs",
    "acid": "Acid Sequence",
    "atmos": "Atmospheric Texture",
    "fx": "Distorted FX",
}
DRUM_TRACK_ORDER = ("core", "reinf", "aux", "fill")
ARR_ROLES = ("core", "reinf", "aux", "fill", "bass", "hook", "stabs", "acid", "atmos", "fx")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _jsonable(value):
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, set):
        return [_jsonable(item) for item in sorted(value, key=str)]
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, Path):
        return value.as_posix()
    return value


def dump(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(payload), indent=2) + "\n", encoding="utf-8")


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def kit_root(kit_id: str, spec: dict) -> Path:
    return ROOT / "kits" / f"{kit_id}_{spec['name']}"


def key_token(pitched_key: str | None) -> str:
    return "KeyNA" if not pitched_key else f"Key{pitched_key}"


def asset_filename(kit_id: str, token: str, bpm: int, key: str, bars: int, variant: str, ext: str) -> str:
    return f"Nostalgia_{kit_id}_{token}_{bpm}BPM_{key}_{int(bars):02d}bar_{variant}.{ext}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def peak_of(audio: np.ndarray) -> float:
    if audio.size == 0:
        return 0.0
    return float(np.max(np.abs(audio)))


def rms_of(audio: np.ndarray) -> float:
    if audio.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(audio))))


def active_span(audio: np.ndarray, thresh: float = 1e-4) -> tuple[int | None, int | None]:
    mag = np.max(np.abs(audio), axis=1) if audio.ndim == 2 else np.abs(audio)
    hits = np.flatnonzero(mag > thresh)
    if hits.size == 0:
        return None, None
    return int(hits[0]), int(hits[-1]) + 1


def restrain(audio: np.ndarray, label: str) -> tuple[np.ndarray, float]:
    peak = peak_of(audio)
    if peak <= CEILING:
        return audio, 1.0
    gain = (CEILING * 0.985) / peak
    print(f"  gain {label}: {gain:.4f} to bring peak {peak:.4f} under the ceiling", flush=True)
    return audio * gain, float(gain)


def warm(kit: DrumKit) -> None:
    for pitch in sorted(PERCUSSION_MAP):
        kit.hit(pitch, False)
        kit.hit(pitch, True)


def render_drums(events, total: int, mpqn: int, kit: DrumKit, processed: bool, stereo: bool) -> tuple[np.ndarray, int]:
    length = total + DRUM_EXTRA
    buffer = np.zeros((length, 2) if stereo else length, dtype=np.float64)
    overflow = 0
    for event in events:
        pos = ticks_to_samples(event.performed_start_tick, mpqn)
        hit = kit.hit(event.pitch, processed) * (event.velocity / 127.0)
        if stereo and event.category == "tom":
            pan = float(np.clip((event.pitch - 45) * 0.05, -0.55, 0.55))
        elif stereo:
            pan = PAN.get(event.category, 0.0)
        else:
            pan = 0.0
        overflow += mix_hit(buffer, hit, pos, pan)
    return buffer, int(overflow)


def render_pitched(events, total: int, mpqn: int, preset: dict, stereo: bool, bed_seed: int | None) -> np.ndarray:
    length = total + PITCH_EXTRA
    if stereo:
        audio = render_polyphonic(events, length, mpqn, preset, ticks_to_samples, True)
        if bed_seed is not None:
            audio = audio + low_noise_bed(length, SR, bed_seed, True) * 0.22
        return audio
    return render_monophonic(events, length, mpqn, preset, ticks_to_samples)


def add_span(dest: np.ndarray, dest_a: int, dest_b: int, src: np.ndarray) -> int:
    if dest.ndim != src.ndim:
        raise RuntimeError("channel mismatch while placing audio")
    if dest_a >= dest.shape[0] or dest_b <= dest_a:
        return 0
    dest_b = min(dest_b, dest.shape[0])
    want = dest_b - dest_a
    got = int(src.shape[0])
    if got > want:
        src = src[:want]
    elif got < want:
        pad = want - got
        src = np.pad(src, (0, pad) if src.ndim == 1 else ((0, pad), (0, 0)))
    dest[dest_a:dest_b] += src
    return int(got - want)


def slice_edit(source: np.ndarray, mpqn: int, slice_ticks: int, perm: list[int], reverse_at: int) -> tuple[np.ndarray, list[dict]]:
    pieces = []
    rows = []
    reversed_once = False
    for new_index, old_index in enumerate(perm):
        do_reverse = old_index == reverse_at and not reversed_once
        if do_reverse:
            reversed_once = True
        src_a = ticks_to_samples(old_index * slice_ticks, mpqn)
        src_b = ticks_to_samples((old_index + 1) * slice_ticks, mpqn)
        dst_a = ticks_to_samples(new_index * slice_ticks, mpqn)
        dst_b = ticks_to_samples((new_index + 1) * slice_ticks, mpqn)
        chunk = source[src_a:src_b].copy()
        if do_reverse:
            chunk = chunk[::-1].copy()
        want = dst_b - dst_a
        got = int(chunk.shape[0])
        if abs(got - want) > 1:
            raise RuntimeError(f"slice fit {got} vs {want} exceeds 1 sample")
        if got > want:
            chunk = chunk[:want]
            fit = "truncate"
        elif got < want:
            pad = want - got
            chunk = np.pad(chunk, (0, pad) if chunk.ndim == 1 else ((0, pad), (0, 0)))
            fit = "pad"
        else:
            fit = "exact"
        pieces.append(chunk)
        rows.append(
            {
                "slice_id": f"SL{old_index:02d}",
                "source_slice": int(old_index),
                "dest_slice": int(new_index),
                "source_start_sample": int(src_a),
                "source_end_sample": int(src_b),
                "dest_start_sample": int(dst_a),
                "dest_end_sample": int(dst_b),
                "reversed": bool(do_reverse),
                "fit": fit,
                "sample_delta": int(got - want),
                "note": "Mixed-audio region. Decay that had already crossed into this slice stays in it. Reversal reverses the region, not individual note events.",
            }
        )
    audio = np.concatenate(pieces, axis=0)
    return audio, rows


def with_extra(audio: np.ndarray, extra: int) -> np.ndarray:
    if audio.ndim == 1:
        out = np.zeros(audio.shape[0] + extra, dtype=np.float64)
        out[: audio.shape[0]] = audio
    else:
        out = np.zeros((audio.shape[0] + extra, audio.shape[1]), dtype=np.float64)
        out[: audio.shape[0]] = audio
    return out


def trim_tail(audio: np.ndarray, container: int) -> tuple[np.ndarray, int]:
    extra = audio[container:]
    if extra.size == 0:
        return audio[:container], 0
    mag = np.max(np.abs(extra), axis=1) if extra.ndim == 2 else np.abs(extra)
    hits = np.flatnonzero(mag > 1e-5)
    if hits.size == 0:
        return audio[:container], 0
    tail = int(hits[-1]) + 1
    return audio[: container + tail], tail


def write_audio(path: Path, audio: np.ndarray) -> dict:
    write_wav(path, audio)
    return {
        "path": rel(path),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "frames": int(audio.shape[0]),
        "channels": 1 if audio.ndim == 1 else int(audio.shape[1]),
        "sample_rate": SR,
        "bit_depth": BIT_DEPTH,
        "peak": peak_of(audio),
        "rms": rms_of(audio),
        "active_start_sample": active_span(audio)[0],
        "active_end_sample": active_span(audio)[1],
    }


def export_loop(path: Path, extended: np.ndarray, container: int) -> tuple[dict, np.ndarray, float]:
    if extended.shape[0] < container:
        raise RuntimeError(f"{path.name} is shorter than its container")
    scaled, gain = restrain(extended, path.name)
    body = scaled[:container].copy()
    fade_end(body, LOOP_FADE)
    record = write_audio(path, body)
    record.update({"output_gain": gain, "end_fade_samples": LOOP_FADE, "tail_samples": 0, "container_samples": int(container)})
    return record, scaled, gain


def export_finite(path: Path, extended: np.ndarray, container: int, fade: bool) -> tuple[dict, np.ndarray, float]:
    if extended.shape[0] < container:
        raise RuntimeError(f"{path.name} is shorter than its container")
    scaled, gain = restrain(extended, path.name)
    body, tail = trim_tail(scaled, container)
    export = body.copy()
    if fade:
        fade_end(export, min(LOOP_FADE, export.shape[0]))
    record = write_audio(path, export)
    record.update(
        {
            "output_gain": gain,
            "end_fade_samples": LOOP_FADE if fade else 0,
            "tail_samples": int(tail),
            "container_samples": int(container),
        }
    )
    return record, scaled, gain


def events_to_json(events) -> list[dict]:
    return [event.to_dict() for event in events]


def coalesce_drums(role_events: dict) -> tuple[dict, list[dict]]:
    """Keep identical same-pitch same-start hits once. Withhold non-identical clashes from the combined file only."""
    grouped: dict[tuple[int, int], list] = {}
    for role in DRUM_TRACK_ORDER:
        for event in role_events[role]:
            grouped.setdefault((event.pitch, event.performed_start_tick), []).append((role, event))
    kept = {role: [] for role in DRUM_TRACK_ORDER}
    log: list[dict] = []
    for (pitch, tick), items in grouped.items():
        if len(items) == 1:
            role, event = items[0]
            kept[role].append(event)
            continue
        signatures = {(event.velocity, event.duration_ticks) for _, event in items}
        if len(signatures) == 1:
            role, event = items[0]
            kept[role].append(event)
            log.append(
                {
                    "action": "coalesce_identical",
                    "pitch": int(pitch),
                    "tick": int(tick),
                    "kept": event.event_id,
                    "dropped_from_combined": [other.event_id for _, other in items[1:]],
                }
            )
        else:
            role, event = items[0]
            kept[role].append(event)
            log.append(
                {
                    "action": "withhold_nonidentical",
                    "pitch": int(pitch),
                    "tick": int(tick),
                    "kept": event.event_id,
                    "withheld_from_combined": [other.event_id for _, other in items[1:]],
                    "reason": "Same GM pitch and start, different velocity or duration. Per-role MIDI keeps every hit.",
                }
            )
    for role in kept:
        kept[role].sort(key=lambda event: (event.performed_start_tick, event.pitch, event.event_id))
    return kept, log


def tile_into(stem: np.ndarray, extended: np.ndarray, container: int, loop_bars: int, start: int, end: int, mute: set[int], mpqn: int, honor_mute: bool) -> list[int]:
    deltas = []
    for bar in range(start, end):
        if honor_mute and bar in mute:
            continue
        local = (bar - start) % loop_bars
        src_a = ticks_to_samples(local * BAR_TICKS, mpqn)
        src_b = ticks_to_samples((local + 1) * BAR_TICKS, mpqn)
        dst_a = ticks_to_samples(bar * BAR_TICKS, mpqn)
        dst_b = ticks_to_samples((bar + 1) * BAR_TICKS, mpqn)
        delta = add_span(stem, dst_a, dst_b, extended[src_a:src_b])
        if abs(delta) > 1:
            raise RuntimeError(f"bar fit delta {delta} at bar {bar}")
        deltas.append(delta)
        if local == loop_bars - 1 and container < extended.shape[0]:
            spill = extended[container:]
            room = stem.shape[0] - dst_b
            if room > 0 and spill.shape[0]:
                use = min(room, spill.shape[0])
                stem[dst_b : dst_b + use] += spill[:use]
    return deltas


def place_container(stem: np.ndarray, extended: np.ndarray, container: int, bar: int, bars: int, mpqn: int) -> None:
    dst_a = ticks_to_samples(bar * BAR_TICKS, mpqn)
    dst_b = ticks_to_samples((bar + bars) * BAR_TICKS, mpqn)
    delta = add_span(stem, dst_a, dst_b, extended[:container])
    if abs(delta) > 1:
        raise RuntimeError(f"finite fit delta {delta}")
    if container < extended.shape[0]:
        spill = extended[container:]
        room = stem.shape[0] - dst_b
        if room > 0 and spill.shape[0]:
            use = min(room, spill.shape[0])
            stem[dst_b : dst_b + use] += spill[:use]


def grid(mpqn: int, slots: int, slice_ticks: int) -> list[dict]:
    rows = []
    for index in range(slots):
        start = index * slice_ticks
        end = (index + 1) * slice_ticks
        rows.append(
            {
                "slice_id": f"SL{index:02d}",
                "start_tick": start,
                "end_tick": end,
                "start_sample": ticks_to_samples(start, mpqn),
                "end_sample": ticks_to_samples(end, mpqn),
            }
        )
    return rows


def clean(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for child in folder.iterdir():
        if child.is_file():
            child.unlink()
        elif child.is_dir():
            shutil.rmtree(child)


def upmix(audio: np.ndarray) -> np.ndarray:
    if audio.ndim == 1:
        return np.stack((audio, audio), axis=1)
    return audio


def render_kit(kit_id: str, build: dict, index: int) -> dict:
    started = time.perf_counter()
    spec = build["spec"]
    bpm = int(spec["bpm"])
    mpqn, effective = encode_tempo(bpm)
    root = kit_root(kit_id, spec)
    folders = {name: root / name for name in ("audio", "midi", "source", "demo", "stems", "data")}
    for folder in folders.values():
        clean(folder)
    print(f"{kit_id} {spec['name']} {bpm} BPM ({effective:.6f} effective)", flush=True)

    kit = DrumKit(spec["drums"], 1000 + index)
    warm(kit)
    files: list[dict] = []
    buffers: dict[str, np.ndarray] = {}
    containers: dict[str, int] = {}
    arrangement = build["arrangement"]
    plan = ARRANGEMENTS[kit_id]
    mute = set(arrangement["mute_bars"])

    def store_loop(asset_key: str, token: str, variant: str, bars: int, key: str, extended: np.ndarray, container: int, folder: Path, **meta):
        name = asset_filename(kit_id, token, bpm, key, bars, variant, "wav")
        record, scaled, _gain = export_loop(folder / name, extended, container)
        record.update(meta)
        record["variant"] = variant
        files.append(record)
        buffers[asset_key] = scaled
        containers[asset_key] = container
        return record

    def store_finite(asset_key: str, token: str, variant: str, bars: int, key: str, extended: np.ndarray, container: int, folder: Path, fade: bool, **meta):
        name = asset_filename(kit_id, token, bpm, key, bars, variant, "wav")
        record, scaled, _gain = export_finite(folder / name, extended, container, fade)
        record.update(meta)
        record["variant"] = variant
        files.append(record)
        buffers[asset_key] = scaled
        containers[asset_key] = container
        return record

    def write_part_midi(folder: Path, token: str, variant: str, bars: int, key: str, events, name: str, **meta):
        boundary = bars * BAR_TICKS
        filename = asset_filename(kit_id, token, bpm, key, bars, variant, "mid")
        path = folder / filename
        write_format0(str(path), name, events, mpqn, boundary)
        record = {"path": rel(path), "sha256": sha256_file(path), "bytes": path.stat().st_size, "kind": "midi", "boundary_ticks": boundary}
        record.update(meta)
        record["variant"] = variant
        files.append(record)

    # Source break, then slice edits that depend on it.
    source_asset = build["assets"]["source"]
    source_total = ticks_to_samples(source_asset["ticks"], mpqn)
    source_proc, source_overflow = render_drums(source_asset["events"], source_total, mpqn, kit, True, True)
    source_dry, _dry_overflow = render_drums(source_asset["events"], source_total, mpqn, kit, False, False)
    store_loop(
        "source",
        "SourceBreak",
        "Source",
        4,
        "KeyNA",
        source_proc,
        source_total,
        folders["source"],
        kind="wav",
        role="source",
        identity=False,
        identity_id=None,
        loop_class="source_reference",
        midi_fidelity="faithful_resynthesis",
        overflow_samples=source_overflow,
        processing="synthesized drums, room taps, waveshaper",
    )
    store_loop(
        "source-dry",
        "SourceBreak",
        "Sourcedry",
        4,
        "KeyNA",
        source_dry,
        source_total,
        folders["source"],
        kind="wav",
        role="source",
        identity=False,
        identity_id=None,
        loop_class="source_reference",
        midi_fidelity="faithful_resynthesis",
        processing="dry excitation only; room and waveshaper bypassed",
    )
    write_part_midi(
        folders["source"],
        "SourceBreak",
        "Source",
        4,
        "KeyNA",
        source_asset["events"],
        f"{kit_id} Source Break",
        role="source",
        identity=False,
        event_source="asset",
        asset_key="source",
        paired_audio=files[0]["path"],
    )
    files[0]["paired_midi"] = files[-1]["path"]
    files[1]["paired_midi"] = files[-1]["path"]

    slice_maps = {
        "half_bar_grid": grid(mpqn, 8, 1920),
        "quarter_bar_grid": grid(mpqn, 16, 960),
        "edits": {},
        "statement": "Slice boundaries are absolute tick positions on the shared tempo grid. Equal tick spans can differ by one sample. Edits are cut from the unfaded render; the exported source file fades its last 64 samples, so those samples are not a byte match. MIDI for these edits is symbolic and does not recreate reversal or mixed-slice timbre.",
    }

    for asset_key, asset in build["assets"].items():
        role = asset["role"]
        if role == "source" or role == "fx":
            continue
        bars = asset["bars"]
        total = ticks_to_samples(asset["ticks"], mpqn)
        token = ROLE_TOKEN[role]
        variant = asset["variant"]
        pitched_key = None if role in DRUM_ROLES or role == "fx" else spec["key_label"]
        key = key_token(pitched_key)
        folder = folders["audio"]
        if role in DRUM_ROLES and asset.get("slice_perm"):
            proc, rows = slice_edit(buffers["source"][:source_total], mpqn, asset["slice_ticks"], list(asset["slice_perm"]), asset["reverse_slice"])
            if proc.shape[0] != total:
                raise RuntimeError(f"{asset_key} sliced {proc.shape[0]} samples, container is {total}")
            dry = None
            if asset.get("dry"):
                dry, _dry_rows = slice_edit(buffers["source-dry"][:source_total], mpqn, asset["slice_ticks"], list(asset["slice_perm"]), asset["reverse_slice"])
                dry = with_extra(dry, DRUM_EXTRA)
            proc = with_extra(proc, DRUM_EXTRA)
            slice_maps["edits"][asset_key] = rows
            meta = dict(
                kind="wav",
                role=role,
                identity=True,
                identity_id=asset["asset_id"],
                loop_class=asset["loop_class"],
                midi_fidelity=asset["midi_fidelity"],
                processing="audio slice edit of the processed source break",
            )
            if asset["loop_class"] == "true_loop":
                store_loop(asset_key, token, variant, bars, key, proc, total, folder, **meta)
                if asset.get("dry"):
                    dry_meta = dict(meta)
                    dry_meta.update(identity=False, identity_id=None, processing="same slice edit of the dry source break")
                    store_loop(f"{asset_key}-dry", token, f"{variant}dry", bars, key, dry, total, folder, **dry_meta)
            else:
                store_finite(asset_key, token, variant, bars, key, proc, total, folder, True, **meta)
        elif role in DRUM_ROLES:
            proc, overflow = render_drums(asset["events"], total, mpqn, kit, True, True)
            meta = dict(
                kind="wav",
                role=role,
                identity=bool(asset["identity"]),
                identity_id=asset["asset_id"] if asset["identity"] else None,
                loop_class=asset["loop_class"],
                midi_fidelity=asset["midi_fidelity"],
                overflow_samples=overflow,
                processing="synthesized drums, room taps, waveshaper; velocity scales amplitude linearly from the shared excitation",
            )
            if asset["loop_class"] == "true_loop":
                store_loop(asset_key, token, variant, bars, key, proc, total, folder, **meta)
                if asset.get("dry") or role == "core":
                    dry, _overflow = render_drums(asset["events"], total, mpqn, kit, False, False)
                    dry_meta = dict(meta)
                    dry_meta.update(
                        identity=False,
                        identity_id=None,
                        processing="dry excitation, no room, no waveshaper, same event times and velocities",
                    )
                    store_loop(f"{asset_key}-dry", token, f"{variant}dry", bars, key, dry, total, folder, **dry_meta)
            else:
                store_finite(asset_key, token, variant, bars, key, proc, total, folder, True, **meta)
        elif role in {"bass", "hook", "stabs", "acid", "atmos"}:
            preset = spec["voices"][role]
            stereo = role in {"hook", "stabs", "atmos"}
            bed = (5000 + index * 2 + (0 if variant == "V01" else 1)) if role == "atmos" else None
            proc = render_pitched(asset["events"], total, mpqn, preset, stereo, bed)
            meta = dict(
                kind="wav",
                role=role,
                identity=True,
                identity_id=asset["asset_id"],
                loop_class=asset["loop_class"],
                midi_fidelity="faithful_resynthesis",
                processing=_voice_processing(role, preset),
            )
            store_loop(asset_key, token, variant, bars, key, proc, total, folder, **meta)
            if asset.get("dry"):
                dry_preset = dict(preset)
                dry_preset["drive"] = 1.0
                dry = render_pitched(asset["events"], total, mpqn, dry_preset, stereo, None if role == "atmos" else None)
                dry_meta = dict(meta)
                dry_meta.update(
                    identity=False,
                    identity_id=None,
                    processing="waveshaper bypassed (drive 1); oscillator, glide, filter, and envelope unchanged; atmosphere noise bed omitted",
                )
                store_loop(f"{asset_key}-dry", token, f"{variant}dry", bars, key, dry, total, folder, **dry_meta)
        if asset["events"] and asset_key in buffers:
            write_part_midi(
                folders["midi"],
                token,
                variant,
                bars,
                key,
                asset["events"],
                f"{kit_id} {TRACK_NAME.get(role, token)} {variant}",
                role=role,
                identity=False,
                event_source="asset",
                asset_key=asset_key,
                companion_of=asset["asset_id"] if asset["identity"] else None,
            )
            midi_path = files[-1]["path"]
            for record in reversed(files):
                if record.get("kind") == "wav" and record.get("role") == role and record.get("variant") in {variant, f"{variant}dry"}:
                    record["paired_midi"] = midi_path
                    if record.get("variant") == variant:
                        files[-1]["paired_audio"] = record["path"]

    # FX gestures.
    fx = spec["fx"]
    build_bars = int(fx["build_bars"])
    release_bars = int(fx["release_bars"])
    build_total = ticks_to_samples(build_bars * BAR_TICKS, mpqn)
    release_total = ticks_to_samples(release_bars * BAR_TICKS, mpqn)
    build_audio = fx_build(build_total, SR, 2000 + index, float(fx["build_end"]), float(fx["drive"]))
    fade_end(build_audio, LOOP_FADE)
    build_audio = with_extra(build_audio, 0)
    release_audio = with_extra(fx_release(release_total, SR, float(fx["release_hz"]), float(fx["drive"]), 3000 + index), 0)
    accent_audio, accent_active = fx_accent(SR, midi_to_hz(36 + spec["tonic_pc"]), float(fx["drive"]), 4000 + index)
    accent_total = ticks_to_samples(BAR_TICKS, mpqn)
    accent_buffer = np.zeros((accent_total, 2), dtype=np.float64)
    use = min(accent_total, accent_audio.shape[0])
    accent_buffer[:use] = accent_audio[:use]
    accent_buffer = with_extra(accent_buffer, 0)
    store_finite(
        "fx-Build",
        "FX",
        "Build",
        build_bars,
        "KeyNA",
        build_audio,
        build_total,
        folders["audio"],
        False,
        kind="wav",
        role="fx",
        identity=True,
        identity_id=f"{kit_id}-FX-Build",
        loop_class="finite_fx",
        midi_fidelity="none",
        fx_class="unpitched",
        processing=f"filtered noise riser to {fx['build_end']} Hz, tanh drive {fx['drive']}, 64-sample end fade",
        event_span=None,
    )
    store_finite(
        "fx-Release",
        "FX",
        "Release",
        release_bars,
        key_token(spec["key_label"]),
        release_audio,
        release_total,
        folders["audio"],
        False,
        kind="wav",
        role="fx",
        identity=True,
        identity_id=f"{kit_id}-FX-Release",
        loop_class="finite_fx",
        midi_fidelity="none",
        fx_class="pitched_glide_no_midi",
        processing=f"sine sweep from {fx['release_hz']} Hz toward 40 Hz plus decaying noise, tanh drive {fx['drive']}. No note MIDI: the glide is continuous.",
        event_span=None,
    )
    store_finite(
        "fx-Accent",
        "FX",
        "Accent",
        1,
        key_token(spec["key_label"]),
        accent_buffer,
        accent_total,
        folders["audio"],
        False,
        kind="wav",
        role="fx",
        identity=True,
        identity_id=f"{kit_id}-FX-Accent",
        loop_class="finite_fx",
        midi_fidelity="partial_tonal_onset",
        fx_class="mixed",
        processing="decaying sine at the kit tonic plus a noise transient. MIDI is the tonal onset only, not the noise or the pitch sweep.",
        audio_active_samples=int(accent_active),
    )
    write_part_midi(
        folders["midi"],
        "FX",
        "Accent",
        1,
        key_token(spec["key_label"]),
        build["assets"]["fx-Accent"]["events"],
        f"{kit_id} Distorted FX Accent",
        role="fx",
        identity=False,
        event_source="asset",
        asset_key="fx-Accent",
        companion_of=f"{kit_id}-FX-Accent",
        midi_fidelity="partial_tonal_onset",
    )
    for record in reversed(files):
        if record.get("kind") == "wav" and record.get("variant") == "Accent":
            record["paired_midi"] = files[-1]["path"]
            files[-1]["paired_audio"] = record["path"]
            break

    # Stop-and-return context: one groove bar, the stop, one groove bar.
    context_total = ticks_to_samples(3 * BAR_TICKS, mpqn)
    context = np.zeros((context_total + DRUM_EXTRA, buffers["core-V01"].shape[1]), dtype=np.float64)
    bar_len = ticks_to_samples(BAR_TICKS, mpqn)
    first = buffers["core-V01"][:bar_len]
    stop = buffers["fill-Stop"]
    stop_container = containers["fill-Stop"]
    add_span(context, 0, bar_len, first)
    add_span(context, bar_len, ticks_to_samples(2 * BAR_TICKS, mpqn), stop[:stop_container])
    third_a = ticks_to_samples(2 * BAR_TICKS, mpqn)
    third_b = ticks_to_samples(3 * BAR_TICKS, mpqn)
    add_span(context, third_a, third_b, first)
    if stop_container < stop.shape[0]:
        spill = stop[stop_container:]
        room = context.shape[0] - ticks_to_samples(2 * BAR_TICKS, mpqn)
        use = min(room, spill.shape[0])
        if use > 0:
            context[ticks_to_samples(2 * BAR_TICKS, mpqn) : ticks_to_samples(2 * BAR_TICKS, mpqn) + use] += spill[:use]
    # The reference stacks a full groove bar on the stop's release. 0.75 keeps that sum under the ceiling.
    context *= 0.75
    store_finite(
        "stop-context",
        "Fill",
        "StopContext",
        3,
        "KeyNA",
        context,
        context_total,
        folders["audio"],
        True,
        kind="wav",
        role="fill",
        identity=False,
        identity_id=None,
        loop_class="audition_reference",
        midi_fidelity="context_reference",
        processing="First bar is Core Break V01. Second bar is the stop-and-return fill. Third bar repeats that Core Break bar, with the stop release added. The sum is scaled by 0.75 so the stacked transients stay under the ceiling. Not an extra identity.",
    )

    # Custom phrases used by the arrangement.
    custom_buffers = {}
    custom_containers = {}
    for start, end, _name, _roles, *custom in plan["sections"]:
        custom_map = custom[0] if custom else {}
        for custom_id in custom_map.values():
            if custom_id in custom_buffers:
                continue
            phrase = CUSTOM[custom_id]
            events, _rep = pitched_to_events(
                phrase["notes"],
                {"fixed_offset": {}, "swing": None, "hat_odd_extra": 0},
                phrase["role"],
                f"{kit_id}-{custom_id}",
                phrase["bars"],
            )
            total = ticks_to_samples(phrase["bars"] * BAR_TICKS, mpqn)
            stereo = phrase["role"] in {"hook", "stabs", "atmos"}
            audio = render_pitched(events, total, mpqn, spec["voices"][phrase["role"]], stereo, None)
            scaled, _gain = restrain(audio, custom_id)
            custom_buffers[custom_id] = scaled
            custom_containers[custom_id] = total

    # Arrangement stems.
    musical = ticks_to_samples(64 * BAR_TICKS, mpqn)
    delivery = musical + TAIL_SAMPLES
    stems = {}
    fit_deltas = []
    for role in ARR_ROLES:
        stereo = role in {"core", "reinf", "aux", "fill", "hook", "stabs", "atmos", "fx"}
        stems[role] = np.zeros((delivery, 2) if stereo else delivery, dtype=np.float64)

    for start, end, _name, roles, *custom in plan["sections"]:
        custom_map = custom[0] if custom else {}
        for role, variant in roles.items():
            key = f"{role}-{variant}"
            fit_deltas.extend(
                tile_into(
                    stems[role],
                    buffers[key],
                    containers[key],
                    build["assets"][key]["bars"],
                    start,
                    end,
                    mute,
                    mpqn,
                    role in {"core", "reinf", "aux"},
                )
            )
        for role, custom_id in custom_map.items():
            phrase = CUSTOM[custom_id]
            fit_deltas.extend(
                tile_into(
                    stems[role],
                    custom_buffers[custom_id],
                    custom_containers[custom_id],
                    phrase["bars"],
                    start,
                    end,
                    mute,
                    mpqn,
                    False,
                )
            )
    for name, bar in plan["fills"]:
        key = f"fill-{name}"
        place_container(stems["fill"], buffers[key], containers[key], bar, FILL_BARS[name], mpqn)
    for name, bar in plan["fx"]:
        key = f"fx-{name}"
        asset = build["assets"][key]
        if name == "Accent":
            dst = ticks_to_samples(bar * BAR_TICKS, mpqn)
            audio = buffers[key]
            end = min(delivery, dst + audio.shape[0])
            stems["fx"][dst:end] += audio[: end - dst]
        else:
            place_container(stems["fx"], buffers[key], containers[key], bar, asset["bars"], mpqn)

    kick_positions = [
        ticks_to_samples(event.performed_start_tick, mpqn)
        for role in ("core", "reinf")
        for event in arrangement["events"][role]
        if event.category == "kick"
    ]
    stems["bass"] = duck_bass(stems["bass"], kick_positions, SR, float(spec["duck"]))

    mixed = np.zeros((delivery, 2), dtype=np.float64)
    for audio in stems.values():
        mixed += upmix(audio)
    sum_peak = peak_of(mixed)
    stem_peak = max(peak_of(audio) for audio in stems.values())
    gain = 1.0
    reason = "sum already at or under the -1 dBFS target"
    if sum_peak > TARGET_PEAK:
        gain = TARGET_PEAK / sum_peak
        reason = "shared linear trim of the summed stems to about -1 dBFS"
    limit = CEILING * 0.985
    if stem_peak * gain > limit:
        gain = limit / stem_peak
        reason = "shared linear trim also kept each stem under the ceiling"
    if gain != 1.0:
        for role in stems:
            stems[role] *= gain
        mixed *= gain
    print(f"  arrangement gain {gain:.4f} ({reason}); pre-trim sum peak {sum_peak:.4f}", flush=True)

    stem_records = []
    for role, audio in stems.items():
        token = STEM_TOKEN[role]
        pitched_key = spec["key_label"] if role in {"bass", "hook", "stabs", "acid", "atmos", "fx"} else None
        if role == "fx":
            pitched_key = spec["key_label"]
        name = asset_filename(kit_id, token, bpm, key_token(pitched_key), 64, "Main", "wav")
        record = write_audio(folders["stems"] / name, audio)
        record.update(
            {
                "kind": "wav",
                "role": role,
                "variant": "Main",
                "identity": False,
                "identity_id": None,
                "loop_class": "arrangement_stem",
                "container_samples": int(musical),
                "tail_samples": int(TAIL_SAMPLES),
                "output_gain": gain,
                "end_fade_samples": 0,
                "stem": True,
            }
        )
        files.append(record)
        stem_records.append(record["path"])
    demo_name = asset_filename(kit_id, "Demo", bpm, key_token(spec["key_label"]), 64, "Main", "wav")
    demo_record = write_audio(folders["demo"] / demo_name, mixed)
    demo_record.update(
        {
            "kind": "wav",
            "role": "demo",
            "variant": "Main",
            "identity": False,
            "loop_class": "demonstration_mix",
            "container_samples": int(musical),
            "tail_samples": int(TAIL_SAMPLES),
            "output_gain": gain,
            "end_fade_samples": 0,
            "stems": stem_records,
            "reconstruction": "Sum of stems after dual-mono upmix of mono stems. No nonlinear master. Compare reopened 24-bit files; expect quantization error, not a mathematical null.",
        }
    )
    files.append(demo_record)

    # Arrangement MIDI.
    kept, coalesce_log = coalesce_drums({role: arrangement["events"][role] for role in DRUM_TRACK_ORDER})
    boundary = 64 * BAR_TICKS
    tracks = [MidiTrack("Conductor", [], None)]
    for role in ARR_ROLES:
        events = kept[role] if role in kept else arrangement["events"][role]
        tracks.append(MidiTrack(f"{kit_id} {TRACK_NAME[role]}", events, None))
        write_part_midi(
            folders["midi"],
            f"Arrangement{ROLE_TOKEN[role]}",
            "Part",
            64,
            key_token(spec["key_label"] if role in {"bass", "hook", "stabs", "acid", "atmos", "fx"} else None),
            arrangement["events"][role],
            f"{kit_id} {TRACK_NAME[role]}",
            role=role,
            identity=False,
            event_source="arrangement",
            arrangement_role=role,
            loop_class="arrangement_midi",
        )
    combined_name = asset_filename(kit_id, "Arrangement", bpm, key_token(spec["key_label"]), 64, "Combined", "mid")
    combined_path = folders["midi"] / combined_name
    write_format1(str(combined_path), tracks, mpqn, boundary)
    files.append(
        {
            "path": rel(combined_path),
            "sha256": sha256_file(combined_path),
            "bytes": combined_path.stat().st_size,
            "kind": "midi",
            "role": "arrangement",
            "variant": "Combined",
            "identity": False,
            "boundary_ticks": boundary,
            "event_source": "combined",
            "coalesce_count": sum(1 for row in coalesce_log if row["action"] == "coalesce_identical"),
            "withheld_count": sum(1 for row in coalesce_log if row["action"] == "withhold_nonidentical"),
        }
    )

    qerr = {
        str(bars): quantization_error(bars * BAR_TICKS, mpqn)
        for bars in (1, 2, 3, 4, 8, 16, 64)
    }
    data = {
        "kit_id": kit_id,
        "name": spec["name"],
        "direction": spec["direction"],
        "bpm_requested": bpm,
        "mpqn": mpqn,
        "bpm_effective": effective,
        "key_label": spec["key_label"],
        "tonic_pc": spec["tonic_pc"],
        "mode": spec["mode"],
        "duck": spec["duck"],
        "duck_note": "Arrangement bass only. Remaining gain at each core or reinforcement kick, then 55 ms return. Pack bass loops are not ducked. V03 reversed kicks can move the audible attack off the MIDI time; the duck follows MIDI.",
        "timing": spec["timing"],
        "quantization_error_samples": qerr,
        "musical_samples": int(musical),
        "delivery_samples": int(delivery),
        "tail_samples": TAIL_SAMPLES,
        "arrangement_gain": gain,
        "arrangement_gain_reason": reason,
        "pretrim_sum_peak": sum_peak,
        "sections": arrangement["sections"],
        "harmony": arrangement["harmony"],
        "fills": arrangement["fills"],
        "fx": arrangement["fx"],
        "mute_bars": arrangement["mute_bars"],
        "changes": arrangement["changes"],
        "coalesce": coalesce_log,
        "fit_delta_max": int(max((abs(item) for item in fit_deltas), default=0)),
        "fit_delta_nonzero": int(sum(1 for item in fit_deltas if item)),
        "swing": _swing_doc(spec["timing"]),
        "identities": [asset["asset_id"] for asset in build["assets"].values() if asset["identity"]],
    }
    dump(folders["data"] / "arrangement.json", data)
    dump(
        folders["data"] / "events.json",
        {
            "assets": {key: events_to_json(asset["events"]) for key, asset in build["assets"].items()},
            "arrangement": {role: events_to_json(events) for role, events in arrangement["events"].items()},
        },
    )
    dump(folders["data"] / "transforms.json", build["transforms"])
    dump(folders["data"] / "repairs.json", build["repairs"])
    dump(folders["source"] / asset_filename(kit_id, "SourceBreak", bpm, "KeyNA", 4, "SliceMap", "json"), slice_maps)
    dump(folders["source"] / asset_filename(kit_id, "SourceBreak", bpm, "KeyNA", 4, "Events", "json"), events_to_json(source_asset["events"]))
    for path in (
        folders["data"] / "arrangement.json",
        folders["data"] / "events.json",
        folders["data"] / "transforms.json",
        folders["data"] / "repairs.json",
        folders["source"] / asset_filename(kit_id, "SourceBreak", bpm, "KeyNA", 4, "SliceMap", "json"),
        folders["source"] / asset_filename(kit_id, "SourceBreak", bpm, "KeyNA", 4, "Events", "json"),
    ):
        files.append({"path": rel(path), "sha256": sha256_file(path), "bytes": path.stat().st_size, "kind": "json", "identity": False})

    identities = [record for record in files if record.get("identity")]
    if len(identities) != 24:
        raise RuntimeError(f"{kit_id} rendered {len(identities)} identity files")
    elapsed = time.perf_counter() - started
    print(f"  {len(files)} files, {len(identities)} identities, {elapsed:.1f}s, coalesce {data['coalesce'] and len(coalesce_log)}", flush=True)
    return {
        "kit_id": kit_id,
        "elapsed_seconds": elapsed,
        "files": files,
        "summary": {key: data[key] for key in ("name", "direction", "bpm_requested", "bpm_effective", "mpqn", "key_label", "arrangement_gain", "pretrim_sum_peak", "fit_delta_max", "identities", "musical_samples", "delivery_samples")},
        "coalesce": coalesce_log,
    }


def _voice_processing(role: str, preset: dict) -> str:
    glide = " Glide is an 80 ms frequency ramp inside the voice when the event flag is set. Note-only MIDI does not contain the ramp." if role in {"bass", "acid"} else ""
    accent = " Velocity at or above 100 is accent intent: the voice raises cutoff, and acid also raises Q by up to 0.6, capped at 8. A receiver of the MIDI may ignore velocity." if role == "acid" else ""
    bed = " A filtered-noise bed is mixed under the tones." if role == "atmos" else ""
    return (
        f"{preset.get('wave')} oscillator, resonant lowpass, drive {preset.get('drive')}, "
        f"cutoff {preset.get('cutoff')} to {preset.get('cutoff_end')} Hz, Q {preset.get('q')}.{glide}{accent}{bed}"
    )


def _swing_doc(timing: dict) -> dict:
    swing = timing.get("swing")
    if not swing:
        return {
            "swing": None,
            "fixed_offset": timing.get("fixed_offset", {}),
            "hat_odd_extra": timing.get("hat_odd_extra", 0),
            "reset": "No swing. Fixed offsets are constant and do not reset. Downbeats are not delayed by swing.",
        }
    return {
        "swing": swing,
        "subdivision_ticks": swing["subdivision_ticks"],
        "offset_ticks": swing["offset_ticks"],
        "instruments": swing["instruments"],
        "reset": "Odd sixteenths of the named instruments are delayed. Even sixteenths, including every downbeat, receive no swing.",
        "fixed_offset": timing.get("fixed_offset", {}),
        "hat_odd_extra": timing.get("hat_odd_extra", 0),
    }


def _preset_document() -> dict:
    kits = {}
    for index, (kit_id, spec) in enumerate(KITS.items(), start=1):
        kits[kit_id] = {
            "drums": spec["drums"],
            "voices": spec["voices"],
            "fx": spec["fx"],
            "timing": spec["timing"],
            "drum_seed": 1000 + index,
            "fx_build_seed": 2000 + index,
            "fx_release_seed": 3000 + index,
            "fx_accent_seed": 4000 + index,
        }
    return {
        "pan": PAN,
        "room_taps_seconds": [0.011, 0.017],
        "room_tap_gains": [0.10, 0.07],
        "glide_seconds": 0.08,
        "accent_velocity_at_or_above": 100,
        "velocity_to_drum_amplitude": "linear, velocity/127, applied to the shared excitation",
        "bypass": {
            "drums": "Dry is the peak-normalized excitation. Processed adds the room taps and tanh waveshaper and is not normalized again.",
            "pitched": "Dry sets waveshaper drive to 1. Oscillator, glide, filter, and envelope stay.",
            "atmosphere": "Noise bed is processed-only.",
        },
        "kits": kits,
    }


def planning_document(builds: dict) -> dict:
    kits = {}
    for kit_id, build in builds.items():
        spec = build["spec"]
        mpqn, effective = encode_tempo(int(spec["bpm"]))
        kits[kit_id] = {
            "name": spec["name"],
            "direction": spec["direction"],
            "bpm_requested": spec["bpm"],
            "mpqn": mpqn,
            "bpm_effective": effective,
            "key_label": spec["key_label"],
            "mode": spec["mode"],
            "tonic_pc": spec["tonic_pc"],
            "identities": [asset["asset_id"] for asset in build["assets"].values() if asset["identity"]],
            "sections": build["arrangement"]["sections"],
            "harmony": build["arrangement"]["harmony"],
            "swing": _swing_doc(spec["timing"]),
        }
    return {
        "collection": "Nostalgia",
        "status": "planned_before_audio",
        "generated_at_utc": _now(),
        "version": __version__,
        "renderer": {
            "implementation": "Python numpy/scipy offline buffers",
            "supercollider": "not installed; nostalgia-engines.scd is not executed",
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "scipy": __import__("scipy").__version__,
            "platform": platform.platform(),
            "sample_rate": SR,
            "bit_depth": BIT_DEPTH,
            "control_block": CONTROL_BLOCK,
            "algorithmic_latency_samples": 0,
            "filter_note": "Lowpass coefficients update every 64 samples. Oscillators are sample accurate. Filter phase delay is not compensated.",
        },
        "timing": {
            "tpq": TPQ,
            "bar_ticks": BAR_TICKS,
            "rounding": "half-up of absolute ticks * 48000 * mpqn / (1000000 * 960); do not accumulate rounded beats",
            "tail_seconds": TAIL_SECONDS,
            "tail_samples": TAIL_SAMPLES,
            "ceiling_linear": CEILING,
            "target_peak_linear": TARGET_PEAK,
            "c4": 60,
        },
        "pitch_limits": {role: {"low": lo, "high": hi, "max_active": limit} for role, (lo, hi, limit) in PITCH_LIMITS.items()},
        "percussion_map": PERCUSSION_MAP,
        "drum_gate_ticks": DRUM_GATE,
        "kits": kits,
        "identity_count": sum(len(item["identities"]) for item in kits.values()),
        "dry_policy": {
            "drums": "Dry is the peak-normalized excitation. Processed is that buffer through room taps and tanh, without a second normalize.",
            "pitched": "Dry sets drive to 1. Glide, filter, and envelope stay. No dry file when drive is already 1.",
            "not_duplicated": "Reinforcement, auxiliary percussion, stabs, atmosphere, fills, and FX do not get a second file just to satisfy a dry/processed pair.",
        },
    }


def write_kit_index(builds: dict, rendered: dict) -> None:
    lines = [
        "# Nostalgia kit index",
        "",
        "Eight original construction kits. Tempos are the requested integers. Effective BPM follows the integer microseconds-per-quarter encoding.",
        "",
        "| Kit | Name | Direction | BPM | Effective BPM | Key | Identities |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for kit_id, build in builds.items():
        spec = build["spec"]
        _mpqn, effective = encode_tempo(int(spec["bpm"]))
        lines.append(
            f"| {kit_id} | {spec['name']} | {spec['direction']} | {spec['bpm']} | {effective:.6f} | {spec['key_label']} | 24 |"
        )
    lines.append("")
    lines.append("## Arrangement regions")
    lines.append("")
    for kit_id, build in builds.items():
        spec = build["spec"]
        lines.append(f"### {kit_id} {spec['name']}")
        lines.append("")
        for region in build["arrangement"]["sections"]:
            lines.append(f"- Bars {region['start_bar']}-{region['end_bar']}: {region['name']}")
        lines.append("")
        for region in build["arrangement"]["harmony"]:
            lines.append(
                f"- Harmony {region['region_id']}: bars {region['start_bar']}-{region['end_bar']}, root pc {region['root_pc']} {region['quality']} ({region['function']}), collection {region['collection_mode']}"
            )
        lines.append("")
    if rendered:
        lines.append("Rendered kits: " + ", ".join(rendered) + ".")
        lines.append("")
    path = ROOT / "docs" / "kit-index.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_percussion_doc() -> None:
    lines = [
        "# Percussion map",
        "",
        "Channel 10. C4 = 60. Gates are symbolic MIDI lengths. Acoustic decay is audio, not an overlapping note.",
        "",
        "| MIDI | GM name | Gate ticks |",
        "| --- | --- | --- |",
    ]
    for pitch, name in PERCUSSION_MAP.items():
        lines.append(f"| {pitch} | {name} | {DRUM_GATE[pitch]} |")
    lines.append("")
    lines.append("Core Break and Reinforcement Drums may share pitches when the layering is deliberate. Combined MIDI coalesces identical same-pitch same-start hits and withholds non-identical clashes from the combined file only. Per-role files keep every hit.")
    lines.append("")
    (ROOT / "docs" / "percussion-map.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str]) -> dict:
    mpqn, _effective = encode_tempo(128)
    if mpqn != 468750 or ticks_to_samples(245760, mpqn) != 5_760_000:
        raise RuntimeError("128 BPM timing anchor failed")
    kits = [item for item in argv if not item.startswith("-")]
    builds = build_all()
    if not kits:
        kits = list(builds)
    unknown = [kit_id for kit_id in kits if kit_id not in builds]
    if unknown:
        raise SystemExit(f"unknown kit {unknown}")
    plan = planning_document(builds)
    dump(ROOT / "docs" / "planning-manifest.json", plan)
    dump(ROOT / "presets" / "synth-presets.json", _preset_document())
    write_percussion_doc()
    write_kit_index(builds, {})
    rendered = {}
    for index, kit_id in enumerate(KITS, start=1):
        if kit_id not in kits:
            continue
        rendered[kit_id] = render_kit(kit_id, builds[kit_id], index)
    delivery = {
        "collection": "Nostalgia",
        "status": "rendered",
        "generated_at_utc": _now(),
        "complete": list(rendered) == list(builds),
        "rendered_kits": list(rendered),
        "identity_files": sum(1 for kit in rendered.values() for record in kit["files"] if record.get("identity")),
        "renderer": plan["renderer"],
        "timing": plan["timing"],
        "kits": rendered,
    }
    dump(ROOT / "docs" / "delivery-manifest.json", delivery)
    write_kit_index(builds, rendered)
    from .page import write_collection_page

    write_collection_page(builds, delivery, ROOT / "reports" / "collection-map-Cursor.html")
    print(f"delivery complete={delivery['complete']} identity files={delivery['identity_files']}", flush=True)
    return delivery


if __name__ == "__main__":
    main(sys.argv[1:])
