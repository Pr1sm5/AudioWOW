import numpy as np

_buffer = None
_buffer_pos = 0

# Einstellbare Parameter
_delays = [
    (0.030, 0.6),
    (0.045, 0.4),
    (0.070, 0.25),
    (0.100, 0.15),
]
_mix = 0.5  # Dry/Wet


def set_mix(value: float):
    """Dry/Wet Mix: 0.0 = nur Original, 1.0 = nur Reverb."""
    global _mix
    _mix = max(0.0, min(1.0, value))


def set_preset(preset: str):
    """Vordefinierte Raumgrößen."""
    global _delays, _buffer
    _buffer = None  # Buffer zurücksetzen bei Preset-Wechsel

    if preset == 'small':
        _delays = [
            (0.010, 0.5),
            (0.020, 0.3),
            (0.030, 0.15),
        ]
        print("  Reverb Preset: Kleiner Raum")

    elif preset == 'medium':
        _delays = [
            (0.030, 0.6),
            (0.045, 0.4),
            (0.070, 0.25),
            (0.100, 0.15),
        ]
        print("  Reverb Preset: Mittlerer Raum (Standard)")

    elif preset == 'large':
        _delays = [
            (0.060, 0.7),
            (0.100, 0.5),
            (0.150, 0.35),
            (0.200, 0.2),
            (0.300, 0.1),
        ]
        print("  Reverb Preset: Großer Raum / Hall")

    elif preset == 'cave':
        _delays = [
            (0.100, 0.8),
            (0.200, 0.6),
            (0.350, 0.4),
            (0.500, 0.25),
            (0.700, 0.1),
        ]
        print("  Reverb Preset: Höhle")


def apply_reverb(chunk: np.ndarray, samplerate: int) -> np.ndarray:
    global _buffer, _buffer_pos

    max_delay_samples = int(max(d[0] for d in _delays) * samplerate)

    if _buffer is None or len(_buffer) != max_delay_samples:
        _buffer = np.zeros(max_delay_samples, dtype='float32')

    wet = chunk.copy()

    for delay_sec, decay in _delays:
        delay_samples = int(delay_sec * samplerate)
        echo = np.zeros_like(chunk)

        for i in range(len(chunk)):
            buf_idx = (_buffer_pos + i - delay_samples) % max_delay_samples
            echo[i] = _buffer[buf_idx] * decay

        wet += echo

    for i in range(len(chunk)):
        _buffer[(_buffer_pos + i) % max_delay_samples] = chunk[i]

    _buffer_pos = (_buffer_pos + len(chunk)) % max_delay_samples

    # Dry/Wet mischen
    output = chunk * (1.0 - _mix) + wet * _mix

    return np.clip(output, -1.0, 1.0)


def reset():
    global _buffer, _buffer_pos
    _buffer = None
    _buffer_pos = 0