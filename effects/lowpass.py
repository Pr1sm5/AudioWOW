import numpy as np

_lowpass_last = None


def apply_lowpass(
    chunk: np.ndarray,
    samplerate: int,
    cutoff_hz: float = 1000.0
) -> np.ndarray:
    """
    Einfacher Lowpass-Filter.
    Lässt tiefe Frequenzen durch und dämpft hohe Frequenzen.
    """
    global _lowpass_last

    dt = 1.0 / samplerate
    rc = 1.0 / (2.0 * np.pi * cutoff_hz)
    alpha = dt / (rc + dt)

    output = np.zeros_like(chunk)

    if _lowpass_last is None:
        _lowpass_last = chunk[0]

    for i in range(len(chunk)):
        _lowpass_last = _lowpass_last + alpha * (chunk[i] - _lowpass_last)
        output[i] = _lowpass_last

    return np.clip(output, -1.0, 1.0)


def reset_lowpass():
    global _lowpass_last
    _lowpass_last = None