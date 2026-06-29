import numpy as np

_gain = 8.0
_mix = 0.7


def set_gain(value: float):
    """Set how hard the signal is driven into the waveshaper."""
    global _gain
    _gain = max(1.0, min(40.0, value))


def set_mix(value: float):
    """Set the blend between clean audio and distorted audio."""
    global _mix
    _mix = max(0.0, min(1.0, value))


def set_drive(gain: float):
    """Alias used by the UI for the distortion gain control."""
    set_gain(gain)


def set_level(mix: float):
    """Alias used by the UI for the distortion mix control."""
    set_mix(mix)


def apply_distortion(
    chunk: np.ndarray,
    samplerate: int,
    gain: float = None,
    mix: float = None,
) -> np.ndarray:
    """Apply tanh soft clipping and blend it with the original signal."""
    gain = _gain if gain is None else gain
    mix = _mix if mix is None else mix
    dry = chunk
    driven = chunk * gain
    distorted = np.tanh(driven)
    output = dry * (1.0 - mix) + distorted * mix
    return np.clip(output, -1.0, 1.0).astype("float32")


def reset_distortion():
    """Reset hook kept for consistency with stateful effects."""
    pass
