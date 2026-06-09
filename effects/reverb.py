import numpy as np

# Zustand zwischen den Frames persistent halten
_buffer = None
_buffer_pos = 0

def apply_reverb(chunk: np.ndarray, samplerate: int) -> np.ndarray:
    """
    Reverb via Delay-Summation (Schroeder-style).
    Mehrere Echos mit unterschiedlichen Verzögerungen und Dämpfungen
    werden auf das Signal addiert.
    """
    global _buffer, _buffer_pos

    # Delays in Millisekunden und ihre Dämpfungsfaktoren
    delays = [
        (0.030, 0.6),   # 30ms,  60% Lautstärke
        (0.045, 0.4),   # 45ms,  40%
        (0.070, 0.25),  # 70ms,  25%
        (0.100, 0.15),  # 100ms, 15%
    ]

    max_delay_samples = int(max(d[0] for d in delays) * samplerate)

    # Buffer beim ersten Aufruf initialisieren
    if _buffer is None or len(_buffer) != max_delay_samples:
        _buffer = np.zeros(max_delay_samples, dtype='float32')

    output = chunk.copy()

    for delay_sec, decay in delays:
        delay_samples = int(delay_sec * samplerate)
        echo = np.zeros_like(chunk)

        for i in range(len(chunk)):
            buf_idx = (_buffer_pos + i - delay_samples) % max_delay_samples
            echo[i] = _buffer[buf_idx] * decay

        output += echo

    # Aktuellen Chunk in den Buffer schreiben
    for i in range(len(chunk)):
        _buffer[(_buffer_pos + i) % max_delay_samples] = chunk[i]

    _buffer_pos = (_buffer_pos + len(chunk)) % max_delay_samples

    # Clipping verhindern
    output = np.clip(output, -1.0, 1.0)

    return output


def reset():
    """Buffer zurücksetzen — aufrufen wenn Reverb ausgeschaltet wird."""
    global _buffer, _buffer_pos
    _buffer = None
    _buffer_pos = 0