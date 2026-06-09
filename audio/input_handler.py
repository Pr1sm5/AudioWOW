import numpy as np
import soundfile as sf  # pip install soundfile


def load_wav(filepath: str) -> tuple[np.ndarray, int]:
    """
    Lädt eine WAV-Datei.
    Gibt (audio_data, samplerate) zurück.
    audio_data ist immer Mono (1D numpy array).
    """
    data, samplerate = sf.read(filepath, dtype='float32')

    # Stereo → Mono (Durchschnitt beider Kanäle)
    if data.ndim == 2:
        data = np.mean(data, axis=1)

    return data, samplerate


def get_microphone_devices() -> list:
    """Listet verfügbare Eingabegeräte auf."""
    import sounddevice as sd
    devices = sd.query_devices()
    return [d for d in devices if d['max_input_channels'] > 0]