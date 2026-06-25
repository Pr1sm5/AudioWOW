import numpy as np

_delay_buffer = None
_delay_buffer_pos = 0
_delay_mix = 0.5
_delay_sec = 0.35
_feedback = 0.4


def set_delay_strength(strength: float):
    global _delay_mix
    _delay_mix = max(0.0, min(1.0, strength))


def set_delay(delay_sec: float):
    global _delay_sec, _delay_buffer, _delay_buffer_pos
    _delay_sec = max(0.01, min(2.0, delay_sec))
    _delay_buffer = None
    _delay_buffer_pos = 0


def set_feedback(feedback: float):
    global _feedback
    _feedback = max(0.0, min(0.9, feedback))


def apply_delay(
    chunk: np.ndarray,
    samplerate: int,
    delay_sec: float = None,
    feedback: float = None,
) -> np.ndarray:
    delay_sec = _delay_sec if delay_sec is None else delay_sec
    feedback = _feedback if feedback is None else feedback
    delay_samples = int(delay_sec * samplerate)

    if delay_samples <= 0:
        return chunk

    global _delay_buffer, _delay_buffer_pos
    if _delay_buffer is None or len(_delay_buffer) != delay_samples:
        _delay_buffer = np.zeros(delay_samples, dtype="float32")
        _delay_buffer_pos = 0

    output = np.zeros_like(chunk)
    for i in range(len(chunk)):
        dry = chunk[i]
        delayed = _delay_buffer[_delay_buffer_pos]
        output[i] = dry * (1.0 - _delay_mix) + delayed * _delay_mix
        _delay_buffer[_delay_buffer_pos] = dry + delayed * feedback
        _delay_buffer_pos = (_delay_buffer_pos + 1) % delay_samples

    return np.clip(output, -1.0, 1.0).astype("float32")


def reset_delay():
    global _delay_buffer, _delay_buffer_pos
    _delay_buffer = None
    _delay_buffer_pos = 0
