import numpy as np

# Zustand persistent halten
_delay_buffer = None
_delay_buffer_pos = 0

def apply_delay(
    chunk: np.ndarray,
    samplerate: int,
    delay_sec: float = 0.35,
    feedback: float = 0.4,
    mix: float = 0.5
) -> np.ndarray:
    """
    Einfacher Delay-Effekt.

    delay_sec: Verzögerung in Sekunden, z.B. 0.35 = 350ms
    feedback: Wie stark das Echo wieder in den Buffer zurückgeht
    mix: Verhältnis zwischen Originalsignal und Delay
         0.0 = nur trocken
         1.0 = starkes Delay
    """
    global _delay_buffer, _delay_buffer_pos

    delay_samples = int(delay_sec * samplerate)

    if delay_samples <= 0:
        return chunk

    # Buffer initialisieren
    if _delay_buffer is None or len(_delay_buffer) != delay_samples:
        _delay_buffer = np.zeros(delay_samples, dtype="float32")
        _delay_buffer_pos = 0

    output = np.zeros_like(chunk)

    for i in range(len(chunk)):
        dry = chunk[i]
        delayed = _delay_buffer[_delay_buffer_pos]

        # Dry/Wet-Mix
        output[i] = dry * (1.0 - mix) + delayed * mix

        # Feedback in Buffer schreiben
        _delay_buffer[_delay_buffer_pos] = dry + delayed * feedback

        _delay_buffer_pos = (_delay_buffer_pos + 1) % delay_samples

    output = np.clip(output, -1.0, 1.0)

    return output


def reset_delay():
    """Delay-Buffer zurücksetzen — aufrufen wenn Delay ausgeschaltet wird."""
    global _delay_buffer, _delay_buffer_pos
    _delay_buffer = None
    _delay_buffer_pos = 0