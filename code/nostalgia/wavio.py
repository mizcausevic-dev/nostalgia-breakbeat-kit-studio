"""24-bit PCM WAV read and write. Little-endian, no extra chunks."""

from __future__ import annotations

import struct

import numpy as np

from .constants import BIT_DEPTH, SR


def write_wav(path: str, audio: np.ndarray, sr: int = SR) -> None:
    if sr != SR:
        raise ValueError("sample rate must be 48000")
    data = np.asarray(audio, dtype=np.float64)
    if data.ndim == 1:
        channels = 1
        frames = data
    elif data.ndim == 2 and data.shape[1] in (1, 2):
        channels = data.shape[1]
        frames = data
    else:
        raise ValueError(f"audio shape {data.shape}")
    if not np.isfinite(data).all():
        raise ValueError(f"non-finite audio for {path}")
    peak = float(np.max(np.abs(data))) if data.size else 0.0
    if peak >= 1.0:
        raise ValueError(f"refusing to write clipped audio {path} peak {peak}")
    data_bytes = _float_to_pcm24(frames)
    block_align = channels * 3
    fmt = struct.pack(
        "<HHIIHH",
        1,
        channels,
        sr,
        sr * block_align,
        block_align,
        BIT_DEPTH,
    )
    blob = b"RIFF" + struct.pack("<I", 36 + len(data_bytes)) + b"WAVE"
    blob += b"fmt " + struct.pack("<I", 16) + fmt
    blob += b"data" + struct.pack("<I", len(data_bytes)) + data_bytes
    with open(path, "wb") as handle:
        handle.write(blob)


def read_wav(path: str) -> tuple[np.ndarray, int, int, int]:
    """Return float audio in -1..1, sample rate, bit depth, channels."""
    with open(path, "rb") as handle:
        blob = handle.read()
    if blob[:4] != b"RIFF" or blob[8:12] != b"WAVE":
        raise ValueError(f"not a WAV file: {path}")
    pos = 12
    fmt = None
    data = None
    while pos + 8 <= len(blob):
        tag = blob[pos : pos + 4]
        size = struct.unpack_from("<I", blob, pos + 4)[0]
        payload = blob[pos + 8 : pos + 8 + size]
        pos += 8 + size + (size & 1)
        if tag == b"fmt ":
            fmt = payload
        elif tag == b"data":
            data = payload
    if fmt is None or data is None:
        raise ValueError(f"incomplete WAV: {path}")
    audio_format, channels, sr, _rate, block_align, bits = struct.unpack("<HHIIHH", fmt[:16])
    if audio_format != 1:
        raise ValueError(f"not PCM: {path}")
    if bits != 24 or block_align != channels * 3:
        raise ValueError(f"expected 24-bit PCM, got {bits}-bit {path}")
    audio = _pcm24_to_float(data)
    if channels > 1:
        audio = audio.reshape(-1, channels)
    return audio, sr, bits, channels


def _float_to_pcm24(frames: np.ndarray) -> bytes:
    """Interleaved little-endian 24-bit two's complement."""
    ints = np.rint(np.clip(frames, -1.0, 1.0) * 8_388_607.0).astype(np.int32).reshape(-1)
    unsigned = ints.astype(np.uint32)
    packed = np.stack(
        (
            (unsigned & 0xFF).astype(np.uint8),
            ((unsigned >> 8) & 0xFF).astype(np.uint8),
            ((unsigned >> 16) & 0xFF).astype(np.uint8),
        ),
        axis=1,
    )
    return packed.tobytes()


def _pcm24_to_float(data: bytes) -> np.ndarray:
    if len(data) % 3 != 0:
        raise ValueError("24-bit payload is not a whole number of samples")
    raw = np.frombuffer(data, dtype=np.uint8).reshape(-1, 3)
    values = (
        raw[:, 0].astype(np.int32)
        | (raw[:, 1].astype(np.int32) << 8)
        | (raw[:, 2].astype(np.int32) << 16)
    )
    values[raw[:, 2] >= 128] -= 0x1000000
    return values.astype(np.float64) / 8_388_607.0
