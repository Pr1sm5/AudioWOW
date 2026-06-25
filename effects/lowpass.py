import numpy as np

_lowpass_last = None
_cutoff_hz = 1000.0


def set_cutoff(cutoff_hz: float):
    global _cutoff_hz
    _cutoff_hz = max(20.0, min(20000.0, cutoff_hz))


def apply_lowpass(
    chunk: np.ndarray,
    samplerate: int,
    cutoff_hz: float = None,
) -> np.ndarray:
    global _lowpass_last

    cutoff_hz = _cutoff_hz if cutoff_hz is None else cutoff_hz
    dt = 1.0 / samplerate
    rc = 1.0 / (2.0 * np.pi * cutoff_hz)
    alpha = dt / (rc + dt)

    output = np.zeros_like(chunk)
    if _lowpass_last is None:
        _lowpass_last = chunk[0]

    for i in range(len(chunk)):
        _lowpass_last = _lowpass_last + alpha * (chunk[i] - _lowpass_last)
        output[i] = _lowpass_last

    return np.clip(output, -1.0, 1.0).astype("float32")


def reset_lowpass():
    global _lowpass_last
    _lowpass_last = None
