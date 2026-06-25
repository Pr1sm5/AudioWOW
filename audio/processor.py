import numpy as np
from audio.input_handler import load_wav
from audio.output_handler import get_output_stream
import sounddevice as sd

SAMPLERATE = 44100
BLOCKSIZE = 1024

active_effects = []
_audio_data = None
_position = 0
_volume = 1.0
_mic_mode = False
_mic_device_index = None  # ← neu

def set_volume(value: float):
    global _volume
    _volume = max(0.0, min(2.0, value))
    print(f"Volume: {int(_volume * 100)}%")


def load_file(filepath: str):
    global _audio_data, _position, _mic_mode
    _mic_mode = False
    _audio_data, sr = load_wav(filepath)
    _position = 0
    print(f"Geladen: {filepath} | {sr} Hz | {len(_audio_data)} Samples")


def load_audio_data(data: np.ndarray, samplerate: int = 44100):
    global _audio_data, _position, _mic_mode, SAMPLERATE
    _mic_mode = False
    _audio_data = data.astype('float32')
    _position = 0
    SAMPLERATE = samplerate


def enable_mic(device_index: int = None):
    global _mic_mode, _mic_device_index
    _mic_mode = True
    _mic_device_index = device_index
    print("Mikrofon: aktiv")


# Callback für WAV / Sinuswelle (OutputStream)
def _callback_file(outdata, frames, time, status):
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

    chunk = chunk * _volume
    outdata[:] = chunk.reshape(-1, 1)
    _position = end % len(_audio_data)


# Callback für Mikrofon (Stream, hat indata)
def _callback_mic(indata, outdata, frames, time, status):
    chunk = indata[:, 0].copy()  # Mono aus erstem Kanal

    for effect_fn in active_effects:
        chunk = effect_fn(chunk, SAMPLERATE)

    chunk = chunk * _volume
    outdata[:] = chunk.reshape(-1, 1)


def start_stream():
    if _mic_mode:
        return sd.Stream(
            device=(_mic_device_index, sd.default.device[1]),  # ← Index statt Name
            samplerate=SAMPLERATE,
            blocksize=BLOCKSIZE,
            dtype='float32',
            channels=1,
            callback=_callback_mic
        )
    else:
        from audio.output_handler import get_output_stream
        return get_output_stream(_callback_file, SAMPLERATE, BLOCKSIZE)