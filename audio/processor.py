import numpy as np
import sounddevice as sd
from threading import Lock
from audio.input_handler import load_wav
from audio.output_handler import get_output_stream
from audio import mixer

SAMPLERATE = 44100
BLOCKSIZE = 1024
active_effects = []
_volume = 1.0
_mic_mode = False
_mic_device_index = None
_signal_lock = Lock()
_latest_signal = np.zeros(BLOCKSIZE, dtype="float32")


def set_volume(value: float):
    """Set the master output volume, clamped between silence and 200%."""
    global _volume
    _volume = max(0.0, min(2.0, value))
    print(f"Volume: {int(_volume * 100)}%")


def get_latest_signal() -> np.ndarray:
    """Return a thread-safe copy of the most recent output chunk for visualizers."""
    with _signal_lock:
        return _latest_signal.copy()


def _publish_signal(chunk: np.ndarray):
    """Store the latest processed chunk so the UI can draw it outside the audio thread."""
    global _latest_signal
    with _signal_lock:
        _latest_signal = chunk.astype("float32", copy=True)


def _resample_audio(data: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    """Convert loaded audio to the app sample rate using simple linear interpolation."""
    if source_rate == target_rate or len(data) == 0:
        return data.astype("float32")

    duration = len(data) / source_rate
    source_times = np.linspace(0.0, duration, num=len(data), endpoint=False)
    target_length = int(duration * target_rate)
    target_times = np.linspace(0.0, duration, num=target_length, endpoint=False)
    return np.interp(target_times, source_times, data).astype("float32")


def load_file(filepath: str, name: str = None, volume: float = 1.0):
    """Load a WAV file, normalize its sample rate, and register it with the mixer."""
    from audio.input_handler import load_wav
    data, sr = load_wav(filepath)
    data = _resample_audio(data, sr, SAMPLERATE)
    track_name = name or filepath.split("\\")[-1]
    mixer.add_track(data, name=track_name, volume=volume)


def enable_mic(device_index: int = None, volume: float = 1.0):
    """Switch the processor into microphone mode and tell the mixer to include mic audio."""
    global _mic_mode, _mic_device_index
    _mic_mode = True
    _mic_device_index = device_index
    mixer.enable_mic(volume=volume)


def _callback_file(outdata, frames, time, status):
    """Audio callback for playback without microphone input."""
    chunk = mixer.get_mix_chunk(frames, samplerate=SAMPLERATE)  # ← samplerate ergänzt

    for effect_fn in active_effects:
        chunk = effect_fn(chunk, SAMPLERATE)

    chunk = chunk * _volume
    _publish_signal(chunk)
    outdata[:] = chunk.reshape(-1, 1)


def _callback_mic(indata, outdata, frames, time, status):
    """Audio callback that mixes live microphone input with any loaded tracks."""
    mic_chunk = indata[:, 0].copy()
    chunk = mixer.get_mix_chunk(frames, samplerate=SAMPLERATE, mic_chunk=mic_chunk)  # ← samplerate ergänzt

    for effect_fn in active_effects:
        chunk = effect_fn(chunk, SAMPLERATE)

    chunk = chunk * _volume
    _publish_signal(chunk)
    outdata[:] = chunk.reshape(-1, 1)

def load_audio_data(data: np.ndarray, samplerate: int = 44100):
    """Lädt ein numpy array direkt als Audioquelle (z.B. Sinuswelle)."""
    global _audio_data, _position, SAMPLERATE
    _audio_data = data.astype('float32')
    _position = 0
    SAMPLERATE = samplerate
    mixer.add_track(_audio_data, name="Sine wave", volume=1.0)
    print(f"Audio geladen | {samplerate} Hz | {len(data)} Samples")


def clear_sources():
    """Remove all audio sources and reset the published visualizer signal."""
    global _mic_mode, _mic_device_index
    _mic_mode = False
    _mic_device_index = None
    mixer.clear_tracks()
    mixer.disable_mic()
    _publish_signal(np.zeros(BLOCKSIZE, dtype="float32"))


def start_stream():
    """Create, but do not start, the correct stream for the current input mode."""
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
