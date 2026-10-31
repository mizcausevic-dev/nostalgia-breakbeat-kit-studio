"""Build kit events from kitdata and derive break variations.

V01 and V02 are event edits. Their audio is resynthesized, so their MIDI is
faithful. V03 and the turnaround are audio-slice edits. Their MIDI is a
symbolic rhythm map and does not recreate reversed audio or slice timbre.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import replace

from .constants import BAR_TICKS, ROLE_CHANNEL, scale_pcs
from .events import Event, active_peak, finalize, timing_offset
from .kitdata import ARRANGEMENTS, CUSTOM, KITS

CORE_BARS = 4
PHRASE_BARS = {"bass": 8, "hook": 8, "stabs": 8, "acid": 8, "atmos": 16}
ARR_BARS = 64
FILL_BARS = {"Connector": 1, "Detail": 2, "Stop": 1, "Turnaround": 1}


def _event(prefix: str, index: int, **kwargs) -> Event:
    return Event(event_id=f"{prefix}-E{index:04d}", **kwargs)


def _clone(event: Event, prefix: str, index: int, **changes) -> Event:
    data = replace(event, event_id=f"{prefix}-E{index:04d}", **changes)
    return data


def hits_to_events(hits: list, timing: dict, prefix: str, bars: int) -> tuple[list[Event], list[dict]]:
    container = bars * BAR_TICKS
    raw: list[Event] = []
    for hit in hits:
        kind, position, pitch, velocity, category = hit
        step = position if kind == "step" else (position // 240 if position % 240 == 0 else None)
        nominal = position * 240 if kind == "step" else position
        offset = timing_offset(step, category, timing)
        raw.append(
            _event(
                prefix,
                len(raw) + 1,
                pitch=pitch,
                velocity=int(velocity),
                nominal_start_tick=int(nominal),
                timing_offset_ticks=int(offset),
                duration_ticks=60,
                channel=10,
                category=category,
                midi_fidelity="faithful_resynthesis",
            )
        )
    # Gates depend on pitch and must be applied before overlap repair.
    from .events import drum_gate

    for item in raw:
        item.duration_ticks = drum_gate(item.pitch)
    events, repairs = finalize(raw, container, percussion=True)
    for index, item in enumerate(events, start=1):
        item.event_id = f"{prefix}-E{index:04d}"
    return events, repairs


def pitched_to_events(rows: list, timing: dict, role: str, prefix: str, bars: int) -> tuple[list[Event], list[dict]]:
    from .constants import PITCH_LIMITS

    lo, hi, limit = PITCH_LIMITS[role]
    container = bars * BAR_TICKS
    raw: list[Event] = []
    channel = ROLE_CHANNEL[role]
    for row in rows:
        step, dur_steps, pitches, velocity, glide = row
        if not isinstance(pitches, tuple):
            pitches = (pitches,)
        offset = timing_offset(step, role if role != "stabs" else "stabs", timing)
        # Stabs are not in the swing instrument list unless added. Hooks are not swung.
        if role not in ("bass", "acid"):
            offset = 0
        for pitch in pitches:
            raw.append(
                _event(
                    prefix,
                    len(raw) + 1,
                    pitch=int(pitch),
                    velocity=int(velocity),
                    nominal_start_tick=int(step) * 240,
                    timing_offset_ticks=int(offset),
                    duration_ticks=int(dur_steps) * 240,
                    channel=channel,
                    category=role,
                    glide=bool(glide),
                    midi_fidelity="faithful_resynthesis",
                )
            )
    events, repairs = finalize(
        raw,
        container,
        monophonic=limit == 1,
        max_active=limit,
        pitch_lo=lo,
        pitch_hi=hi,
    )
    for index, item in enumerate(events, start=1):
        item.event_id = f"{prefix}-E{index:04d}"
    return events, repairs


def _step_of(event: Event) -> int | None:
    if event.nominal_start_tick % 240 == 0:
        return event.nominal_start_tick // 240
    return None


def derive_v01(source: list[Event], prefix: str) -> tuple[list[Event], list[dict]]:
    rows: list[dict] = []
    kept: list[Event] = []
    for event in source:
        if event.category == "open":
            rows.append({"source_event_id": event.event_id, "dest_event_id": None, "operation": "omit_open_hat"})
            continue
        nominal = event.nominal_start_tick
        operation = "retain"
        if event.category == "ghost":
            shifted = nominal + 240
            operation = "recontext_ghost"
            # Keep the shift inside the same 4-bar container and off the snare onset.
            if shifted < 4 * BAR_TICKS:
                nominal = shifted
            else:
                operation = "retain"
        clone = _clone(
            event,
            prefix,
            len(kept) + 1,
            nominal_start_tick=nominal,
            source_event_id=event.event_id,
            operation=operation,
            midi_fidelity="faithful_resynthesis",
        )
        kept.append(clone)
        rows.append({"source_event_id": event.event_id, "dest_event_id": clone.event_id, "operation": operation})
    events, repairs = finalize(kept, 4 * BAR_TICKS, percussion=True)
    return events, rows, repairs


def derive_v02(source: list[Event], prefix: str, omit: set[int]) -> tuple[list[Event], list[dict], list[dict]]:
    rows: list[dict] = []
    kept: list[Event] = []
    early_hats = []
    for event in source:
        step = _step_of(event)
        if event.category == "kick" and step is not None and (step % 16) in omit:
            rows.append({"source_event_id": event.event_id, "dest_event_id": None, "operation": "omit_syncopated_kick"})
            continue
        if step is not None and step >= 56 and event.category in {"hat", "open"}:
            rows.append({"source_event_id": event.event_id, "dest_event_id": None, "operation": "truncate_phrase_end"})
            continue
        if step is not None and step >= 48 and event.category in {"tom", "crash", "ride", "bell", "clap"}:
            rows.append({"source_event_id": event.event_id, "dest_event_id": None, "operation": "truncate_phrase_end"})
            continue
        velocity = event.velocity
        operation = "retain"
        if event.category == "snare":
            velocity = min(127, event.velocity + 12)
            operation = "accent_redistribution"
        clone = _clone(
            event,
            prefix,
            len(kept) + 1,
            velocity=velocity,
            source_event_id=event.event_id,
            operation=operation,
            midi_fidelity="faithful_resynthesis",
        )
        kept.append(clone)
        rows.append({"source_event_id": event.event_id, "dest_event_id": clone.event_id, "operation": operation})
        if event.category == "hat" and step is not None and step < 8:
            early_hats.append(event)
    for event in early_hats:
        clone = _clone(
            event,
            prefix,
            len(kept) + 1,
            nominal_start_tick=event.nominal_start_tick + 56 * 240,
            source_event_id=event.event_id,
            operation="fragment_repetition",
            midi_fidelity="faithful_resynthesis",
        )
        kept.append(clone)
        rows.append({"source_event_id": event.event_id, "dest_event_id": clone.event_id, "operation": "fragment_repetition"})
    events, repairs = finalize(kept, 4 * BAR_TICKS, percussion=True)
    id_map = {}
    for index, item in enumerate(events, start=1):
        id_map[item.event_id] = f"{prefix}-E{index:04d}"
        item.event_id = id_map[item.event_id]
    for row in rows:
        if row["dest_event_id"] in id_map:
            row["dest_event_id"] = id_map[row["dest_event_id"]]
    return events, rows, repairs


def _relocate_slices(source: list[Event], prefix: str, perm: list[int], reverse_at, slice_ticks: int, slots: int, container_bars: int) -> tuple[list[Event], list[dict]]:
    groups: list[list[Event]] = [[] for _ in range(slots if slice_ticks * slots > 4 * BAR_TICKS else max(slots, 16))]
    # Source of a turnaround is the 4-bar break, addressed in quarter-bar slices (16).
    source_slots = (4 * BAR_TICKS) // slice_ticks
    groups = [[] for _ in range(source_slots)]
    for event in source:
        index = min(source_slots - 1, event.performed_start_tick // slice_ticks)
        groups[index].append(event)
    container = container_bars * BAR_TICKS
    kept: list[Event] = []
    rows: list[dict] = []
    reversed_once = False
    for new_index, old_index in enumerate(perm):
        do_reverse = old_index == reverse_at and not reversed_once
        if do_reverse:
            reversed_once = True
        repeated = perm.count(old_index) > 1
        for event in groups[old_index]:
            rel = event.performed_start_tick - old_index * slice_ticks
            dur = event.duration_ticks
            if do_reverse:
                rel = slice_ticks - rel - dur
                operation = "reverse_audio"
                fidelity = "symbolic_reverse_audio"
            elif repeated:
                operation = "repeat_fragment"
                fidelity = "symbolic_slice_edit"
            elif new_index != old_index:
                operation = "reorder_slice"
                fidelity = "symbolic_slice_edit"
            else:
                operation = "retain_slice"
                fidelity = "symbolic_slice_edit"
            if rel < 0:
                rel = 0
            if rel + dur >= slice_ticks:
                dur = max(1, slice_ticks - rel - 1)
            start = new_index * slice_ticks + rel
            if start >= container:
                continue
            if start + dur > container:
                dur = container - start
            clone = _clone(
                event,
                prefix,
                len(kept) + 1,
                nominal_start_tick=start,
                timing_offset_ticks=0,
                duration_ticks=dur,
                source_event_id=event.event_id,
                operation=operation,
                midi_fidelity=fidelity,
                slice_id=f"SL{old_index:02d}",
            )
            kept.append(clone)
            rows.append(
                {
                    "source_event_id": event.event_id,
                    "dest_event_id": clone.event_id,
                    "operation": operation,
                    "source_slice": old_index,
                    "dest_slice": new_index,
                    "midi_fidelity": fidelity,
                }
            )
    events, repairs = finalize(kept, container, percussion=True)
    id_map = {}
    for index, item in enumerate(events, start=1):
        id_map[item.event_id] = f"{prefix}-E{index:04d}"
        item.event_id = id_map[item.event_id]
    for row in rows:
        if row["dest_event_id"] in id_map:
            row["dest_event_id"] = id_map[row["dest_event_id"]]
        else:
            row["dest_event_id"] = None
            row["operation"] = row["operation"] + "_dropped_on_repair"
    return events, rows, repairs


def _asset(asset_id: str, role: str, variant: str, bars: int, events: list[Event], **extra) -> dict:
    return {
        "asset_id": asset_id,
        "role": role,
        "variant": variant,
        "bars": bars,
        "ticks": bars * BAR_TICKS,
        "events": events,
        "repairs": extra.pop("repairs", []),
        "transformations": extra.pop("transformations", []),
        "midi_fidelity": extra.pop("midi_fidelity", "faithful_resynthesis"),
        "loop_class": extra.pop("loop_class", "true_loop"),
        "identity": extra.pop("identity", True),
        "pitched": role in ROLE_CHANNEL and role != "fx",
        **extra,
    }


def build_kit(kit_id: str) -> dict:
    spec = KITS[kit_id]
    timing = spec["timing"]
    repairs: list[dict] = []
    transforms: list[dict] = []
    assets: dict[str, dict] = {}

    source_events, source_repairs = hits_to_events(spec["source"], timing, f"{kit_id}-SRC", CORE_BARS)
    repairs.extend(source_repairs)
    assets["source"] = _asset(
        f"{kit_id}-SRC",
        "source",
        "Source",
        CORE_BARS,
        source_events,
        repairs=source_repairs,
        identity=False,
        loop_class="source_reference",
        midi_fidelity="faithful_resynthesis",
        pitched=False,
    )

    v01, rows, rep = derive_v01(source_events, f"{kit_id}-CB1")
    transforms.extend(rows)
    repairs.extend(rep)
    assets["core-V01"] = _asset(f"{kit_id}-CB-V01", "core", "V01", CORE_BARS, v01, repairs=rep, transformations=rows, dry=True)

    v02, rows, rep = derive_v02(source_events, f"{kit_id}-CB2", spec["omit"])
    transforms.extend(rows)
    repairs.extend(rep)
    assets["core-V02"] = _asset(f"{kit_id}-CB-V02", "core", "V02", CORE_BARS, v02, repairs=rep, transformations=rows, dry=True)

    v03, rows, rep = _relocate_slices(source_events, f"{kit_id}-CB3", spec["perm"], spec["reverse"], 1920, 8, CORE_BARS)
    transforms.extend(rows)
    repairs.extend(rep)
    assets["core-V03"] = _asset(
        f"{kit_id}-CB-V03",
        "core",
        "V03",
        CORE_BARS,
        v03,
        repairs=rep,
        transformations=rows,
        midi_fidelity="symbolic_slice_edit",
        dry=True,
        slice_perm=list(spec["perm"]),
        reverse_slice=spec["reverse"],
        slice_ticks=1920,
    )

    for variant, hits in spec["reinf"].items():
        events, rep = hits_to_events(hits, timing, f"{kit_id}-RD{variant[-1]}", CORE_BARS)
        repairs.extend(rep)
        assets[f"reinf-{variant}"] = _asset(f"{kit_id}-RD-{variant}", "reinf", variant, CORE_BARS, events, repairs=rep)
    for variant, hits in spec["aux"].items():
        events, rep = hits_to_events(hits, timing, f"{kit_id}-AP{variant[-1]}", CORE_BARS)
        repairs.extend(rep)
        assets[f"aux-{variant}"] = _asset(f"{kit_id}-AP-{variant}", "aux", variant, CORE_BARS, events, repairs=rep)

    for role in ("bass", "hook", "stabs", "acid", "atmos"):
        for variant, rows_in in spec["phrases"][role].items():
            code = {"bass": "BS", "hook": "HK", "stabs": "ST", "acid": "AC", "atmos": "AT"}[role]
            events, rep = pitched_to_events(rows_in, timing, role, f"{kit_id}-{code}{variant[-1]}", PHRASE_BARS[role])
            repairs.extend(rep)
            assets[f"{role}-{variant}"] = _asset(
                f"{kit_id}-{code}-{variant}",
                role,
                variant,
                PHRASE_BARS[role],
                events,
                repairs=rep,
                dry=role in {"bass", "acid"} or spec["voices"]["hook"]["drive"] > 1.001 and role == "hook",
            )

    for name, payload in spec["fills"].items():
        if name == "Turn":
            events, rows, rep = _relocate_slices(source_events, f"{kit_id}-FLT", payload["order"], payload["reverse"], 960, 4, 1)
            transforms.extend(rows)
            repairs.extend(rep)
            assets["fill-Turnaround"] = _asset(
                f"{kit_id}-FL-Turnaround",
                "fill",
                "Turnaround",
                1,
                events,
                repairs=rep,
                transformations=rows,
                midi_fidelity="symbolic_slice_edit",
                loop_class="finite_fill",
                slice_perm=list(payload["order"]),
                reverse_slice=payload["reverse"],
                slice_ticks=960,
                slice_source_slots=16,
            )
            continue
        variant = name
        events, rep = hits_to_events(payload, timing, f"{kit_id}-FL{name[:1]}", FILL_BARS[name])
        repairs.extend(rep)
        assets[f"fill-{name}"] = _asset(
            f"{kit_id}-FL-{name}",
            "fill",
            name,
            FILL_BARS[name],
            events,
            repairs=rep,
            loop_class="finite_fill",
        )

    tonic_pitch = 36 + spec["tonic_pc"]
    accent_rows = [(0, 1, tonic_pitch, 118, False)]
    accent_events, rep = pitched_to_events(accent_rows, {"fixed_offset": {}, "swing": None, "hat_odd_extra": 0}, "bass", f"{kit_id}-FXA", 1)
    # The impact's tonal partial uses a bass-range pitch, but the role is FX, not bass.
    for item in accent_events:
        item.channel = 6
        item.category = "fx"
        item.midi_fidelity = "partial_tonal_onset"
    repairs.extend(rep)
    assets["fx-Accent"] = _asset(
        f"{kit_id}-FX-Accent",
        "fx",
        "Accent",
        1,
        accent_events,
        repairs=rep,
        loop_class="finite_fx",
        midi_fidelity="partial_tonal_onset",
        pitched=False,
        fx_class="mixed",
        pitch_note=tonic_pitch,
    )
    assets["fx-Build"] = _asset(f"{kit_id}-FX-Build", "fx", "Build", spec["fx"]["build_bars"], [], loop_class="finite_fx", midi_fidelity="none", pitched=False, fx_class="unpitched")
    assets["fx-Release"] = _asset(
        f"{kit_id}-FX-Release",
        "fx",
        "Release",
        spec["fx"]["release_bars"],
        [],
        loop_class="finite_fx",
        midi_fidelity="none",
        pitched=False,
        fx_class="pitched_glide_no_midi",
    )

    arrangement, arr_repairs = _arrange(kit_id, spec, assets)
    repairs.extend(arr_repairs)
    return {
        "kit_id": kit_id,
        "spec": spec,
        "assets": assets,
        "arrangement": arrangement,
        "repairs": repairs,
        "transforms": transforms,
    }


def _arrange(kit_id: str, spec: dict, assets: dict) -> tuple[dict, list[dict]]:
    plan = ARRANGEMENTS[kit_id]
    mute = set()
    for name, bar in plan["fills"]:
        mute.update(range(bar, bar + FILL_BARS[name]))
    by_role: dict[str, list[Event]] = {role: [] for role in ("core", "reinf", "aux", "bass", "hook", "stabs", "acid", "atmos", "fill", "fx")}
    changes: list[dict] = []
    counters = Counter()

    def add_tiled(role: str, events: list[Event], bars: int, start: int, end: int, operation: str, fidelity: str):
        for bar in range(start, end):
            if role in {"core", "reinf", "aux"} and bar in mute:
                continue
            local = (bar - start) % bars
            delta = (bar - local) * BAR_TICKS
            for event in events:
                if event.nominal_start_tick // BAR_TICKS != local:
                    continue
                counters[role] += 1
                clone = _clone(
                    event,
                    f"{kit_id}-ARR-{role[:2].upper()}",
                    counters[role],
                    nominal_start_tick=event.nominal_start_tick + delta,
                    source_event_id=event.event_id,
                    operation=operation,
                    midi_fidelity=fidelity,
                )
                region_end = end * BAR_TICKS
                if clone.performed_start_tick >= region_end or clone.performed_start_tick >= ARR_BARS * BAR_TICKS:
                    continue
                if clone.end_tick > min(region_end, ARR_BARS * BAR_TICKS):
                    clone.duration_ticks = min(region_end, ARR_BARS * BAR_TICKS) - clone.performed_start_tick
                    clone.operation = operation + "_clipped"
                    changes.append({"event_id": clone.event_id, "change": "clipped_at_region", "role": role})
                if clone.duration_ticks > 0:
                    by_role[role].append(clone)

    pcs = scale_pcs(spec["tonic_pc"], spec["mode"])
    for start, end, name, roles, *custom in plan["sections"]:
        custom_map = custom[0] if custom else {}
        for role, variant in roles.items():
            asset = assets[f"{role}-{variant}"]
            add_tiled(role, asset["events"], asset["bars"], start, end, "tile", asset["midi_fidelity"])
        for role, custom_id in custom_map.items():
            phrase = CUSTOM[custom_id]
            events, _rep = pitched_to_events(
                phrase["notes"],
                {"fixed_offset": {}, "swing": None, "hat_odd_extra": 0},
                phrase["role"],
                f"{kit_id}-{custom_id}",
                phrase["bars"],
            )
            add_tiled(role, events, phrase["bars"], start, end, "arrangement_specific", "faithful_resynthesis")
            changes.append({"section": name, "custom": custom_id, "role": role, "change": "arrangement_specific_phrase"})

    for name, bar in plan["fills"]:
        asset = assets[f"fill-{name}"]
        add_tiled("fill", asset["events"], asset["bars"], bar, bar + asset["bars"], "place_fill", asset["midi_fidelity"])

    accent = assets["fx-Accent"]
    for name, bar in plan["fx"]:
        if name == "Accent":
            add_tiled("fx", accent["events"], 1, bar, bar + 1, "place_fx", "partial_tonal_onset")
        else:
            changes.append({"fx": name, "bar": bar, "midi": None, "reason": assets[f"fx-{name}"]["fx_class"]})

    # Finalize each pitched role inside the full arrangement.
    arr_repairs: list[dict] = []
    for role, events in list(by_role.items()):
        if role in {"core", "reinf", "aux", "fill"}:
            finalized, rep = finalize(events, ARR_BARS * BAR_TICKS, percussion=True)
        elif role == "fx":
            finalized, rep = finalize(events, ARR_BARS * BAR_TICKS, pitch_lo=28, pitch_hi=60, max_active=1)
        else:
            from .constants import PITCH_LIMITS

            lo, hi, limit = PITCH_LIMITS[role]
            finalized, rep = finalize(
                events,
                ARR_BARS * BAR_TICKS,
                monophonic=limit == 1,
                max_active=limit,
                pitch_lo=lo,
                pitch_hi=hi,
            )
        by_role[role] = finalized
        arr_repairs.extend(rep)

    harmony = []
    for index, (start, end, root, quality, function, override) in enumerate(plan["harmony"], start=1):
        mode = override or spec["mode"]
        collection = scale_pcs(spec["tonic_pc"], mode)
        harmony.append(
            {
                "region_id": f"{kit_id}-H{index:02d}",
                "start_bar": start,
                "end_bar": end,
                "root_pc": root,
                "quality": quality,
                "function": function,
                "collection_mode": mode,
                "pitch_classes": list(collection),
            }
        )
    sections = []
    for index, (start, end, name, roles, *custom) in enumerate(plan["sections"], start=1):
        sections.append(
            {
                "region_id": f"{kit_id}-S{index:02d}",
                "start_bar": start,
                "end_bar": end,
                "name": name,
                "roles": roles,
                "custom": custom[0] if custom else {},
            }
        )
    return {
        "events": by_role,
        "sections": sections,
        "harmony": harmony,
        "mute_bars": sorted(mute),
        "fills": [{"name": name, "bar": bar, "bars": FILL_BARS[name]} for name, bar in plan["fills"]],
        "fx": [{"name": name, "bar": bar} for name, bar in plan["fx"]],
        "changes": changes,
        "kit_pcs": list(pcs),
    }, arr_repairs


def _plurality(events: list[Event]) -> int | None:
    counts = Counter(event.pitch % 12 for event in events)
    if not counts:
        return None
    ranking = counts.most_common()
    if len(ranking) > 1 and ranking[0][1] == ranking[1][1]:
        return -1
    return ranking[0][0]


def check_collection(builds: dict[str, dict]) -> list[str]:
    errors: list[str] = []
    bass_prints = {}
    kick_prints = {}
    for kit_id, build in builds.items():
        spec = build["spec"]
        pcs = set(scale_pcs(spec["tonic_pc"], spec["mode"]))
        identities = [a for a in build["assets"].values() if a["identity"]]
        if len(identities) != 24:
            errors.append(f"{kit_id} identity count {len(identities)}")
        for asset in build["assets"].values():
            if asset["role"] in {"bass", "hook", "stabs", "acid", "atmos"}:
                for event in asset["events"]:
                    if event.pitch % 12 not in pcs:
                        errors.append(f"{event.event_id} pc {event.pitch % 12} outside {spec['key_label']}")
            if asset["role"] == "core":
                if active_peak(asset["events"]) < 1:
                    errors.append(f"{asset['asset_id']} empty")
        arrangement = build["arrangement"]
        for region in arrangement["harmony"]:
            start = region["start_bar"] * BAR_TICKS
            end = region["end_bar"] * BAR_TICKS
            allowed = set(region["pitch_classes"])
            bass = []
            others = []
            for role, events in arrangement["events"].items():
                if role in {"core", "reinf", "aux", "fill"}:
                    continue
                for event in events:
                    if event.end_tick <= start or event.performed_start_tick >= end:
                        continue
                    if event.pitch % 12 not in allowed:
                        errors.append(f"{event.event_id} conflicts with {region['region_id']}")
                    if role == "bass":
                        bass.append(event)
                    else:
                        others.append(event)
            root = _plurality(bass)
            if bass and root != region["root_pc"]:
                errors.append(
                    f"{kit_id} {region['region_id']} bass plurality {root} != root {region['root_pc']}"
                )
            elif not bass and others and not any(event.pitch % 12 == region["root_pc"] for event in others):
                errors.append(f"{kit_id} {region['region_id']} root absent")
        # Structural partition.
        cursor = 0
        for region in arrangement["sections"]:
            if region["start_bar"] != cursor:
                errors.append(f"{kit_id} structural gap at {cursor}")
            cursor = region["end_bar"]
        if cursor != 64:
            errors.append(f"{kit_id} structural end {cursor}")
        if not 5 <= len(arrangement["sections"]) <= 8:
            errors.append(f"{kit_id} section count")
        cursor = 0
        for region in arrangement["harmony"]:
            if region["start_bar"] != cursor:
                errors.append(f"{kit_id} harmony gap at {cursor}")
            cursor = region["end_bar"]
        if cursor != 64:
            errors.append(f"{kit_id} harmony end {cursor}")
        for role in ("core", "reinf", "aux", "bass", "hook", "stabs", "acid", "atmos", "fill"):
            if not arrangement["events"][role]:
                errors.append(f"{kit_id} arrangement missing {role}")
        if not any(item["name"] == "Accent" for item in arrangement["fx"]):
            errors.append(f"{kit_id} missing accent placement")
        kicks = tuple(event.performed_start_tick for event in build["assets"]["source"]["events"] if event.category == "kick")
        if kicks in kick_prints.values():
            errors.append(f"{kit_id} kick grid duplicates another kit")
        kick_prints[kit_id] = kicks
        bass_fp = tuple(
            (event.performed_start_tick, event.duration_ticks, event.pitch - build["assets"]["bass-V01"]["events"][0].pitch)
            for event in sorted(build["assets"]["bass-V01"]["events"], key=lambda item: item.performed_start_tick)
        )
        if bass_fp in bass_prints.values():
            errors.append(f"{kit_id} bass is a transposition of another kit")
        bass_prints[kit_id] = bass_fp
        for left, right in (("core-V01", "source"), ("core-V02", "core-V01"), ("core-V03", "source"), ("bass-V02", "bass-V01"), ("hook-V02", "hook-V01")):
            a = {(e.performed_start_tick, e.pitch, e.velocity) for e in build["assets"][left]["events"]}
            b = {(e.performed_start_tick, e.pitch, e.velocity) for e in build["assets"][right]["events"]}
            if a == b:
                errors.append(f"{kit_id} {left} duplicates {right}")
    return errors


def build_all() -> dict[str, dict]:
    builds = {}
    failures = []
    for kit_id in KITS:
        try:
            builds[kit_id] = build_kit(kit_id)
        except Exception as exc:
            failures.append(f"{kit_id}: {exc}")
    if failures:
        raise RuntimeError("score build failed\n" + "\n".join(failures))
    errors = check_collection(builds)
    if errors:
        raise RuntimeError("score check failed\n" + "\n".join(errors))
    return builds


if __name__ == "__main__":
    result = build_all()
    for kit_id, build in result.items():
        repairs = len(build["repairs"])
        sections = ",".join(region["name"] for region in build["arrangement"]["sections"])
        print(f"{kit_id} {build['spec']['name']} repairs={repairs} sections={sections}")
