import numpy as np

_buffer     = None
_buffer_pos = 0
_delays = [
    (0.030, 0.6),
    (0.045, 0.4),
    (0.070, 0.25),
    (0.100, 0.15),
]
_dry = 1.0   # ← neu
_wet = 0.5   # ← neu (ersetzt _mix)


def set_dry(value: float):
    """Set the volume of the original signal in the reverb output."""
    global _dry
    _dry = max(0.0, min(1.0, value))

def set_wet(value: float):
    """Set the volume of the generated reflections in the reverb output."""
    global _wet
    _wet = max(0.0, min(1.0, value))

# Alias für Rückwärtskompatibilität
def set_mix(value: float):
    """Backward-compatible name for setting the wet reverb amount."""
    set_wet(value)


def set_preset(preset: str):
    """Choose a group of echo timings that approximates a room size."""
    global _delays, _buffer
    _buffer = None

    presets = {
        'small':  [(0.010, 0.5), (0.020, 0.3), (0.030, 0.15)],
        'medium': [(0.030, 0.6), (0.045, 0.4), (0.070, 0.25), (0.100, 0.15)],
        'large':  [(0.060, 0.7), (0.100, 0.5), (0.150, 0.35), (0.200, 0.2), (0.300, 0.1)],
        'cave':   [(0.100, 0.8), (0.200, 0.6), (0.350, 0.4), (0.500, 0.25), (0.700, 0.1)],
    }
    names = {'small': 'Kleiner Raum', 'medium': 'Mittlerer Raum',
             'large': 'Großer Raum', 'cave': 'Höhle'}

    if preset in presets:
        _delays = presets[preset]
        print(f"  Reverb Preset: {names[preset]}")


def apply_reverb(chunk: np.ndarray, samplerate: int) -> np.ndarray:
    """Generate simple reverb by summing several delayed, decayed copies."""
    global _buffer, _buffer_pos

    max_delay_samples = int(max(d[0] for d in _delays) * samplerate)

    if _buffer is None or len(_buffer) != max_delay_samples:
        _buffer = np.zeros(max_delay_samples, dtype='float32')

    wet = np.zeros_like(chunk)  # ← nur Echo, nicht chunk.copy()

    for delay_sec, decay in _delays:
        delay_samples = int(delay_sec * samplerate)
        echo = np.zeros_like(chunk)
        for i in range(len(chunk)):
            buf_idx  = (_buffer_pos + i - delay_samples) % max_delay_samples
            echo[i]  = _buffer[buf_idx] * decay
        wet += echo

    for i in range(len(chunk)):
        _buffer[(_buffer_pos + i) % max_delay_samples] = chunk[i]

    _buffer_pos = (_buffer_pos + len(chunk)) % max_delay_samples

    # Dry + Wet getrennt → kein Lautstärkeverlust beim Original
    output = chunk * _dry + wet * _wet

    return np.clip(output, -1.0, 1.0).astype('float32')


def reset():
    """Clear reverb memory so old reflections stop immediately."""
    global _buffer, _buffer_pos
    _buffer     = None
    _buffer_pos = 0
