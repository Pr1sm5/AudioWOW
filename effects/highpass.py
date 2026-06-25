import numpy as np

_highpass_last_input = None
_highpass_last_output = None


def apply_highpass(
    chunk: np.ndarray,
    samplerate: int,
    cutoff_hz: float = 500.0
) -> np.ndarray:
    """
    Einfacher Highpass-Filter.
    Lässt hohe Frequenzen durch und dämpft tiefe Frequenzen.
    """
    global _highpass_last_input, _highpass_last_output

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
    global _highpass_last_input, _highpass_last_output
    _highpass_last_input = None
    _highpass_last_output = None