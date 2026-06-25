import numpy as np
import sounddevice as sd
from audio.input_handler import load_wav
from audio.output_handler import get_output_stream
from audio import mixer

SAMPLERATE = 44100
BLOCKSIZE = 1024
active_effects = []
_volume = 1.0
_mic_mode = False
_mic_device_index = None


def set_volume(value: float):
    global _volume
    _volume = max(0.0, min(2.0, value))
    print(f"Volume: {int(_volume * 100)}%")


def load_file(filepath: str, name: str = None, volume: float = 1.0):
    from audio.input_handler import load_wav
    data, sr = load_wav(filepath)
    track_name = name or filepath.split("\\")[-1]
    mixer.add_track(data, name=track_name, volume=volume)


def enable_mic(device_index: int = None, volume: float = 1.0):
    global _mic_mode, _mic_device_index
    _mic_mode = True
    _mic_device_index = device_index
    mixer.enable_mic(volume=volume)


def _callback_file(outdata, frames, time, status):
    chunk = mixer.get_mix_chunk(frames, samplerate=SAMPLERATE)  # ← samplerate ergänzt

    for effect_fn in active_effects:
        chunk = effect_fn(chunk, SAMPLERATE)

    chunk = chunk * _volume
    outdata[:] = chunk.reshape(-1, 1)


def _callback_mic(indata, outdata, frames, time, status):
    mic_chunk = indata[:, 0].copy()
    chunk = mixer.get_mix_chunk(frames, samplerate=SAMPLERATE, mic_chunk=mic_chunk)  # ← samplerate ergänzt

    for effect_fn in active_effects:
        chunk = effect_fn(chunk, SAMPLERATE)

    chunk = chunk * _volume
    outdata[:] = chunk.reshape(-1, 1)

def load_audio_data(data: np.ndarray, samplerate: int = 44100):
    """Lädt ein numpy array direkt als Audioquelle (z.B. Sinuswelle)."""
    global _audio_data, _position, _mic_mode, SAMPLERATE
    _mic_mode = False
    _audio_data = data.astype('float32')
    _position = 0
    SAMPLERATE = samplerate
    print(f"Audio geladen | {samplerate} Hz | {len(data)} Samples")

def start_stream():
    if _mic_mode:
        return sd.Stream(
            device=(_mic_device_index, sd.default.device[1]),
            samplerate=SAMPLERATE,
            blocksize=BLOCKSIZE,
            dtype='float32',
            channels=1,
            callback=_callback_mic
        )
    else:
        return get_output_stream(_callback_file, SAMPLERATE, BLOCKSIZE)