import numpy as np

_gain = 8.0   # ← neu
_mix  = 0.7   # ← neu


def set_gain(value: float):
    global _gain
    _gain = max(1.0, min(40.0, value))


def set_mix(value: float):
    global _mix
    _mix = max(0.0, min(1.0, value))


def apply_distortion(chunk: np.ndarray, samplerate: int) -> np.ndarray:
    dry      = chunk
    driven   = chunk * _gain          # ← global statt Parameter
    distorted = np.tanh(driven)
    output   = dry * (1.0 - _mix) + distorted * _mix  # ← global
    return np.clip(output, -1.0, 1.0).astype('float32')


def reset_distortion():
    pass