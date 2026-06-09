import numpy as np
from audio.input_handler import load_wav
from audio.output_handler import get_output_stream

SAMPLERATE = 44100
BLOCKSIZE = 1024

active_effects = []  # Effekt-Funktionen werden hier rein/rausgehängt
_audio_data = None
_position = 0        # Aktuelle Leseposition im WAV

def load_file(filepath: str):
    """WAV laden und global speichern."""
    global _audio_data, _position
    _audio_data, sr = load_wav(filepath)
    _position = 0
    print(f"Geladen: {filepath} | {sr} Hz | {len(_audio_data)} Samples")

def _callback(outdata, frames, time, status):
    """Wird von sounddevice pro Block aufgerufen."""
    global _position

    if _audio_data is None:
        outdata[:] = np.zeros((frames, 1), dtype='float32')
        return

    end = _position + frames
    chunk = _audio_data[_position:end]

    # Auffüllen falls am Ende der Datei
    if len(chunk) < frames:
        chunk = np.pad(chunk, (0, frames - len(chunk)))

    # Effekte anwenden
    for effect_fn in active_effects:
        chunk = effect_fn(chunk, SAMPLERATE)

    outdata[:] = chunk.reshape(-1, 1)
    _position = end % len(_audio_data)  # Loop

def start_stream():
    """Startet den Audio-Stream."""
    stream = get_output_stream(_callback, SAMPLERATE, BLOCKSIZE)
    return stream