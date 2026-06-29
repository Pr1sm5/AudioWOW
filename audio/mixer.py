import numpy as np

_tracks = []
_mic_enabled = False
_mic_volume = 1.0
_solo_index = None

DEFAULT_FX_PARAMS = {
    'reverb':     {'dry': 1.0, 'wet': 0.5},
    'delay':      {'seconds': 0.35, 'feedback': 0.4, 'dry': 1.0, 'wet': 0.5},
    'lowpass':    {'cutoff': 1000.0},
    'highpass':   {'cutoff': 500.0},
    'distortion': {'drive': 8.0, 'level': 0.7},
}


def add_track(data: np.ndarray, name: str = "Track", volume: float = 1.0):
    """Add a mono float32 buffer as a looping mixer track."""
    _tracks.append({
        'data': data.astype('float32'),
        'position': 0,
        'volume': volume,
        'name': name,
        'muted': False,
        'fx_enabled': set(),
        'fx_params': {name: params.copy() for name, params in DEFAULT_FX_PARAMS.items()},
        'fx_state': {},
    })
    print(f"Track added: {name} | {len(data)} samples")


def remove_track(index: int):
    """Remove a track and keep the solo selection consistent."""
    global _solo_index
    if 0 <= index < len(_tracks):
        name = _tracks[index]['name']
        _tracks.pop(index)
        if _solo_index == index:
            _solo_index = None
        elif _solo_index is not None and _solo_index > index:
            _solo_index -= 1
        print(f"Track removed: {name}")


def clear_tracks():
    """Remove every loaded track and clear solo mode."""
    global _solo_index
    _tracks.clear()
    _solo_index = None


def has_sources() -> bool:
    """Return whether the mixer has at least one file/sine track or microphone input."""
    return bool(_tracks) or _mic_enabled


def get_tracks():
    """Return UI-friendly metadata for all loaded tracks."""
    return [
        {
            'index': index,
            'name': track['name'],
            'volume': track['volume'],
            'muted': track['muted'],
            'solo': _solo_index == index,
            'effects': sorted(track['fx_enabled']),
        }
        for index, track in enumerate(_tracks)
    ]


def track_count() -> int:
    """Return the number of loaded non-microphone tracks."""
    return len(_tracks)


def track_has_effect(index: int, effect_fn) -> bool:
    """Check whether a track has a named effect enabled."""
    return 0 <= index < len(_tracks) and _effect_name(effect_fn) in _tracks[index]['fx_enabled']


def get_track_effects(index: int):
    """Return a copy of the enabled effect names for one track."""
    if not 0 <= index < len(_tracks):
        return set()
    return set(_tracks[index]['fx_enabled'])


def get_track_effect_params(index: int):
    """Return copied per-effect parameters for one track."""
    if not 0 <= index < len(_tracks):
        return {name: params.copy() for name, params in DEFAULT_FX_PARAMS.items()}
    return {name: params.copy() for name, params in _tracks[index]['fx_params'].items()}


def set_track_effect_enabled(index: int, effect_name: str, enabled: bool):
    """Turn a per-track effect on or off and clear stale state when disabled."""
    if not 0 <= index < len(_tracks) or effect_name not in DEFAULT_FX_PARAMS:
        return

    track = _tracks[index]
    if enabled:
        track['fx_enabled'].add(effect_name)
    else:
        track['fx_enabled'].discard(effect_name)
        track['fx_state'].pop(effect_name, None)


def set_track_effect_param(index: int, effect_name: str, param_name: str, value: float):
    """Update one per-track effect parameter after clamping it to a safe range."""
    if not 0 <= index < len(_tracks):
        return
    if effect_name not in _tracks[index]['fx_params']:
        return
    if param_name not in _tracks[index]['fx_params'][effect_name]:
        return

    clamped = _clamp_effect_param(effect_name, param_name, value)
    _tracks[index]['fx_params'][effect_name][param_name] = clamped
    if effect_name in ('delay', 'reverb') and param_name == 'seconds':
        _tracks[index]['fx_state'].pop(effect_name, None)


def clear_solo():
    """Disable solo mode so all unmuted tracks can be heard."""
    global _solo_index
    _solo_index = None


def list_tracks():
    """Print a CLI-friendly overview of tracks, volume, mute, solo, and effects."""
    if not _tracks and not _mic_enabled:
        print("Keine Tracks geladen.")
        return
    for i, track in enumerate(_tracks):
        solo_marker = " [SOLO]" if _solo_index == i else ""
        mute_marker = " [MUTE]" if track['muted'] else ""
        fx_names = ", ".join(sorted(track['fx_enabled']))
        fx_str = f" | FX: {fx_names}" if fx_names else ""
        print(f"  [{i}] {track['name']} | Vol: {int(track['volume'] * 100)}%{solo_marker}{mute_marker}{fx_str}")
    if _mic_enabled:
        print(f"  [M] Mikrofon | Vol: {int(_mic_volume * 100)}%")


def solo_track(index: int):
    """Toggle solo mode for a single track."""
    global _solo_index
    if not 0 <= index < len(_tracks):
        return
    if _solo_index == index:
        _solo_index = None
        print("Solo OFF")
    else:
        _solo_index = index
        print(f"Solo: {_tracks[index]['name']}")


def mute_track(index: int):
    """Toggle mute for a single track and print the new state."""
    if 0 <= index < len(_tracks):
        set_track_muted(index, not _tracks[index]['muted'])
        state = "MUTE" if _tracks[index]['muted'] else "UNMUTE"
        print(f"{state}: {_tracks[index]['name']}")


def set_track_muted(index: int, muted: bool):
    """Set a track's mute state directly."""
    if 0 <= index < len(_tracks):
        _tracks[index]['muted'] = muted


def set_track_volume(index: int, volume: float):
    """Set one track's volume, clamped between silence and 200%."""
    if 0 <= index < len(_tracks):
        _tracks[index]['volume'] = max(0.0, min(2.0, volume))


def add_track_effect(track_index: int, effect_fn):
    """Enable an effect on one track using the function name as the effect key."""
    effect_name = _effect_name(effect_fn)
    set_track_effect_enabled(track_index, effect_name, True)
    if 0 <= track_index < len(_tracks):
        print(f"FX '{effect_name}' -> {_tracks[track_index]['name']}")


def remove_track_effect(track_index: int, effect_fn):
    """Disable an effect on one track using the function name as the effect key."""
    effect_name = _effect_name(effect_fn)
    set_track_effect_enabled(track_index, effect_name, False)
    if 0 <= track_index < len(_tracks):
        print(f"FX '{effect_name}' removed from {_tracks[track_index]['name']}")


def enable_mic(volume: float = 1.0):
    """Include microphone chunks in the mixed output."""
    global _mic_enabled, _mic_volume
    _mic_enabled = True
    _mic_volume = volume
    print("Mic-Track: aktiv")


def disable_mic():
    """Stop including microphone chunks in the mixed output."""
    global _mic_enabled
    _mic_enabled = False


def get_mix_chunk(frames: int, samplerate: int = 44100, mic_chunk: np.ndarray = None) -> np.ndarray:
    """Build the next mixed audio block from tracks, mic input, and per-track effects."""
    mixed = np.zeros(frames, dtype='float32')

    for i, track in enumerate(_tracks):
        if _solo_index is not None and _solo_index != i:
            _advance_position(track, frames)
            continue
        if track['muted']:
            _advance_position(track, frames)
            continue

        data = track['data']
        pos = track['position']
        end = pos + frames

        chunk = data[pos:end]
        if len(chunk) < frames:
            chunk = np.pad(chunk, (0, frames - len(chunk)))

        chunk = _apply_track_effects(track, chunk, samplerate)
        mixed += chunk * track['volume']
        track['position'] = end % len(data)

    if _mic_enabled and mic_chunk is not None and _solo_index is None:
        mixed += mic_chunk * _mic_volume

    peak = np.max(np.abs(mixed))
    if peak > 1.0:
        mixed /= peak

    return mixed


def _advance_position(track: dict, frames: int):
    """Move a skipped track forward so mute/solo does not pause its timeline."""
    track['position'] = (track['position'] + frames) % len(track['data'])


def _effect_name(effect_fn) -> str:
    """Convert apply_reverb-style function names into mixer effect keys."""
    return getattr(effect_fn, '__name__', str(effect_fn)).replace('apply_', '')


def _clamp_effect_param(effect_name: str, param_name: str, value: float) -> float:
    """Keep effect parameters inside ranges that avoid silence, runaway feedback, or clipping."""
    if param_name in ('wet', 'level'):
        return max(0.0, min(1.0, value))
    if param_name == 'dry':
        return max(1.0, min(2.0, value))
    if effect_name == 'delay' and param_name == 'feedback':
        return max(0.0, min(0.9, value))
    if effect_name == 'delay' and param_name == 'seconds':
        return max(0.01, min(2.0, value))
    if param_name == 'cutoff':
        return max(20.0, min(20000.0, value))
    if param_name == 'drive':
        return max(1.0, min(40.0, value))
    return value


def _apply_track_effects(track: dict, chunk: np.ndarray, samplerate: int) -> np.ndarray:
    """Apply enabled effects in a stable order while preserving stateful buffers."""
    for effect_name in ('reverb', 'delay', 'lowpass', 'highpass', 'distortion'):
        if effect_name not in track['fx_enabled']:
            continue
        params = track['fx_params'][effect_name]
        state = track['fx_state'].setdefault(effect_name, {})
        if effect_name == 'reverb':
            chunk = _apply_track_reverb(chunk, samplerate, params, state)
        elif effect_name == 'delay':
            chunk = _apply_track_delay(chunk, samplerate, params, state)
        elif effect_name == 'lowpass':
            chunk = _apply_track_lowpass(chunk, samplerate, params, state)
        elif effect_name == 'highpass':
            chunk = _apply_track_highpass(chunk, samplerate, params, state)
        elif effect_name == 'distortion':
            chunk = _apply_track_distortion(chunk, params)
    return chunk


def _apply_track_reverb(chunk: np.ndarray, samplerate: int, params: dict, state: dict) -> np.ndarray:
    """Add several short echoes to simulate room reverb for a single track."""
    delays = ((0.030, 0.6), (0.045, 0.4), (0.070, 0.25), (0.100, 0.15))
    max_delay_samples = int(max(delay for delay, _decay in delays) * samplerate)
    buffer = state.get('buffer')
    if buffer is None or len(buffer) != max_delay_samples:
        buffer = np.zeros(max_delay_samples, dtype='float32')
        state['buffer'] = buffer
        state['pos'] = 0

    pos = state.get('pos', 0)
    wet = chunk.copy()
    for delay_sec, decay in delays:
        delay_samples = int(delay_sec * samplerate)
        echo = np.zeros_like(chunk)
        for i in range(len(chunk)):
            echo[i] = buffer[(pos + i - delay_samples) % max_delay_samples] * decay
        wet += echo

    for i in range(len(chunk)):
        buffer[(pos + i) % max_delay_samples] = chunk[i]

    state['pos'] = (pos + len(chunk)) % max_delay_samples
    mix = params.get('wet', 0.5)
    dry = params.get('dry', 1.0)
    return np.clip(chunk * dry + wet * mix, -1.0, 1.0).astype('float32')


def _apply_track_delay(chunk: np.ndarray, samplerate: int, params: dict, state: dict) -> np.ndarray:
    """Apply a feedback delay line using per-track state."""
    delay_samples = int(params['seconds'] * samplerate)
    if delay_samples <= 0:
        return chunk

    buffer = state.get('buffer')
    if buffer is None or len(buffer) != delay_samples:
        buffer = np.zeros(delay_samples, dtype='float32')
        state['buffer'] = buffer
        state['pos'] = 0

    pos = state.get('pos', 0)
    output = np.zeros_like(chunk)
    dry_gain = params.get('dry', 1.0)
    wet_gain = params.get('wet', 0.5)
    for i in range(len(chunk)):
        dry     = chunk[i]
        delayed = buffer[pos]
        output[i] = dry * dry_gain + delayed * wet_gain
        buffer[pos] = dry + delayed * params['feedback']
        pos = (pos + 1) % delay_samples

    state['pos'] = pos
    return np.clip(output, -1.0, 1.0).astype('float32')


def _apply_track_lowpass(chunk: np.ndarray, samplerate: int, params: dict, state: dict) -> np.ndarray:
    """Apply a one-pole lowpass filter that smooths away high frequencies."""
    cutoff = params['cutoff']
    dt = 1.0 / samplerate
    rc = 1.0 / (2.0 * np.pi * cutoff)
    alpha = dt / (rc + dt)
    last = state.get('last', chunk[0])
    output = np.zeros_like(chunk)
    for i in range(len(chunk)):
        last = last + alpha * (chunk[i] - last)
        output[i] = last
    state['last'] = last
    return np.clip(output, -1.0, 1.0).astype('float32')


def _apply_track_highpass(chunk: np.ndarray, samplerate: int, params: dict, state: dict) -> np.ndarray:
    """Apply a one-pole highpass filter that reduces low frequencies."""
    cutoff = params['cutoff']
    dt = 1.0 / samplerate
    rc = 1.0 / (2.0 * np.pi * cutoff)
    alpha = rc / (rc + dt)
    last_input = state.get('last_input', chunk[0])
    last_output = state.get('last_output', 0.0)
    output = np.zeros_like(chunk)
    for i in range(len(chunk)):
        current = chunk[i]
        last_output = alpha * (last_output + current - last_input)
        output[i] = last_output
        last_input = current
    state['last_input'] = last_input
    state['last_output'] = last_output
    return np.clip(output, -1.0, 1.0).astype('float32')


def _apply_track_distortion(chunk: np.ndarray, params: dict) -> np.ndarray:
    """Apply tanh soft clipping and blend it with the dry signal."""
    distorted = np.tanh(chunk * params['drive'])
    output = chunk * (1.0 - params['level']) + distorted * params['level']
    return np.clip(output, -1.0, 1.0).astype('float32')
