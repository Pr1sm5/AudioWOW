import numpy as np

# Jede Quelle: {'data': np.ndarray, 'position': int, 'volume': float, 'name': str}
_tracks = []
_mic_enabled = False
_mic_volume = 1.0


def add_track(data: np.ndarray, name: str = "Track", volume: float = 1.0):
    _tracks.append({
        'data': data.astype('float32'),
        'position': 0,
        'volume': volume,
        'name': name
    })
    print(f"Track hinzugefügt: {name} | {len(data)} Samples")


def remove_track(index: int):
    if 0 <= index < len(_tracks):
        name = _tracks[index]['name']
        _tracks.pop(index)
        print(f"Track entfernt: {name}")


def list_tracks():
    if not _tracks:
        print("Keine Tracks geladen.")
        return
    for i, t in enumerate(_tracks):
        print(f"  [{i}] {t['name']} | Volume: {int(t['volume'] * 100)}%")


def set_track_volume(index: int, volume: float):
    if 0 <= index < len(_tracks):
        _tracks[index]['volume'] = max(0.0, min(2.0, volume))


def enable_mic(volume: float = 1.0):
    global _mic_enabled, _mic_volume
    _mic_enabled = True
    _mic_volume = volume
    print("Mic-Track: aktiv")


def disable_mic():
    global _mic_enabled
    _mic_enabled = False
    print("Mic-Track: deaktiviert")


def get_mix_chunk(frames: int, mic_chunk: np.ndarray = None) -> np.ndarray:
    """Mixt alle aktiven Tracks + optional Mic zu einem Chunk zusammen."""
    mixed = np.zeros(frames, dtype='float32')

    # WAV Tracks addieren
    for track in _tracks:
        data = track['data']
        pos = track['position']
        end = pos + frames

        chunk = data[pos:end]
        if len(chunk) < frames:
            chunk = np.pad(chunk, (0, frames - len(chunk)))

        mixed += chunk * track['volume']

        # Loop
        track['position'] = end % len(data)

    # Mic addieren
    if _mic_enabled and mic_chunk is not None:
        mixed += mic_chunk * _mic_volume

    # Normalisieren — verhindert Clipping wenn mehrere Tracks laut sind
    peak = np.max(np.abs(mixed))
    if peak > 1.0:
        mixed /= peak

    return mixed