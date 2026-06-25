import numpy as np
import sounddevice as sd

def play_audio(audio: np.ndarray, samplerate: int) -> None:
    """Spielt ein numpy-Array direkt ab (blockierend)."""
    sd.play(audio, samplerate)
    sd.wait()  # Wartet bis Playback fertig


def get_output_stream(callback, samplerate: int = 44100, blocksize: int = 1024):
    return sd.OutputStream(       # ← nicht Stream
        samplerate=samplerate,
        blocksize=blocksize,
        dtype='float32',
        channels=1,
        callback=callback
    )