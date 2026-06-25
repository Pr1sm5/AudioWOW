import numpy as np

_gain = 8.0
_mix = 0.7


def set_gain(value: float):
    global _gain
    _gain = max(1.0, min(40.0, value))


def set_mix(value: float):
    global _mix
    _mix = max(0.0, min(1.0, value))


def set_drive(gain: float):
    set_gain(gain)


def set_level(mix: float):
    set_mix(mix)


def apply_distortion(
    chunk: np.ndarray,
    samplerate: int,
    gain: float = None,
    mix: float = None,
) -> np.ndarray:
    gain = _gain if gain is None else gain
    mix = _mix if mix is None else mix
    dry = chunk
    driven = chunk * gain
    distorted = np.tanh(driven)
    output = dry * (1.0 - mix) + distorted * mix
    return np.clip(output, -1.0, 1.0).astype("float32")


def reset_distortion():
    pass
