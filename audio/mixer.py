import numpy as np

_tracks = []
_mic_enabled = False
_mic_volume = 1.0
_solo_index = None


def add_track(data: np.ndarray, name: str = "Track", volume: float = 1.0):
    _tracks.append({
        'data':     data.astype('float32'),
        'position': 0,
        'volume':   volume,
        'name':     name,
        'muted':    False,
        'effects':  [],   # ← neu: Track-eigene Effektliste
    })
    print(f"Track hinzugefügt: {name} | {len(data)} Samples")


def remove_track(index: int):
    global _solo_index
    if 0 <= index < len(_tracks):
        name = _tracks[index]['name']
        _tracks.pop(index)
        if _solo_index == index:
            _solo_index = None
        print(f"Track entfernt: {name}")


def list_tracks():
    if not _tracks and not _mic_enabled:
        print("Keine Tracks geladen.")
        return
    for i, t in enumerate(_tracks):
        solo_marker = " [SOLO]" if _solo_index == i else ""
        mute_marker = " [MUTE]" if t['muted']       else ""
        fx_names    = ", ".join(fn.__name__.replace("apply_", "") for fn in t['effects'])
        fx_str      = f" | FX: {fx_names}" if fx_names else ""
        print(f"  [{i}] {t['name']} | Vol: {int(t['volume'] * 100)}%{solo_marker}{mute_marker}{fx_str}")
    if _mic_enabled:
        print(f"  [M] Mikrofon | Vol: {int(_mic_volume * 100)}%")


def solo_track(index: int):
    global _solo_index
    if _solo_index == index:
        _solo_index = None
        print("Solo OFF")
    else:
        _solo_index = index
        print(f"Solo: {_tracks[index]['name']}")


def mute_track(index: int):
    if 0 <= index < len(_tracks):
        _tracks[index]['muted'] = not _tracks[index]['muted']
        state = "MUTE" if _tracks[index]['muted'] else "UNMUTE"
        print(f"{state}: {_tracks[index]['name']}")


def set_track_volume(index: int, volume: float):
    if 0 <= index < len(_tracks):
        _tracks[index]['volume'] = max(0.0, min(2.0, volume))
        print(f"Track {index} Volume: {int(volume * 100)}%")


def add_track_effect(track_index: int, effect_fn):
    """Effekt zu einem bestimmten Track hinzufügen."""
    if 0 <= track_index < len(_tracks):
        if effect_fn not in _tracks[track_index]['effects']:
            _tracks[track_index]['effects'].append(effect_fn)
            print(f"FX '{effect_fn.__name__}' → {_tracks[track_index]['name']}")


def remove_track_effect(track_index: int, effect_fn):
    """Effekt von einem bestimmten Track entfernen."""
    if 0 <= track_index < len(_tracks):
        if effect_fn in _tracks[track_index]['effects']:
            _tracks[track_index]['effects'].remove(effect_fn)
            print(f"FX '{effect_fn.__name__}' entfernt von {_tracks[track_index]['name']}")


def enable_mic(volume: float = 1.0):
    global _mic_enabled, _mic_volume
    _mic_enabled = True
    _mic_volume = volume
    print("Mic-Track: aktiv")


def disable_mic():
    global _mic_enabled
    _mic_enabled = False


def get_mix_chunk(frames: int, samplerate: int = 44100, mic_chunk: np.ndarray = None) -> np.ndarray:
    mixed = np.zeros(frames, dtype='float32')

    for i, track in enumerate(_tracks):
        if _solo_index is not None and _solo_index != i:
            _advance_position(track, frames)
            continue
        if track['muted']:
            _advance_position(track, frames)
            continue

        data = track['data']
        pos  = track['position']
        end  = pos + frames

        chunk = data[pos:end]
        if len(chunk) < frames:
            chunk = np.pad(chunk, (0, frames - len(chunk)))

        # ← Track-eigene Effekte anwenden
        for effect_fn in track['effects']:
            chunk = effect_fn(chunk, samplerate)

        mixed += chunk * track['volume']
        track['position'] = end % len(data)

    if _mic_enabled and mic_chunk is not None and _solo_index is None:
        mixed += mic_chunk * _mic_volume

    peak = np.max(np.abs(mixed))
    if peak > 1.0:
        mixed /= peak

    return mixed


def _advance_position(track: dict, frames: int):
    track['position'] = (track['position'] + frames) % len(track['data'])