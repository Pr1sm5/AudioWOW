import numpy as np

_delay_buffer = None
_delay_buffer_pos = 0
_delay_sec = 0.35
_feedback  = 0.4
_dry       = 1.0   # ← neu
_wet       = 0.5   # ← neu (ersetzt _delay_mix)


def set_delay(delay_sec: float):
    """Set delay time in seconds and rebuild the delay buffer on the next block."""
    global _delay_sec, _delay_buffer, _delay_buffer_pos
    _delay_sec = max(0.01, min(2.0, delay_sec))
    _delay_buffer = None
    _delay_buffer_pos = 0

def set_feedback(feedback: float):
    """Set how much delayed signal is fed back into the delay line."""
    global _feedback
    _feedback = max(0.0, min(0.9, feedback))

def set_dry(value: float):
    """Set the volume of the original signal in the delay output."""
    global _dry
    _dry = max(0.0, min(1.0, value))

def set_wet(value: float):
    """Set the volume of the delayed signal in the delay output."""
    global _wet
    _wet = max(0.0, min(1.0, value))

# Alias für Rückwärtskompatibilität
def set_delay_strength(strength: float):
    """Backward-compatible name for setting the wet delay amount."""
    set_wet(strength)


def apply_delay(chunk: np.ndarray, samplerate: int) -> np.ndarray:
    """Process one audio block through a stateful feedback delay."""
    global _delay_buffer, _delay_buffer_pos

    delay_samples = int(_delay_sec * samplerate)
    if delay_samples <= 0:
        return chunk

    if _delay_buffer is None or len(_delay_buffer) != delay_samples:
        _delay_buffer = np.zeros(delay_samples, dtype="float32")
        _delay_buffer_pos = 0

    output = np.zeros_like(chunk)
    for i in range(len(chunk)):
        dry     = chunk[i]
        delayed = _delay_buffer[_delay_buffer_pos]

        # Dry bleibt voll, Wet wird addiert → kein Lautstärkeverlust
        output[i] = dry * _dry + delayed * _wet

        # Feedback zurück in Buffer
        _delay_buffer[_delay_buffer_pos] = dry + delayed * _feedback
        _delay_buffer_pos = (_delay_buffer_pos + 1) % delay_samples

    return np.clip(output, -1.0, 1.0).astype("float32")


def reset_delay():
    """Clear delay memory so old echoes stop immediately."""
    global _delay_buffer, _delay_buffer_pos
    _delay_buffer = None
    _delay_buffer_pos = 0
