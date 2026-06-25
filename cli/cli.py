import numpy as np
from audio.processor import load_file, load_audio_data, enable_mic, start_stream, active_effects, set_volume
from audio.input_handler import get_microphone_devices
from audio import mixer
from effects.reverb     import apply_reverb,     reset as reset_reverb
from effects.delay      import apply_delay,      reset_delay
from effects.lowpass    import apply_lowpass,    reset_lowpass
from effects.highpass   import apply_highpass,   reset_highpass
from effects.distortion import apply_distortion, reset_distortion

_current_volume = 1.0

EFFECTS = {
    'r': ("Reverb",     apply_reverb,     reset_reverb),
    'd': ("Delay",      apply_delay,      reset_delay),
    'l': ("Lowpass",    apply_lowpass,    reset_lowpass),
    'h': ("Highpass",   apply_highpass,   reset_highpass),
    'x': ("Distortion", apply_distortion, reset_distortion),
}


# ─── Input Quellen ────────────────────────────────────────────────────────────

def _generate_sine(frequency: float, duration: float, samplerate: int = 44100) -> np.ndarray:
    t = np.linspace(0, duration, int(samplerate * duration), endpoint=False)
    return np.sin(2 * np.pi * frequency * t).astype('float32')


def _add_source() -> None:
    """Fügt eine einzelne Quelle zum Mixer hinzu."""
    print("\nQuelle hinzufügen:")
    print("  [1] WAV-Datei")
    print("  [2] Sinuswelle")
    print("  [3] Mikrofon")

    choice = input("Auswahl: ").strip()

    if choice == '1':
        filepath = input("Pfad zur WAV-Datei: ").strip()
        vol = input("Volume 0.0-2.0 (Enter = 1.0): ").strip()
        vol = float(vol) if vol else 1.0
        load_file(filepath, volume=vol)

    elif choice == '2':
        try:
            freq = input("Frequenz Hz (Enter = 440): ").strip()
            freq = float(freq) if freq else 440.0
            dur  = input("Dauer Sekunden (Enter = 5): ").strip()
            dur  = float(dur) if dur else 5.0
            vol  = input("Volume 0.0-2.0 (Enter = 1.0): ").strip()
            vol  = float(vol) if vol else 1.0
            wave = _generate_sine(freq, dur)
            mixer.add_track(wave, name=f"Sine {freq}Hz", volume=vol)
            print(f"Sinuswelle hinzugefügt: {freq} Hz, {dur} s")
        except ValueError:
            print("Ungültige Eingabe.")

    elif choice == '3':
        devices = get_microphone_devices()
        if not devices:
            print("Kein Mikrofon gefunden!")
            return
        print("\nVerfügbare Mikrofone:")
        for i, d in enumerate(devices):
            print(f"  [{i}] {d['name']} (Index: {d['index']})")
        idx = input("Gerät (Enter = Standard): ").strip()
        device_index = devices[int(idx)]['index'] if idx else None
        vol = input("Mic Volume 0.0-2.0 (Enter = 1.0): ").strip()
        vol = float(vol) if vol else 1.0
        enable_mic(device_index, volume=vol)

    else:
        print("Ungültige Auswahl.")


def prompt_input_source() -> None:
    """Mixer-Modus: Mehrere Quellen laden bis [d] gedrückt wird."""
    print("\n=== Quellen verwalten ===")

    while True:
        print("\n  [a] Quelle hinzufügen")
        print("  [r] Track entfernen")
        print("  [l] Tracks anzeigen")
        print("  [d] Fertig / Starten")

        choice = input("Auswahl: ").strip().lower()

        if choice == 'a':
            _add_source()

        elif choice == 'r':
            mixer.list_tracks()
            idx = input("Track Index zum Entfernen: ").strip()
            if idx.isdigit():
                mixer.remove_track(int(idx))

        elif choice == 'l':
            mixer.list_tracks()

        elif choice == 'd':
            if not mixer._tracks and not mixer._mic_enabled:
                print("Mindestens eine Quelle hinzufügen!")
            else:
                break

        else:
            print("Ungültige Auswahl.")


# ─── Effekt Parameter ─────────────────────────────────────────────────────────

def _adjust_params(key: str) -> None:
    try:
        if key == 'r':
            from effects.reverb import set_preset, set_mix
            print("  [1] Preset wählen")
            print("  [2] Dry/Wet Mix")
            print("  [3] Beide")
            sub = input("  Auswahl: ").strip()

            if sub in ('1', '3'):
                print("  [s] Small  [m] Medium  [l] Large  [c] Cave")
                p = input("  Preset: ").strip().lower()
                presets = {'s': 'small', 'm': 'medium', 'l': 'large', 'c': 'cave'}
                if p in presets:
                    set_preset(presets[p])
                else:
                    print("  Unbekanntes Preset.")

            if sub in ('2', '3'):
                val = input("  Mix 0.0-1.0 (Enter = 0.5): ").strip()
                set_mix(float(val) if val else 0.5)
                print(f"  Reverb Mix: {float(val) if val else 0.5}")

        elif key == 'd':
            from effects.delay import set_delay_strength, set_feedback
            print(f"  [1] Stärke  [2] Feedback  [3] Beide")
            sub = input("  Auswahl: ").strip()
            if sub in ('1', '3'):
                val = input("  Stärke 0.0-1.0 (Enter = 0.5): ").strip()
                set_delay_strength(float(val) if val else 0.5)
            if sub in ('2', '3'):
                val = input("  Feedback 0.0-0.9 (Enter = 0.4): ").strip()
                set_feedback(float(val) if val else 0.4)

        elif key == 'l':
            from effects.lowpass import set_cutoff
            freq = input("  Cutoff Hz 20-20000 (Enter = 1000): ").strip()
            set_cutoff(float(freq) if freq else 1000.0)
            print(f"  Lowpass Cutoff: {float(freq) if freq else 1000.0} Hz")

        elif key == 'h':
            from effects.highpass import set_cutoff
            freq = input("  Cutoff Hz 20-20000 (Enter = 500): ").strip()
            set_cutoff(float(freq) if freq else 500.0)
            print(f"  Highpass Cutoff: {float(freq) if freq else 500.0} Hz")

        elif key == 'x':
            from effects.distortion import set_gain, set_mix
            print(f"  [1] Gain  [2] Mix  [3] Beide")
            sub = input("  Auswahl: ").strip()
            if sub in ('1', '3'):
                val = input("  Gain 1.0-40.0 (Enter = 8.0): ").strip()
                set_gain(float(val) if val else 8.0)
            if sub in ('2', '3'):
                val = input("  Mix 0.0-1.0 (Enter = 0.7): ").strip()
                set_mix(float(val) if val else 0.7)

    except ValueError:
        print("  Ungültige Eingabe.")


# ─── Toggle & Volume ──────────────────────────────────────────────────────────

def _toggle(key: str) -> None:
    name, effect_fn, reset_fn = EFFECTS[key]
    if effect_fn in active_effects:
        active_effects.remove(effect_fn)
        if reset_fn:
            reset_fn()
        print(f"{name}: OFF")
    else:
        active_effects.append(effect_fn)
        print(f"{name}: ON")
        _adjust_params(key)


def _change_volume(delta: float) -> None:
    global _current_volume
    _current_volume = max(0.0, min(2.0, _current_volume + delta))
    set_volume(_current_volume)

def _track_fx_menu() -> None:
    """Effekte auf einzelne Tracks anwenden."""
    mixer.list_tracks()
    idx = input("Track Index: ").strip()
    if not idx.isdigit():
        return
    idx = int(idx)

    print("\nEffekt wählen:")
    for k, (name, _, _) in EFFECTS.items():
        print(f"  [{k}] {name}")

    key = input("Effekt Key: ").strip().lower()
    if key not in EFFECTS:
        print("Unbekannter Effekt.")
        return

    name, effect_fn, reset_fn = EFFECTS[key]
    track = mixer._tracks[idx]

    if effect_fn in track['effects']:
        mixer.remove_track_effect(idx, effect_fn)
        if reset_fn:
            reset_fn()
        print(f"{name}: OFF für Track {idx}")
    else:
        mixer.add_track_effect(idx, effect_fn)
        print(f"{name}: ON für Track {idx}")
        _adjust_params(key)


def _track_volume_menu() -> None:
    """Lautstärke eines einzelnen Tracks anpassen."""
    mixer.list_tracks()
    idx = input("Track Index: ").strip()
    if not idx.isdigit():
        return
    idx = int(idx)

    vol = input(f"Neue Lautstärke 0.0-2.0 (Enter = 1.0): ").strip()
    try:
        vol = float(vol) if vol else 1.0
        mixer.set_track_volume(idx, vol)
    except ValueError:
        print("Ungültige Eingabe.")



# ─── Anzeige ──────────────────────────────────────────────────────────────────

def _print_help() -> None:
    print("""
╔══════════════════════════════════╗
║       DASP Live Audio FX         ║
╠══════════════════════════════════╣
║  EFFEKTE (toggle an/aus)         ║
║  [r]  Reverb                     ║
║  [d]  Delay                      ║
║  [l]  Lowpass Filter             ║
║  [h]  Highpass Filter            ║
║  [x]  Distortion                 ║
╠══════════════════════════════════╣
║  PARAMETER                       ║
║  [p]  Effekt-Parameter ändern    ║
╠══════════════════════════════════╣
║  STEUERUNG                       ║
║  [+]  Lauter  [-]  Leiser        ║
║  [i]  Status  [s]  Quellen       ║
║  [?]  Hilfe   [q]  Beenden       ║
║  [f]  Track FX   [v]  Track Vol  ║
╚══════════════════════════════════╝""")


def _print_status() -> None:
    active_names = [EFFECTS[k][0] for k in EFFECTS if EFFECTS[k][1] in active_effects]
    status = ', '.join(active_names) if active_names else 'keine'
    print(f"Volume: {int(_current_volume * 100)}% | Effekte: {status}")
    mixer.list_tracks()


# ─── Haupt-Loop ───────────────────────────────────────────────────────────────

def run() -> None:
    """Startet die CLI. Wird von main.py aufgerufen."""
    prompt_input_source()
    stream = start_stream()

    with stream:
        _print_help()

        while True:
            key = input("> ").strip().lower()

            if key == 'q':
                break
            elif key in EFFECTS:
                _toggle(key)
            elif key == 'p':
                print("Effekt wählen:", {k: EFFECTS[k][0] for k in EFFECTS})
                pk = input("Key: ").strip().lower()
                if pk in EFFECTS:
                    _adjust_params(pk)
            elif key == '+':
                _change_volume(+0.1)

            elif key == '-':
                _change_volume(-0.1)

            elif key == 'i':
                _print_status()

            elif key == 's':
                stream.stop()
                active_effects.clear()
                mixer._tracks.clear()
                mixer._mic_enabled = False
                prompt_input_source()
                stream.start()

            elif key == 'f':  # Track-FX
                _track_fx_menu()

            elif key == 'v':  # Track-Volume
                _track_volume_menu()

            elif key == '?':
                _print_help()

            elif key == 'o':  # s-olo
                mixer.list_tracks()
                idx = input("Track Index für Solo (Enter = aufheben): ").strip()
                if idx.isdigit():
                    mixer.solo_track(int(idx))
                else:
                    mixer._solo_index = None
                    print("Solo aufgehoben.")

            elif key == 'm':  # mute
                mixer.list_tracks()
                idx = input("Track Index für Mute: ").strip()
                if idx.isdigit():
                    mixer.mute_track(int(idx))
            else:
                print("Unbekannt. [?] für Hilfe.")

    print("Tschüss!")