"""Note events, timing offsets, and overlap repair.

performed_start_tick = nominal_start_tick + timing_offset_ticks
Duration is measured from the performed start. Active notes run from note-on
up to, but not including, note-off.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .constants import ACCENT_VELOCITY, DRUM_GATE, PERCUSSION_MAP, PITCH_LIMITS


@dataclass
class Event:
    event_id: str
    pitch: int
    velocity: int
    nominal_start_tick: int
    timing_offset_ticks: int
    duration_ticks: int
    channel: int
    category: str
    glide: bool = False
    accent: bool = False
    source_event_id: str | None = None
    operation: str | None = None
    midi_fidelity: str = "faithful"
    slice_id: str | None = None

    @property
    def performed_start_tick(self) -> int:
        return self.nominal_start_tick + self.timing_offset_ticks

    @property
    def end_tick(self) -> int:
        return self.performed_start_tick + self.duration_ticks

    def to_dict(self) -> dict:
        data = asdict(self)
        data["performed_start_tick"] = self.performed_start_tick
        data["end_tick"] = self.end_tick
        return data


def timing_offset(step: int | None, category: str, timing: dict) -> int:
    """Integer tick offset for a step.

    Swing delays odd sixteenths. Even sixteenths, including each downbeat,
    receive no swing, which is the reset. Constant per-category offsets are
    not swing and do not reset.
    """
    off = int(timing.get("fixed_offset", {}).get(category, 0))
    if step is None:
        return off
    if step % 2 == 1:
        swing = timing.get("swing")
        if swing and category in swing["instruments"]:
            off += int(swing["offset_ticks"])
        if category in ("hat", "open"):
            off += int(timing.get("hat_odd_extra", 0))
    return int(off)


def finalize(
    events: list[Event],
    container_ticks: int,
    *,
    monophonic: bool = False,
    max_active: int | None = None,
    pitch_lo: int | None = None,
    pitch_hi: int | None = None,
    percussion: bool = False,
) -> tuple[list[Event], list[dict]]:
    """Validate events and shorten overlaps.

    Shortening is recorded. It is a safety repair, not a silent musical edit.
    """
    repairs: list[dict] = []
    kept: list[Event] = []
    for event in events:
        start = event.performed_start_tick
        if start < 0:
            raise ValueError(f"{event.event_id} negative start {start}")
        if start >= container_ticks:
            raise ValueError(f"{event.event_id} starts at or beyond {container_ticks}")
        if event.duration_ticks <= 0:
            raise ValueError(f"{event.event_id} non-positive duration")
        if not 1 <= event.velocity <= 127:
            raise ValueError(f"{event.event_id} velocity {event.velocity}")
        if percussion:
            if event.pitch not in PERCUSSION_MAP:
                raise ValueError(f"{event.event_id} pitch {event.pitch} not in percussion map")
            if event.channel != 10:
                raise ValueError(f"{event.event_id} percussion not on channel 10")
        else:
            if pitch_lo is not None and not pitch_lo <= event.pitch <= pitch_hi:
                raise ValueError(
                    f"{event.event_id} pitch {event.pitch} outside {pitch_lo}-{pitch_hi}"
                )
        end = start + event.duration_ticks
        if end > container_ticks:
            new_dur = container_ticks - start
            if new_dur <= 0:
                raise ValueError(f"{event.event_id} cannot fit in container")
            repairs.append(
                {
                    "event_id": event.event_id,
                    "repair": "shorten_to_boundary",
                    "from": event.duration_ticks,
                    "to": new_dur,
                }
            )
            event.duration_ticks = new_dur
        if event.accent and event.velocity < ACCENT_VELOCITY:
            raise ValueError(f"{event.event_id} accent flag but velocity {event.velocity}")
        if event.velocity >= ACCENT_VELOCITY:
            event.accent = True
        kept.append(event)

    kept.sort(key=lambda item: (item.performed_start_tick, item.pitch, item.event_id))
    if monophonic:
        _shorten_overlaps(kept, repairs, same_pitch_only=False)
    else:
        _shorten_overlaps(kept, repairs, same_pitch_only=True)

    if max_active is not None:
        peak = active_peak(kept)
        if peak > max_active:
            raise ValueError(f"active notes {peak} exceed limit {max_active}")
    return kept, repairs


def _shorten_overlaps(events: list[Event], repairs: list[dict], same_pitch_only: bool) -> None:
    previous: list[Event] = []
    for event in events:
        still_open: list[Event] = []
        for prior in previous:
            if prior.end_tick <= event.performed_start_tick:
                continue
            clash = (not same_pitch_only) or prior.pitch == event.pitch
            if clash and prior.end_tick > event.performed_start_tick:
                new_dur = event.performed_start_tick - prior.performed_start_tick
                if new_dur <= 0:
                    raise ValueError(
                        f"unrepairable overlap {prior.event_id} vs {event.event_id}"
                    )
                repairs.append(
                    {
                        "event_id": prior.event_id,
                        "repair": "shorten_overlap",
                        "against": event.event_id,
                        "from": prior.duration_ticks,
                        "to": new_dur,
                    }
                )
                prior.duration_ticks = new_dur
            if prior.end_tick > event.performed_start_tick:
                still_open.append(prior)
        previous = still_open + [event]


def active_peak(events: list[Event]) -> int:
    points: list[tuple[int, int]] = []
    for event in events:
        points.append((event.performed_start_tick, 1))
        points.append((event.end_tick, -1))
    points.sort(key=lambda item: (item[0], item[1]))
    current = 0
    peak = 0
    for _tick, delta in points:
        current += delta
        peak = max(peak, current)
    return peak


def same_pitch_overlaps(events: list[Event]) -> list[tuple[str, str]]:
    bad: list[tuple[str, str]] = []
    by_pitch: dict[int, list[Event]] = {}
    for event in events:
        by_pitch.setdefault(event.pitch, []).append(event)
    for group in by_pitch.values():
        group.sort(key=lambda item: item.performed_start_tick)
        for left, right in zip(group, group[1:]):
            if left.end_tick > right.performed_start_tick:
                bad.append((left.event_id, right.event_id))
    return bad


def limits_for(role: str) -> tuple[int, int, int] | None:
    return PITCH_LIMITS.get(role)


def drum_gate(pitch: int) -> int:
    if pitch not in DRUM_GATE:
        raise KeyError(pitch)
    return DRUM_GATE[pitch]
