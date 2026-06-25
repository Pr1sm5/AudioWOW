import numpy as np
from audio.processor import load_file, enable_mic, start_stream, active_effects, set_volume
from audio.input_handler import get_microphone_devices
from effects.reverb     import apply_reverb,    reset as reset_reverb
from effects.delay      import apply_delay,     reset_delay
from effects.lowpass    import apply_lowpass,   reset_lowpass
from effects.highpass   import apply_highpass,  reset_highpass
from effects.distortion import apply_distortion, reset_distortion
from audio.processor import load_file, load_audio_data, enable_mic, start_stream, active_effects, set_volume

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


def prompt_input_source() -> None:
    """Fragt den User nach einer Audioquelle. Läuft bis eine gültige Wahl getroffen wurde."""
    while True:
        print("\nInput-Quelle wählen:")
        print("  [1] WAV-Datei")
        print("  [2] Sinuswelle")
        print("  [3] Mikrofon")

        choice = input("Auswahl: ").strip()

        if choice == '1':
            filepath = input("Pfad zur WAV-Datei: ").strip()
            load_file(filepath)
            break

        elif choice == '2':
            try:
                freq = input("Frequenz Hz (Enter = 440): ").strip()
                freq = float(freq) if freq else 440.0
                dur  = input("Dauer Sekunden (Enter = 5): ").strip()
                dur  = float(dur) if dur else 5.0
                load_audio_data(_generate_sine(freq, dur))
                print(f"Sinuswelle: {freq} Hz, {dur} s")
                break
            except ValueError:
                print("Ungültige Eingabe.")

        elif choice == '3':
            devices = get_microphone_devices()
            if not devices:
                print("Kein Mikrofon gefunden!")
                continue
            print("\nVerfügbare Mikrofone:")
            for i, d in enumerate(devices):
                print(f"  [{i}] {d['name']} (Index: {d['index']})")
            idx = input("Gerät (Enter = Standard): ").strip()
            device_index = devices[int(idx)]['index'] if idx else None
            enable_mic(device_index)
            break

        else:
            print("Bitte 1, 2 oder 3 eingeben.")


# ─── Effekt Parameter ─────────────────────────────────────────────────────────

def _adjust_params(key: str) -> None:
    """Parameter-Eingabe für einstellbare Effekte."""
    try:
        if key == 'r':
            print("  Reverb hat keine einstellbaren Parameter.")

        elif key == 'd':
            from effects.delay import set_delay, set_feedback
            sec = input("  Delay-Zeit Sekunden (Enter = 0.3): ").strip()
            set_delay(float(sec) if sec else 0.3)
            fb = input("  Feedback 0.0-0.9 (Enter = 0.4): ").strip()
            set_feedback(float(fb) if fb else 0.4)

        elif key == 'l':
            from effects.lowpass import set_cutoff
            freq = input("  Cutoff Hz (Enter = 1000): ").strip()
            set_cutoff(float(freq) if freq else 1000.0)

        elif key == 'h':
            from effects.highpass import set_cutoff
            freq = input("  Cutoff Hz (Enter = 500): ").strip()
            set_cutoff(float(freq) if freq else 500.0)

        elif key == 'x':
            from effects.distortion import set_drive, set_level
            drive = input("  Drive 1.0-20.0 (Enter = 3.0): ").strip()
            set_drive(float(drive) if drive else 3.0)
            level = input("  Level 0.0-1.0 (Enter = 0.7): ").strip()
            set_level(float(level) if level else 0.7)

    except ValueError:
        print("  Ungültige Eingabe, Standardwert beibehalten.")


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
║  [i]  Status  [s]  Quelle wählen ║
║  [?]  Hilfe   [q]  Beenden       ║
╚══════════════════════════════════╝""")


def _print_status() -> None:
    active_names = [EFFECTS[k][0] for k in EFFECTS if EFFECTS[k][1] in active_effects]
    status = ', '.join(active_names) if active_names else 'keine'
    print(f"Volume: {int(_current_volume * 100)}% | Effekte: {status}")


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
                prompt_input_source()
                stream.start()
            elif key == '?':
                _print_help()
            else:
                print("Unbekannt. [?] für Hilfe.")

    print("Tschüss!")