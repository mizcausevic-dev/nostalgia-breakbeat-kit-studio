"""Timing, pitch, and file-format constants for the Nostalgia collection.

C4 is MIDI note 60. Tempo is stored as integer microseconds per quarter note
and that encoded value is the shared timing authority for MIDI and audio.
"""

from __future__ import annotations

SR = 48_000
BIT_DEPTH = 24
TPQ = 960
BAR_TICKS = 3_840  # 4 quarter notes
STEP_TICKS = 240  # sixteenth note

# Post-arrangement audio tail. Not part of the 64-bar musical timeline.
TAIL_SECONDS = 2.0
TAIL_SAMPLES = int(TAIL_SECONDS * SR)  # 96_000 exactly

# Declared peak ceiling, about -0.5 dBFS. Not a true-peak estimate.
CEILING = 10 ** (-0.5 / 20)
# Arrangement trim target, about -1.0 dBFS.
TARGET_PEAK = 10 ** (-1.0 / 20)

# Filter coefficients update on this control block. Audio oscillators are sample accurate.
CONTROL_BLOCK = 64

PITCH_LIMITS = {
    "bass": (28, 60, 1),
    "hook": (48, 96, 2),
    "stabs": (48, 84, 8),
    "acid": (36, 84, 1),
    "atmos": (36, 96, 8),
}

# General MIDI percussion used by this collection. Channel 10 in the file.
PERCUSSION_MAP = {
    36: "Bass Drum 1",
    37: "Side Stick",
    38: "Acoustic Snare",
    39: "Hand Clap",
    41: "Low Floor Tom",
    42: "Closed Hi-Hat",
    43: "High Floor Tom",
    45: "Low Tom",
    46: "Open Hi-Hat",
    47: "Low-Mid Tom",
    48: "Hi-Mid Tom",
    49: "Crash Cymbal 1",
    50: "High Tom",
    51: "Ride Cymbal 1",
    53: "Ride Bell",
    54: "Tambourine",
    56: "Cowbell",
    62: "Mute Hi Conga",
    63: "Open Hi Conga",
    64: "Low Conga",
    70: "Maracas",
    82: "Shaker",
}

# Symbolic MIDI gate lengths. Acoustic decay is an audio tail, not an overlapping note.
DRUM_GATE = {
    36: 60,
    37: 60,
    38: 60,
    39: 60,
    41: 120,
    42: 60,
    43: 120,
    45: 120,
    46: 180,
    47: 120,
    48: 120,
    49: 480,
    50: 120,
    51: 240,
    53: 120,
    54: 60,
    56: 60,
    62: 80,
    63: 80,
    64: 80,
    70: 40,
    82: 40,
}

# 1-based MIDI channels.
CH_BASS = 1
CH_HOOK = 2
CH_STABS = 3
CH_ACID = 4
CH_ATMOS = 5
CH_FX = 6
CH_PERC = 10

ROLE_CHANNEL = {
    "bass": CH_BASS,
    "hook": CH_HOOK,
    "stabs": CH_STABS,
    "acid": CH_ACID,
    "atmos": CH_ATMOS,
    "fx": CH_FX,
}

NATURAL_MINOR = (0, 2, 3, 5, 7, 8, 10)
DORIAN = (0, 2, 3, 5, 7, 9, 10)
PHRYGIAN = (0, 1, 3, 5, 7, 8, 10)

# Accent intent is stored as velocity. Receivers may interpret velocity differently.
ACCENT_VELOCITY = 100

NOTE_NAMES = ("C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B")


def midi_to_hz(note: int) -> float:
    return 440.0 * (2.0 ** ((note - 69) / 12.0))


def encode_tempo(bpm: int) -> tuple[int, float]:
    """Nearest integer microseconds per quarter note, and the resulting BPM."""
    mpqn = int(round(60_000_000 / bpm))
    effective = 60_000_000 / mpqn
    return mpqn, effective


def ticks_to_samples(ticks: int, mpqn: int, sr: int = SR, tpq: int = TPQ) -> int:
    """Absolute sample index of a tick.

    Rounding is half-up on the exact rational position. Callers must use this
    absolute mapping. Do not add rounded per-beat lengths.
    """
    if ticks < 0:
        raise ValueError("negative tick")
    numer = ticks * sr * mpqn
    denom = 1_000_000 * tpq
    return (numer + denom // 2) // denom


def quantization_error(ticks: int, mpqn: int, sr: int = SR, tpq: int = TPQ) -> float:
    """Rounded sample index minus the ideal (possibly fractional) index."""
    ideal = ticks * sr * mpqn / (1_000_000 * tpq)
    return ticks_to_samples(ticks, mpqn, sr, tpq) - ideal


def scale_pcs(tonic_pc: int, mode: str) -> tuple[int, ...]:
    degrees = {"dorian": DORIAN, "phrygian": PHRYGIAN}.get(mode, NATURAL_MINOR)
    return tuple(sorted((tonic_pc + d) % 12 for d in degrees))
