import numpy as np
from audio.input_handler import load_wav
from audio.output_handler import get_output_stream

SAMPLERATE = 44100
BLOCKSIZE = 1024

active_effects = []  # Effekt-Funktionen werden hier rein/rausgehängt
_audio_data = None
_position = 0        # Aktuelle Leseposition im WAV
_volume = 1.0


def set_volume(value: float):
    global _volume
    _volume = max(0.0, min(2.0, value))  # Clamp zwischen 0 und 2
    print(f"Volume: {int(_volume * 100)}%")


def load_file(filepath: str):
    """WAV laden und global speichern."""
    global _audio_data, _position
    _audio_data, sr = load_wav(filepath)
    _position = 0
    print(f"Geladen: {filepath} | {sr} Hz | {len(_audio_data)} Samples")


def _callback(outdata, frames, time, status):
    global _position

    if _audio_data is None:
        outdata[:] = np.zeros((frames, 1), dtype='float32')
        return

    end = _position + frames
    chunk = _audio_data[_position:end]

    if len(chunk) < frames:
        chunk = np.pad(chunk, (0, frames - len(chunk)))

    for effect_fn in active_effects:
        chunk = effect_fn(chunk, SAMPLERATE)

    chunk = chunk * _volume  # ← Volume anwenden

    outdata[:] = chunk.reshape(-1, 1)
    _position = end % len(_audio_data)


def start_stream():
    """Startet den Audio-Stream."""
    stream = get_output_stream(_callback, SAMPLERATE, BLOCKSIZE)
    return stream