import numpy as np
import msvcrt
import sys
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


# ─── Live Key Input ───────────────────────────────────────────────────────────

def _get_key() -> str:
    """Liest einen Tastendruck ohne Enter. Windows only (msvcrt)."""
    key = msvcrt.getch()

    # Sondertasten (Pfeile etc.) senden zwei Bytes: b'\xe0' + Keycode
    if key in (b'\xe0', b'\x00'):
        key2 = msvcrt.getch()
        return f"special_{key2.hex()}"

    try:
        return key.decode('utf-8').lower()
    except UnicodeDecodeError:
        return ''


# ─── Input Quellen (brauchen weiterhin Enter) ─────────────────────────────────

def _generate_sine(frequency: float, duration: float, samplerate: int = 44100) -> np.ndarray:
    t = np.linspace(0, duration, int(samplerate * duration), endpoint=False)
    return np.sin(2 * np.pi * frequency * t).astype('float32')


def _add_source() -> None:
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


def prompt_input_source() -> None:
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
            idx = input("Track Index: ").strip()
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


# ─── Effekt Parameter (brauchen weiterhin Enter) ──────────────────────────────

def _adjust_params(key: str) -> None:
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
        print("  Ungültige Eingabe.")


# ─── Toggle & Volume ──────────────────────────────────────────────────────────

def _toggle(key: str) -> None:
    name, effect_fn, reset_fn = EFFECTS[key]
    if effect_fn in active_effects:
        active_effects.remove(effect_fn)
        if reset_fn:
            reset_fn()
        print(f"\n{name}: OFF")
    else:
        active_effects.append(effect_fn)
        print(f"\n{name}: ON")
        _adjust_params(key)


def _change_volume(delta: float) -> None:
    global _current_volume
    _current_volume = max(0.0, min(2.0, _current_volume + delta))
    set_volume(_current_volume)
    print(f"\rVolume: {int(_current_volume * 100)}%  ", end='', flush=True)


# ─── Anzeige ──────────────────────────────────────────────────────────────────

def _print_help() -> None:
    print("""
╔══════════════════════════════════╗
║       DASP Live Audio FX         ║
╠══════════════════════════════════╣
║  EFFEKTE       STEUERUNG         ║
║  [r] Reverb    [+] Lauter        ║
║  [d] Delay     [-] Leiser        ║
║  [l] Lowpass   [o] Solo          ║
║  [h] Highpass  [m] Mute          ║
║  [x] Distort   [i] Status        ║
║                [s] Quellen       ║
║  [p] Parameter [q] Beenden       ║
╚══════════════════════════════════╝
Taste drücken — kein Enter nötig!
""")


def _print_status() -> None:
    print()
    active_names = [EFFECTS[k][0] for k in EFFECTS if EFFECTS[k][1] in active_effects]
    status = ', '.join(active_names) if active_names else 'keine'
    print(f"Volume: {int(_current_volume * 100)}% | Effekte: {status}")
    mixer.list_tracks()
    print()


# ─── Haupt-Loop ───────────────────────────────────────────────────────────────

def run() -> None:
    prompt_input_source()
    stream = start_stream()

    with stream:
        _print_help()

        while True:
            key = _get_key()

            if key == 'q':
                break

            elif key in EFFECTS:
                _toggle(key)

            elif key == 'p':
                print("\nEffekt wählen:", {k: EFFECTS[k][0] for k in EFFECTS})
                pk = input("Key: ").strip().lower()
                if pk in EFFECTS:
                    _adjust_params(pk)

            elif key == '+':
                _change_volume(+0.1)
            elif key == '-':
                _change_volume(-0.1)

            elif key == 'i':
                _print_status()

            elif key == 'o':
                _print_status()
                idx = input("Solo Track Index (Enter = aufheben): ").strip()
                if idx.isdigit():
                    mixer.solo_track(int(idx))
                else:
                    mixer._solo_index = None
                    print("Solo aufgehoben.")

            elif key == 'm':
                _print_status()
                idx = input("Mute Track Index: ").strip()
                if idx.isdigit():
                    mixer.mute_track(int(idx))

            elif key == 's':
                stream.stop()
                active_effects.clear()
                mixer._tracks.clear()
                mixer._mic_enabled = False
                prompt_input_source()
                stream.start()
                _print_help()

            elif key == '?':
                _print_help()

    print("\nTschüss!")