import numpy as np

_highpass_last_input = None
_highpass_last_output = None
_cutoff_hz = 500.0


def set_cutoff(cutoff_hz: float):
    """Set the highpass cutoff frequency in Hz."""
    global _cutoff_hz
    _cutoff_hz = max(20.0, min(20000.0, cutoff_hz))


def apply_highpass(
    chunk: np.ndarray,
    samplerate: int,
    cutoff_hz: float = None
) -> np.ndarray:
    """
    Einfacher Highpass-Filter.
    Lässt hohe Frequenzen durch und dämpft tiefe Frequenzen.
    """
    global _highpass_last_input, _highpass_last_output

    cutoff_hz = _cutoff_hz if cutoff_hz is None else cutoff_hz
    dt = 1.0 / samplerate
    rc = 1.0 / (2.0 * np.pi * cutoff_hz)
    alpha = rc / (rc + dt)

    output = np.zeros_like(chunk)

    if _highpass_last_input is None:
        _highpass_last_input = chunk[0]
        _highpass_last_output = 0.0

    for i in range(len(chunk)):
        current_input = chunk[i]

        current_output = alpha * (
            _highpass_last_output + current_input - _highpass_last_input
        )

        output[i] = current_output

        _highpass_last_input = current_input
        _highpass_last_output = current_output

    return np.clip(output, -1.0, 1.0)


def reset_highpass():
    """Clear filter history so the next block starts fresh."""
    global _highpass_last_input, _highpass_last_output
    _highpass_last_input = None
    _highpass_last_output = None
