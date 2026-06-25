import numpy as np


def apply_distortion(
    chunk: np.ndarray,
    samplerate: int,
    gain: float = 8.0,
    mix: float = 0.7
) -> np.ndarray:
    """
    Einfacher Distortion-Effekt via Soft Clipping.

    gain: Verstärkung vor der Verzerrung
    mix: Verhältnis zwischen Original und verzerrtem Signal
         0.0 = nur Original
         1.0 = nur Distortion
    """

    dry = chunk
    driven = chunk * gain

    # Soft clipping mit tanh klingt angenehmer als hartes Abschneiden
    distorted = np.tanh(driven)

    output = dry * (1.0 - mix) + distorted * mix

    output = np.clip(output, -1.0, 1.0)

    return output


def reset_distortion():
    
    pass