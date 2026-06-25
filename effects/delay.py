import numpy as np

# Zustand persistent halten
_delay_buffer = None
_delay_buffer_pos = 0

# Stärke des Delay-Effekts (0.0 - 1.0)
_delay_mix = 0.5
_feedback = 0.4  # ← global ergänzen


def set_feedback(value: float):
    global _feedback
    _feedback = max(0.0, min(0.9, value))

def set_delay_strength(strength: float):
    """
    Stärke des Delay-Effekts setzen.
    0.0 = kein Delay
    1.0 = maximales Delay
    """
    global _delay_mix
    _delay_mix = max(0.0, min(1.0, strength))


def apply_delay(
    chunk: np.ndarray,
    samplerate: int,
    delay_sec: float = 0.35,
    feedback: float = 0.4
) -> np.ndarray:
    """
    Einfacher Delay-Effekt.

    delay_sec: Verzögerung in Sekunden
    feedback: Wie stark das Echo wieder in den Buffer zurückgeführt wird
    Die Stärke des Effekts wird über set_delay_strength() eingestellt.
    """
    global _delay_buffer, _delay_buffer_pos

    delay_samples = int(delay_sec * samplerate)

    if delay_samples <= 0:
        return chunk

    # Buffer initialisieren
    if _delay_buffer is None or len(_delay_buffer) != delay_samples:
        _delay_buffer = np.zeros(delay_samples, dtype="float32")
        _delay_buffer_pos = 0

    output = np.zeros_like(chunk)

    for i in range(len(chunk)):
        dry = chunk[i]
        delayed = _delay_buffer[_delay_buffer_pos]

        # Dry/Wet-Mix
        output[i] = dry * (1.0 - _delay_mix) + delayed * _delay_mix

        # Feedback in Buffer schreiben
        _delay_buffer[_delay_buffer_pos] = dry + delayed * feedback

        _delay_buffer_pos = (_delay_buffer_pos + 1) % delay_samples

    # Clipping verhindern
    output = np.clip(output, -1.0, 1.0)

    return output


def reset_delay():
    """Buffer zurücksetzen."""
    global _delay_buffer, _delay_buffer_pos
    _delay_buffer = None
    _delay_buffer_pos = 0