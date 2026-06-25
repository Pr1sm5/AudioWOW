import numpy as np
from audio.processor import load_file, load_audio_data, enable_mic, start_stream, active_effects, set_volume
from audio.input_handler import get_microphone_devices
from effects.reverb      import apply_reverb,     reset as reset_reverb
from effects.delay       import apply_delay,       reset as reset_delay,  set_delay, set_feedback
from effects.lowpass     import apply_lowpass,     set_cutoff as lp_cutoff
from effects.highpass    import apply_highpass,    set_cutoff as hp_cutoff
from effects.distortion  import apply_distortion,  set_drive, set_level

_current_volume = 1.0

# Effekt-Registrierung: key → (name, funktion, reset_funktion oder None)
EFFECTS = {
    'r': ("Reverb",      apply_reverb,     reset_reverb),
    'd': ("Delay",       apply_delay,      reset_delay),
    'l': ("Lowpass",     apply_lowpass,    None),
    'h': ("Highpass",    apply_highpass,   None),
    'x': ("Distortion",  apply_distortion, None),
}


# ─── Audio Quellen ────────────────────────────────────────────────────────────

def generate_sine_wave(frequency: float = 440.0, duration: float = 5.0, samplerate: int = 44100) -> np.ndarray:
    t = np.linspace(0, duration, int(samplerate * duration), endpoint=False)
    return np.sin(2 * np.pi * frequency * t).astype('float32')


def choose_input_source() -> None:
    print("\nInput-Quelle wählen:")
    print("  [1] Audio-Datei (WAV)")
    print("  [2] Sinuswelle")
    print("  [3] Mikrofon")

    while True:
        choice = input("Auswahl (1/2/3): ").strip()

        if choice == '1':
            filepath = input("WAV-Datei Pfad: ").strip()
            load_file(filepath)
            break

        elif choice == '2':
            try:
                freq = input("Frequenz in Hz (Enter = 440Hz): ").strip()
                freq = float(freq) if freq else 440.0
                dur  = input("Dauer in Sekunden (Enter = 5s): ").strip()
                dur  = float(dur)  if dur  else 5.0
                load_audio_data(generate_sine_wave(freq, dur))
                print(f"Sinuswelle: {freq}Hz, {dur}s")
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
            idx = input("Gerät wählen (Enter = Standard): ").strip()
            device_index = devices[int(idx)]['index'] if idx else None
            enable_mic(device_index)
            break

        else:
            print("Bitte 1, 2 oder 3 eingeben.")


# ─── Effekt Parameter ─────────────────────────────────────────────────────────

def adjust_effect_params(key: str):
    """Zeigt Parameter-Menü für Effekte die einstellbar sind."""
    if key == 'r':
        print("Reverb hat keine einstellbaren Parameter in dieser Version.")

    elif key == 'd':
        try:
            sec = input(f"  Delay-Zeit in Sekunden (Enter = 0.3): ").strip()
            set_delay(float(sec) if sec else 0.3)
            fb = input(f"  Feedback 0.0-0.9 (Enter = 0.4): ").strip()
            set_feedback(float(fb) if fb else 0.4)
        except ValueError:
            print("Ungültige Eingabe.")

    elif key == 'l':
        try:
            freq = input(f"  Lowpass Cutoff Hz (Enter = 1000): ").strip()
            lp_cutoff(float(freq) if freq else 1000.0)
        except ValueError:
            print("Ungültige Eingabe.")

    elif key == 'h':
        try:
            freq = input(f"  Highpass Cutoff Hz (Enter = 500): ").strip()
            hp_cutoff(float(freq) if freq else 500.0)
        except ValueError:
            print("Ungültige Eingabe.")

    elif key == 'x':
        try:
            drive = input(f"  Drive 1.0-20.0 (Enter = 3.0): ").strip()
            set_drive(float(drive) if drive else 3.0)
            level = input(f"  Level 0.0-1.0 (Enter = 0.7): ").strip()
            set_level(float(level) if level else 0.7)
        except ValueError:
            print("Ungültige Eingabe.")


# ─── Hilfsfunktionen ──────────────────────────────────────────────────────────

def _toggle(key: str):
    name, effect_fn, reset_fn = EFFECTS[key]
    if effect_fn in active_effects:
        active_effects.remove(effect_fn)
        if reset_fn:
            reset_fn()
        print(f"{name}: OFF")
    else:
        active_effects.append(effect_fn)
        print(f"{name}: ON")
        adjust_effect_params(key)  # Parameter direkt beim Einschalten abfragen


def _change_volume(delta: float):
    global _current_volume
    _current_volume = max(0.0, min(2.0, _current_volume + delta))
    set_volume(_current_volume)


def _print_status():
    active_names = [EFFECTS[k][0] for k in EFFECTS if EFFECTS[k][1] in active_effects]
    print(f"\nVolume: {int(_current_volume * 100)}% | Aktive Effekte: {', '.join(active_names) if active_names else 'keine'}")


def _print_help():
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
║  [+]  Lauter                     ║
║  [-]  Leiser                     ║
║  [i]  Status anzeigen            ║
║  [s]  Neue Quelle wählen         ║
║  [q]  Beenden                    ║
╚══════════════════════════════════╝""")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=== DASP Live Audio FX ===")
    choose_input_source()

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
                print("Welchen Effekt anpassen?", {k: EFFECTS[k][0] for k in EFFECTS})
                pk = input("Key: ").strip().lower()
                if pk in EFFECTS:
                    adjust_effect_params(pk)

            elif key == '+':
                _change_volume(+0.1)
            elif key == '-':
                _change_volume(-0.1)

            elif key == 'i':
                _print_status()

            elif key == 's':
                stream.stop()
                active_effects.clear()
                choose_input_source()
                stream.start()

            elif key == '?':
                _print_help()

            else:
                print("Unbekannter Befehl. [?] für Hilfe.")

    print("Tschüss!")


if __name__ == "__main__":
    main()