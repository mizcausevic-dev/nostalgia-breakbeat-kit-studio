"""Note-only Standard MIDI files.

Format 0 for one part. Format 1 for the combined arrangement, with tempo and
meter on the conductor track only. Note-offs are written before note-ons that
share a tick. Exactly one end-of-track sits at the declared boundary.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from .constants import TPQ
from .events import Event


def _vlq(value: int) -> bytes:
    if value < 0:
        raise ValueError("negative delta")
    buffer = [value & 0x7F]
    value >>= 7
    while value:
        buffer.append((value & 0x7F) | 0x80)
        value >>= 7
    return bytes(reversed(buffer))


def _chunk(tag: bytes, data: bytes) -> bytes:
    return tag + struct.pack(">I", len(data)) + data


def _meta_text(kind: int, text: str) -> bytes:
    raw = text.encode("ascii")
    if len(raw) > 127:
        raise ValueError("meta text too long")
    return bytes([0xFF, kind, len(raw)]) + raw


def _tempo_meta(mpqn: int) -> bytes:
    if not 1 <= mpqn <= 0xFFFFFF:
        raise ValueError("tempo out of range")
    return bytes([0xFF, 0x51, 0x03]) + struct.pack(">I", mpqn)[1:]


def _meter_meta() -> bytes:
    # 4/4, 24 MIDI clocks per quarter, 8 thirty-second notes per quarter.
    return bytes([0xFF, 0x58, 0x04, 0x04, 0x02, 0x18, 0x08])


def _eot() -> bytes:
    return bytes([0xFF, 0x2F, 0x00])


@dataclass
class MidiTrack:
    name: str
    events: list[Event]
    channel: int | None = None


def write_format0(path: str, name: str, events: list[Event], mpqn: int, boundary: int) -> None:
    track = _render_track(name, events, mpqn=mpqn, meter=True, boundary=boundary)
    data = _chunk(b"MThd", struct.pack(">HHH", 0, 1, TPQ)) + track
    with open(path, "wb") as handle:
        handle.write(data)


def write_format1(path: str, tracks: list[MidiTrack], mpqn: int, boundary: int) -> None:
    """First argument is the conductor name via a track with no events and channel None.

    `tracks[0]` is the conductor. Its events must be empty. Tempo and meter are
    written on that track only.
    """
    rendered = []
    for index, track in enumerate(tracks):
        rendered.append(
            _render_track(
                track.name,
                track.events,
                mpqn=mpqn if index == 0 else None,
                meter=index == 0,
                boundary=boundary,
            )
        )
    data = _chunk(b"MThd", struct.pack(">HHH", 1, len(rendered), TPQ)) + b"".join(rendered)
    with open(path, "wb") as handle:
        handle.write(data)


def _render_track(
    name: str,
    events: list[Event],
    *,
    mpqn: int | None,
    meter: bool,
    boundary: int,
) -> bytes:
    timeline: list[tuple[int, int, bytes]] = []
    # order key: offs (0) before other metas already emitted, then ons (1)
    for event in events:
        start = event.performed_start_tick
        end = event.end_tick
        if start < 0 or end > boundary or end <= start:
            raise ValueError(f"MIDI event {event.event_id} outside boundary")
        status_ch = (event.channel - 1) & 0x0F
        timeline.append((start, 1, bytes([0x90 | status_ch, event.pitch & 0x7F, event.velocity & 0x7F])))
        timeline.append((end, 0, bytes([0x80 | status_ch, event.pitch & 0x7F, 0])))
    timeline.sort(key=lambda item: (item[0], item[1]))

    out = bytearray()
    last = 0
    out += _vlq(0) + _meta_text(0x03, name)
    if mpqn is not None:
        out += _vlq(0) + _tempo_meta(mpqn)
    if meter:
        out += _vlq(0) + _meter_meta()
    for tick, _order, payload in timeline:
        if tick < last:
            raise ValueError("MIDI timeline went backwards")
        out += _vlq(tick - last) + payload
        last = tick
    if boundary < last:
        raise ValueError("boundary before last event")
    out += _vlq(boundary - last) + _eot()
    return _chunk(b"MTrk", bytes(out))


def read_midi(path: str) -> dict:
    with open(path, "rb") as handle:
        blob = handle.read()
    if blob[:4] != b"MThd" or len(blob) < 14:
        raise ValueError(f"not a MIDI file: {path}")
    header_len = struct.unpack(">I", blob[4:8])[0]
    fmt, ntrks, division = struct.unpack(">HHH", blob[8:14])
    if header_len != 6:
        raise ValueError("unexpected MIDI header length")
    if division & 0x8000:
        raise ValueError("SMPTE division is not used")
    pos = 8 + header_len
    tracks = []
    for _ in range(ntrks):
        if blob[pos : pos + 4] != b"MTrk":
            raise ValueError("missing MTrk")
        length = struct.unpack(">I", blob[pos + 4 : pos + 8])[0]
        pos += 8
        body = blob[pos : pos + length]
        pos += length
        tracks.append(_parse_track(body))
    if pos != len(blob):
        raise ValueError("trailing bytes after MIDI tracks")
    return {"format": fmt, "division": division, "tracks": tracks}


def _parse_track(body: bytes) -> dict:
    pos = 0
    tick = 0
    name = ""
    tempo = None
    meter = None
    eot = None
    notes_on: dict[tuple[int, int], list[tuple[int, int]]] = {}
    notes: list[dict] = []
    pending: dict[tuple[int, int], list[tuple[int, int]]] = {}
    while pos < len(body):
        delta, pos = _read_vlq(body, pos)
        tick += delta
        if pos >= len(body):
            raise ValueError("truncated MIDI event")
        status = body[pos]
        if status == 0xFF:
            kind = body[pos + 1]
            length, pos = _read_vlq(body, pos + 2)
            data = body[pos : pos + length]
            pos += length
            if kind == 0x03:
                name = data.decode("ascii")
            elif kind == 0x51:
                tempo = int.from_bytes(data, "big")
            elif kind == 0x58:
                meter = (data[0], 2 ** data[1])
            elif kind == 0x2F:
                eot = tick
            else:
                raise ValueError(f"disallowed MIDI meta {kind:#x}")
            continue
        if status & 0xF0 not in (0x80, 0x90):
            raise ValueError(f"disallowed MIDI status {status:#x}")
        channel = (status & 0x0F) + 1
        pitch = body[pos + 1]
        velocity = body[pos + 2]
        pos += 3
        key = (channel, pitch)
        is_off = (status & 0xF0) == 0x80 or velocity == 0
        if not is_off:
            pending.setdefault(key, []).append((tick, velocity))
        else:
            stack = pending.get(key) or []
            if not stack:
                raise ValueError(f"note-off without note-on ch {channel} pitch {pitch}")
            start, vel = stack.pop(0)
            notes.append(
                {
                    "channel": channel,
                    "pitch": pitch,
                    "velocity": vel,
                    "start": start,
                    "duration": tick - start,
                }
            )
    if eot is None:
        raise ValueError("missing end of track")
    unmatched = [key for key, stack in pending.items() if stack]
    if unmatched:
        raise ValueError(f"unmatched note-ons: {unmatched}")
    return {
        "name": name,
        "tempo": tempo,
        "meter": meter,
        "eot": eot,
        "notes": notes,
    }


def _read_vlq(body: bytes, pos: int) -> tuple[int, int]:
    value = 0
    for _ in range(4):
        byte = body[pos]
        pos += 1
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            return value, pos
    raise ValueError("VLQ too long")
