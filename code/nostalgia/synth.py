"""Original synthesis. No sampled breaks and no external audio services.

Signal flow for each drum hit:
oscillator or noise -> amplitude envelope -> optional baked room taps ->
optional per-hit waveshaper -> place on the timeline.

Pitched voices:
oscillator (saw, square, or FM) -> optional glide -> resonant lowpass with a
per-note cutoff envelope -> short release -> optional output waveshaper ->
optional one-pole highpass at 25 Hz.

Filter coefficients update every CONTROL_BLOCK samples (64 samples, 1.333 ms
at 48 kHz). Oscillator phase is sample accurate. Algorithmic latency is 0.
Filter phase delay is not compensated, so MIDI note-ons align to oscillator
onset, not to group delay.

Per-hit waveshaping is not a full-mix drum bus. Hits sum linearly after it,
which keeps loop tiling and stem sums stable. There is no master limiter.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import lfilter

from .constants import CONTROL_BLOCK, SR, midi_to_hz

ROOM_TAPS = ((0.011, 0.10, 1), (0.017, 0.07, 0))


def waveshape(audio: np.ndarray, drive: float) -> np.ndarray:
    if drive <= 1.001:
        return audio
    return np.tanh(audio * drive) / np.tanh(drive)


def _rbj_lowpass(cutoff: float, q: float, sr: int) -> tuple[np.ndarray, np.ndarray]:
    cutoff = float(np.clip(cutoff, 30.0, sr * 0.45))
    q = float(np.clip(q, 0.5, 8.0))
    w0 = 2.0 * np.pi * cutoff / sr
    alpha = np.sin(w0) / (2.0 * q)
    cosw = np.cos(w0)
    b0 = (1.0 - cosw) * 0.5
    b1 = 1.0 - cosw
    b2 = b0
    a0 = 1.0 + alpha
    a1 = -2.0 * cosw
    a2 = 1.0 - alpha
    return np.array([b0 / a0, b1 / a0, b2 / a0]), np.array([1.0, a1 / a0, a2 / a0])


def _highpass_ba(cutoff: float, sr: int) -> tuple[np.ndarray, np.ndarray]:
    radius = float(np.exp(-2.0 * np.pi * cutoff / sr))
    gain = (1.0 + radius) * 0.5
    return np.array([gain, -gain]), np.array([1.0, -radius])


def _env_filter(audio: np.ndarray, sr: int, cutoff_start: float, cutoff_end: float, q: float, decay_s: float) -> np.ndarray:
    output = np.empty_like(audio)
    state = np.zeros(2, dtype=np.float64)
    decay_s = max(decay_s, 1e-4)
    for index in range(0, len(audio), CONTROL_BLOCK):
        t = index / sr
        coef = np.exp(-t / decay_s)
        cutoff = cutoff_end + (cutoff_start - cutoff_end) * coef
        numerator, denominator = _rbj_lowpass(cutoff, q, sr)
        block = audio[index : index + CONTROL_BLOCK]
        filtered, state = lfilter(numerator, denominator, block, zi=state)
        output[index : index + len(block)] = filtered
    return output


def _saw(phase: np.ndarray, freq: np.ndarray, sr: int) -> np.ndarray:
    t = np.mod(phase, 1.0)
    dt = np.clip(freq / sr, 1e-6, 0.45)
    saw = 2.0 * t - 1.0
    early = t < dt
    tt = np.zeros_like(t)
    tt[early] = t[early] / dt[early]
    saw[early] -= tt[early] + tt[early] - tt[early] * tt[early] - 1.0
    late = t > (1.0 - dt)
    tt2 = np.zeros_like(t)
    tt2[late] = (t[late] - 1.0) / dt[late]
    saw[late] -= tt2[late] * tt2[late] + tt2[late] + tt2[late] + 1.0
    return saw


def _square(phase: np.ndarray, freq: np.ndarray, sr: int) -> np.ndarray:
    t = np.mod(phase, 1.0)
    dt = np.clip(freq / sr, 1e-6, 0.45)
    square = np.where(t < 0.5, 1.0, -1.0).astype(np.float64)

    def blep(mask: np.ndarray, distance: np.ndarray) -> None:
        tt = np.zeros_like(distance)
        tt[mask] = distance[mask]
        square[mask] += tt[mask] + tt[mask] - tt[mask] * tt[mask] - 1.0

    # This is a compact band-limiting correction, not a model of a hardware oscillator.
    rising = t < dt
    blep(rising, t / dt)
    dist = t - 0.5
    falling_early = (t >= 0.5) & (t < 0.5 + dt)
    tt = np.zeros_like(t)
    tt[falling_early] = (t[falling_early] - 0.5) / dt[falling_early]
    square[falling_early] -= tt[falling_early] + tt[falling_early] - tt[falling_early] * tt[falling_early] - 1.0
    return square


def _place(buffer: np.ndarray, hit: np.ndarray, pos: int, pan: float = 0.0) -> int:
    """Mix a mono hit. Returns samples that fell past the buffer."""
    if pos >= len(buffer):
        return len(hit)
    room = len(buffer) - pos
    use = min(room, len(hit))
    chunk = hit[:use]
    if buffer.ndim == 1:
        buffer[pos : pos + use] += chunk
    else:
        left = np.cos((pan + 1.0) * np.pi * 0.25)
        right = np.sin((pan + 1.0) * np.pi * 0.25)
        # Center pan is equal power, then scaled so a centered hit keeps its peak.
        scale = np.sqrt(2.0)
        buffer[pos : pos + use, 0] += chunk * left * scale * 0.5 * np.sqrt(2.0)
        buffer[pos : pos + use, 1] += chunk * right * scale * 0.5 * np.sqrt(2.0)
        # The product left*scale*0.5*sqrt(2) at pan 0:
        # left = cos(pi/4) = 0.707, scale = 1.414, 0.5 * 1.414 = 0.707
        # 0.707 * 1.414 * 0.707 = 0.707. That is too low.
    return len(hit) - use


def pan_gains(pan: float) -> tuple[float, float]:
    """Equal-power pan normalized so center is (1, 1) / sqrt(2) * sqrt(2) = 1 on each side? 

    Center should contribute the full mono amplitude to both channels so a mono
    compatibility sum would double. Stems are summed as stereo. A centered source
    is stored at amplitude A on both channels, matching a dual-mono upmix.
    """
    angle = (pan + 1.0) * np.pi * 0.25
    left = np.cos(angle)
    right = np.sin(angle)
    # At pan 0, left = right = 0.707. Multiply by sqrt(2) so center is 1.0 per side.
    norm = np.sqrt(2.0)
    return float(left * norm), float(right * norm)


def mix_hit(buffer: np.ndarray, hit: np.ndarray, pos: int, pan: float = 0.0) -> int:
    if pos >= (buffer.shape[0] if buffer.ndim == 2 else len(buffer)):
        return int(len(hit))
    length = buffer.shape[0]
    use = min(length - pos, len(hit))
    if use <= 0:
        return int(len(hit))
    chunk = hit[:use]
    if buffer.ndim == 1:
        buffer[pos : pos + use] += chunk
    else:
        left, right = pan_gains(pan)
        buffer[pos : pos + use, 0] += chunk * left
        buffer[pos : pos + use, 1] += chunk * right
    return int(len(hit) - use)


def _noise(rng: np.random.Generator, n: int) -> np.ndarray:
    data = rng.standard_normal(n).astype(np.float64)
    data -= np.mean(data)
    return data


def bake_room(hit: np.ndarray, sr: int) -> np.ndarray:
    padded = np.zeros(len(hit) + int(0.03 * sr), dtype=np.float64)
    padded[: len(hit)] = hit
    output = padded.copy()
    for delay_s, gain, _side in ROOM_TAPS:
        delay = int(sr * delay_s)
        output[delay:] += gain * padded[:-delay]
    return output


def fade_end(audio: np.ndarray, samples: int = 64) -> np.ndarray:
    if len(audio) < samples:
        return audio
    ramp = np.linspace(1.0, 0.0, samples)
    if audio.ndim == 1:
        audio[-samples:] *= ramp
    else:
        audio[-samples:, :] *= ramp[:, None]
    return audio


class DrumKit:
    def __init__(self, preset: dict, seed: int):
        self.preset = preset
        self.rng = np.random.default_rng(seed)
        self.cache: dict[tuple, np.ndarray] = {}
        self._dry_scaled: dict[int, np.ndarray] = {}

    def hit(self, pitch: int, processed: bool) -> np.ndarray:
        """Return a hit. Dry and processed share one excitation.

        The dry hit is peak-normalized to the preset target. Processed audio is
        that same buffer through room taps and the waveshaper, without a second
        normalization. Bypass of the processed chain is exactly the dry buffer.
        """
        key = (pitch, processed)
        if key not in self.cache:
            if pitch not in self._dry_scaled:
                dry = self._synthesize(pitch)
                peak = float(np.max(np.abs(dry))) + 1e-12
                self._dry_scaled[pitch] = dry * (self._target(pitch) / peak)
            dry_scaled = self._dry_scaled[pitch]
            if processed:
                audio = waveshape(bake_room(dry_scaled, SR), float(self.preset.get("drive", 1.0)))
            else:
                audio = dry_scaled
            self.cache[key] = np.asarray(audio, dtype=np.float64)
        return self.cache[key]

    def _target(self, pitch: int) -> float:
        targets = self.preset.get("targets", {})
        return float(targets.get(pitch, targets.get("default", 0.4)))

    def _synthesize(self, pitch: int) -> np.ndarray:
        if pitch == 36:
            return self._kick()
        if pitch in (38, 40):
            return self._snare()
        if pitch == 37:
            return self._rim()
        if pitch == 39:
            return self._clap()
        if pitch == 42:
            return self._hat(self.preset["hat"]["decay"])
        if pitch == 46:
            return self._hat(self.preset["open"]["decay"], open_hat=True)
        if pitch in (41, 43, 45, 47, 48, 50):
            return self._tom(pitch)
        if pitch == 49:
            return self._crash()
        if pitch == 51:
            return self._ride()
        if pitch == 53:
            return self._bell()
        if pitch == 54:
            return self._tamb()
        if pitch == 56:
            return self._cowbell()
        if pitch in (62, 63, 64):
            return self._conga(pitch)
        if pitch in (70, 82):
            return self._shaker()
        raise KeyError(f"no synth for percussion pitch {pitch}")

    def _kick(self) -> np.ndarray:
        p = self.preset["kick"]
        n = int(SR * p["decay"])
        t = np.arange(n) / SR
        freq = p["f1"] + (p["f0"] - p["f1"]) * np.exp(-t * p["pitch_drop"])
        phase = 2.0 * np.pi * np.cumsum(freq) / SR
        body = np.sin(phase) * np.exp(-t / p["amp_decay"])
        click = _noise(self.rng, n)
        click_n = int(SR * 0.003)
        window = np.zeros(n)
        window[:click_n] = np.linspace(1.0, 0.0, click_n) ** 2
        return body + click * window * p["click"]

    def _snare(self) -> np.ndarray:
        p = self.preset["snare"]
        n = int(SR * p["decay"])
        t = np.arange(n) / SR
        body = np.sin(2 * np.pi * p["body"] * t) * np.exp(-t / 0.12)
        body += 0.6 * np.sin(2 * np.pi * p["body2"] * t) * np.exp(-t / 0.08)
        noise = _noise(self.rng, n)
        numerator, denominator = _highpass_ba(1800.0, SR)
        noise = lfilter(numerator, denominator, noise)
        noise *= np.exp(-t / p["noise_decay"])
        return body * p["tone"] + noise * p["noise"]

    def _hat(self, decay: float, open_hat: bool = False) -> np.ndarray:
        p = self.preset["open" if open_hat else "hat"]
        n = int(SR * max(decay, 0.02) * (1.6 if open_hat else 1.2))
        t = np.arange(n) / SR
        noise = _noise(self.rng, n)
        numerator, denominator = _highpass_ba(p.get("color", 7000.0), SR)
        noise = lfilter(numerator, denominator, noise)
        metal = (
            np.sin(2 * np.pi * 3200 * t)
            + 0.6 * np.sin(2 * np.pi * 5400 * t)
            + 0.3 * np.sin(2 * np.pi * 7600 * t)
        )
        env = np.exp(-t / decay)
        return (noise + metal * p.get("metallic", 0.25)) * env

    def _tom(self, pitch: int) -> np.ndarray:
        base = {41: 80, 43: 98, 45: 120, 47: 150, 48: 180, 50: 210}[pitch]
        n = int(SR * 0.35)
        t = np.arange(n) / SR
        freq = base * 0.65 + (base - base * 0.65) * np.exp(-t * 18)
        phase = 2 * np.pi * np.cumsum(freq) / SR
        body = np.sin(phase) * np.exp(-t / 0.12)
        noise = _noise(self.rng, n) * np.exp(-t / 0.02) * 0.15
        return body + noise

    def _crash(self) -> np.ndarray:
        n = int(SR * 0.7)
        t = np.arange(n) / SR
        noise = _noise(self.rng, n)
        numerator, denominator = _highpass_ba(5000.0, SR)
        noise = lfilter(numerator, denominator, noise)
        partials = sum(np.sin(2 * np.pi * f * t) * a for f, a in ((420, 0.2), (1280, 0.15), (2100, 0.1)))
        return (noise * 0.7 + partials) * np.exp(-t / 0.28)

    def _ride(self) -> np.ndarray:
        n = int(SR * 0.45)
        t = np.arange(n) / SR
        noise = _noise(self.rng, n)
        numerator, denominator = _highpass_ba(4000.0, SR)
        noise = lfilter(numerator, denominator, noise)
        ping = np.sin(2 * np.pi * 3100 * t) * np.exp(-t / 0.05)
        return (noise * 0.5 + ping) * np.exp(-t / 0.16)

    def _bell(self) -> np.ndarray:
        n = int(SR * 0.28)
        t = np.arange(n) / SR
        tone = np.sin(2 * np.pi * 1180 * t) + 0.5 * np.sin(2 * np.pi * 1740 * t)
        return tone * np.exp(-t / 0.07)

    def _rim(self) -> np.ndarray:
        n = int(SR * 0.05)
        t = np.arange(n) / SR
        noise = _noise(self.rng, n)
        return (np.sin(2 * np.pi * 1850 * t) + noise * 0.4) * np.exp(-t / 0.008)

    def _clap(self) -> np.ndarray:
        n = int(SR * 0.25)
        out = np.zeros(n)
        for offset in (0, int(0.010 * SR), int(0.020 * SR)):
            burst = _noise(self.rng, int(0.04 * SR))
            burst *= np.exp(-np.arange(len(burst)) / SR / 0.012)
            end = min(n, offset + len(burst))
            out[offset:end] += burst[: end - offset]
        numerator, denominator = _highpass_ba(1200.0, SR)
        out = lfilter(numerator, denominator, out)
        t = np.arange(n) / SR
        return out * np.exp(-t / 0.08)

    def _tamb(self) -> np.ndarray:
        n = int(SR * 0.18)
        t = np.arange(n) / SR
        noise = _noise(self.rng, n)
        numerator, denominator = _highpass_ba(6000.0, SR)
        noise = lfilter(numerator, denominator, noise)
        jangle = np.sin(2 * np.pi * 6400 * t) * 0.3
        return (noise + jangle) * np.exp(-t / 0.045)

    def _cowbell(self) -> np.ndarray:
        p = self.preset.get("cowbell", {"freq": 587.0})
        n = int(SR * 0.2)
        t = np.arange(n) / SR
        tone = np.sign(np.sin(2 * np.pi * p["freq"] * t))
        tone += 0.6 * np.sign(np.sin(2 * np.pi * p["freq"] * 1.5 * t))
        return (tone * 0.3) * np.exp(-t / 0.05)

    def _conga(self, pitch: int) -> np.ndarray:
        base = {64: 142, 62: 196, 63: 210}[pitch]
        n = int(SR * 0.22)
        t = np.arange(n) / SR
        freq = base * (1.4 * np.exp(-t * 30) + 1.0)
        body = np.sin(2 * np.pi * np.cumsum(freq) / SR)
        decay = 0.09 if pitch != 63 else 0.14
        return body * np.exp(-t / decay)

    def _shaker(self) -> np.ndarray:
        n = int(SR * 0.045)
        noise = _noise(self.rng, n)
        numerator, denominator = _highpass_ba(5000.0, SR)
        noise = lfilter(numerator, denominator, noise)
        return noise * np.exp(-np.arange(n) / SR / 0.012)


def synthesize_note(
    wave: str,
    freq_hz: float,
    prev_hz: float | None,
    glide: bool,
    samples: int,
    gate_samples: int,
    sr: int,
    cutoff: float,
    cutoff_end: float,
    q: float,
    decay_s: float,
    drive: float,
) -> np.ndarray:
    if samples <= 0:
        return np.zeros(0)
    freq = np.full(samples, freq_hz, dtype=np.float64)
    if glide and prev_hz is not None:
        glide_n = min(samples, int(0.08 * sr))
        freq[:glide_n] = np.linspace(prev_hz, freq_hz, glide_n)
    phase = np.cumsum(freq) / sr
    if wave == "square":
        osc = _square(phase, freq, sr)
    elif wave == "fm":
        ratio = 2.0
        index = 2.4 * np.exp(-np.arange(samples) / sr / max(decay_s, 0.05))
        mod = np.sin(2 * np.pi * np.cumsum(freq * ratio) / sr) * index
        osc = np.sin(2 * np.pi * phase + mod)
    elif wave == "tone":
        osc = np.sin(2 * np.pi * phase)
    else:
        osc = _saw(phase, freq, sr)
    filtered = _env_filter(osc, sr, cutoff, cutoff_end, q, decay_s)
    amp = np.ones(samples)
    attack = min(int(0.004 * sr), max(1, samples // 8))
    amp[:attack] = np.linspace(0.0, 1.0, attack)
    release = max(1, samples - gate_samples)
    if release < samples:
        amp[-release:] *= np.linspace(1.0, 0.0, release)
    filtered *= amp
    numerator, denominator = _highpass_ba(25.0, sr)
    filtered = lfilter(numerator, denominator, filtered)
    return waveshape(filtered, drive)


def render_monophonic(
    events,
    total: int,
    mpqn: int,
    preset: dict,
    ticks_to_samples,
) -> np.ndarray:
    buffer = np.zeros(total, dtype=np.float64)
    ordered = sorted(events, key=lambda item: item.performed_start_tick)
    prev = None
    for index, event in enumerate(ordered):
        start = ticks_to_samples(event.performed_start_tick, mpqn)
        gate_end = ticks_to_samples(event.end_tick, mpqn)
        next_start = total
        if index + 1 < len(ordered):
            next_start = ticks_to_samples(ordered[index + 1].performed_start_tick, mpqn)
        release = int(preset.get("release_s", 0.02) * SR)
        release = min(release, max(0, next_start - gate_end))
        end = min(total, gate_end + release)
        if end <= start or start >= total:
            prev = midi_to_hz(event.pitch)
            continue
        cutoff = preset["cutoff"] * (1.65 if event.accent else 1.0)
        cutoff = min(cutoff, preset.get("cutoff_max", 5000.0))
        note = synthesize_note(
            preset.get("wave", "saw"),
            midi_to_hz(event.pitch),
            prev,
            event.glide,
            end - start,
            max(1, gate_end - start),
            SR,
            cutoff,
            preset["cutoff_end"],
            preset["q"] if not event.accent else min(8.0, preset["q"] + 0.6),
            preset.get("decay_s", 0.12) * (0.65 if event.accent else 1.0),
            preset.get("drive", 1.0),
        )
        buffer[start:end] += note * preset.get("gain", 0.4)
        prev = midi_to_hz(event.pitch)
    return buffer


def render_polyphonic(
    events,
    total: int,
    mpqn: int,
    preset: dict,
    ticks_to_samples,
    stereo: bool,
) -> np.ndarray:
    buffer = np.zeros((total, 2) if stereo else total, dtype=np.float64)
    groups: dict[int, list] = {}
    for event in events:
        groups.setdefault(event.performed_start_tick, []).append(event)
    for start_tick, chord in groups.items():
        chord = sorted(chord, key=lambda item: item.pitch)
        for index, event in enumerate(chord):
            start = ticks_to_samples(event.performed_start_tick, mpqn)
            gate_end = ticks_to_samples(event.end_tick, mpqn)
            release = int(preset.get("release_s", 0.18) * SR)
            end = min(total, max(gate_end, start + 1) + release)
            if start >= total or end <= start:
                continue
            attack_s = preset.get("attack_s", 0.003)
            note = synthesize_note(
                preset.get("wave", "saw"),
                midi_to_hz(event.pitch),
                None,
                False,
                end - start,
                max(1, min(end, gate_end) - start),
                SR,
                preset["cutoff"],
                preset["cutoff_end"],
                preset["q"],
                preset.get("decay_s", 0.2),
                preset.get("drive", 1.0),
            )
            # Slow attack override for atmosphere: rescaled into the existing amplitude.
            if attack_s > 0.02:
                attack = min(len(note), int(attack_s * SR))
                # synthesize_note already applied a 4 ms attack. Replace the front.
                note[:attack] *= np.linspace(0.0, 1.0, attack)
            gain = preset.get("gain", 0.2)
            if stereo:
                span = preset.get("pan_span", 0.35)
                if len(chord) == 1:
                    pan = 0.0
                else:
                    pan = -span + (2 * span) * (index / (len(chord) - 1))
                left, right = pan_gains(pan)
                # Detune is internal to the voice, not an extra MIDI note.
                detune = note * (0.92 + 0.08 * np.sin(np.linspace(0, 8, len(note))))
                use = min(len(note), buffer.shape[0] - start)
                buffer[start : start + use, 0] += detune[:use] * gain * left
                buffer[start : start + use, 1] += note[:use] * gain * right
            else:
                use = min(len(note), len(buffer) - start)
                buffer[start : start + use] += note[:use] * gain
    return buffer


def low_noise_bed(total: int, sr: int, seed: int, stereo: bool) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = total
    noise = _noise(rng, n)
    numerator, denominator = _rbj_lowpass(500.0, 0.7, sr)
    noise = lfilter(numerator, denominator, noise)
    high_b, high_a = _highpass_ba(80.0, sr)
    noise = lfilter(high_b, high_a, noise)
    # Slow level motion, not a musical note.
    lfo = 0.65 + 0.35 * np.sin(2 * np.pi * np.arange(n) / sr / 8.0)
    noise *= lfo * 0.15
    if stereo:
        noise_r = np.roll(noise, int(0.013 * sr))
        return np.stack([noise, noise_r], axis=1)
    return noise


def fx_build(bars_samples: int, sr: int, seed: int, cutoff_end: float, drive: float) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = bars_samples
    noise = _noise(rng, n)
    t = np.linspace(0.0, 1.0, n)
    cutoff = 180.0 * (cutoff_end / 180.0) ** t
    output = np.empty(n)
    state = np.zeros(2)
    for index in range(0, n, CONTROL_BLOCK):
        numerator, denominator = _rbj_lowpass(float(cutoff[index]), 2.5, sr)
        block = noise[index : index + CONTROL_BLOCK]
        filtered, state = lfilter(numerator, denominator, block, zi=state)
        output[index : index + len(block)] = filtered
    amp = t ** 1.4
    mono = waveshape(output * amp, drive)
    peak = np.max(np.abs(mono)) + 1e-12
    mono *= 0.42 / peak
    delayed = np.zeros_like(mono)
    shift = int(0.007 * sr)
    delayed[shift:] = mono[:-shift]
    return np.stack([mono, delayed * 0.85], axis=1)


def fx_release(bars_samples: int, sr: int, start_hz: float, drive: float, seed: int) -> np.ndarray:
    n = bars_samples
    t = np.arange(n) / sr
    duration = n / sr
    freq = start_hz * (40.0 / start_hz) ** (t / max(duration, 1e-3))
    phase = 2 * np.pi * np.cumsum(freq) / sr
    tone = np.sin(phase)
    noise = np.random.default_rng(seed).standard_normal(n) * np.linspace(0.25, 0.0, n)
    amp = np.linspace(1.0, 0.0, n) ** 0.7
    mono = waveshape((tone * 0.7 + noise * 0.2) * amp, drive)
    peak = np.max(np.abs(mono)) + 1e-12
    mono *= 0.4 / peak
    return np.stack([mono, mono * 0.9], axis=1)


def fx_accent(sr: int, freq_hz: float, drive: float, seed: int) -> tuple[np.ndarray, int]:
    """Return stereo audio and the active length in samples before the container tail."""
    rng = np.random.default_rng(seed)
    n = int(0.45 * sr)
    t = np.arange(n) / sr
    freq = freq_hz * np.exp(-t * 8.0) 
    # Do not let the sweep fall into uncontrolled subsonic energy.
    freq = np.maximum(freq, 38.0)
    phase = 2 * np.pi * np.cumsum(freq) / sr
    body = np.sin(phase) * np.exp(-t / 0.12)
    noise = rng.standard_normal(n) * np.exp(-t / 0.015)
    mono = waveshape(body * 0.8 + noise * 0.5, drive)
    peak = np.max(np.abs(mono)) + 1e-12
    mono *= 0.62 / peak
    stereo = np.stack([mono, mono * 0.92], axis=1)
    return stereo, int(0.18 * sr)


def duck_bass(audio: np.ndarray, kick_samples: list[int], sr: int, depth: float) -> np.ndarray:
    """Arrangement-only gain envelope. Depth is the remaining gain at the kick (0.5 = -6 dB)."""
    if audio.ndim != 1 or depth >= 0.999:
        return audio
    envelope = np.ones(len(audio), dtype=np.float64)
    attack = int(0.003 * sr)
    release = int(0.055 * sr)
    for pos in kick_samples:
        if pos < 0 or pos >= len(audio):
            continue
        end_a = min(len(audio), pos + attack)
        envelope[pos:end_a] = np.minimum(envelope[pos:end_a], np.linspace(1.0, depth, end_a - pos))
        start_r = end_a
        end_r = min(len(audio), start_r + release)
        if end_r > start_r:
            envelope[start_r:end_r] = np.minimum(
                envelope[start_r:end_r], np.linspace(depth, 1.0, end_r - start_r)
            )
    return audio * envelope
