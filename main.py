import numpy as np
from audio.processor import load_file, enable_mic, start_stream, active_effects, set_volume
from effects.reverb import apply_reverb, reset as reset_reverb
from audio.input_handler import get_microphone_devices
from audio import mixer

_current_volume = 1.0


def generate_sine_wave(frequency: float = 440.0, duration: float = 5.0, samplerate: int = 44100) -> np.ndarray:
    t = np.linspace(0, duration, int(samplerate * duration), endpoint=False)
    return np.sin(2 * np.pi * frequency * t).astype('float32')


# Beim Start mehrere Quellen laden:
def choose_input_source():
    while True:
        print("\nWas hinzufügen?")
        print("  [1] WAV-Datei")
        print("  [2] Sinuswelle")
        print("  [3] Mikrofon")
        print("  [4] Track entfernen")
        print("  [5] Tracks anzeigen")
        print("  [d] Fertig / Starten")

        choice = input("Auswahl: ").strip().lower()

        if choice == '1':
            filepath = input("WAV-Datei Pfad: ").strip()
            vol = input("Volume 0.0-2.0 (Enter = 1.0): ").strip()
            vol = float(vol) if vol else 1.0
            load_file(filepath, volume=vol)

        elif choice == '2':
            freq = input("Frequenz Hz (Enter = 440): ").strip()
            freq = float(freq) if freq else 440.0
            dur = input("Dauer Sekunden (Enter = 5): ").strip()
            dur = float(dur) if dur else 5.0
            wave = generate_sine_wave(freq, dur)
            mixer.add_track(wave, name=f"Sine {freq}Hz", volume=1.0)

        elif choice == '3':
            devices = get_microphone_devices()
            for i, d in enumerate(devices):
                print(f"  [{i}] {d['name']} (Index: {d['index']})")
            idx = input("Gerät (Enter = Standard): ").strip()
            device_index = devices[int(idx)]['index'] if idx else None
            vol = input("Mic Volume (Enter = 1.0): ").strip()
            vol = float(vol) if vol else 1.0
            enable_mic(device_index, volume=vol)

        elif choice == '4':
            mixer.list_tracks()
            idx = input("Track Index zum Entfernen: ").strip()
            mixer.remove_track(int(idx))

        elif choice == '5':
            mixer.list_tracks()

        elif choice == 'd':
            if not mixer._tracks and not mixer._mic_enabled:
                print("Mindestens eine Quelle hinzufügen!")
            else:
                break


def main():
    print("=== DASP Live Audio FX ===")

    choose_input_source()
    stream = start_stream()

    with stream:
        print("\nKeybinds:")
        print("  [r]   Reverb toggle")
        print("  [+]   Lauter")
        print("  [-]   Leiser")
        print("  [s]   Neue Quelle wählen")
        print("  [q]   Beenden\n")

        while True:
            key = input("> ").strip().lower()

            if key == 'q':
                break
            elif key == 'r':
                _toggle(apply_reverb, "Reverb")
            elif key == '+':
                _change_volume(+0.1)
            elif key == '-':
                _change_volume(-0.1)
            elif key == 's':
                stream.stop()
                active_effects.clear()
                choose_input_source()
                stream.start()

    print("Tschüss!")


def _toggle(effect_fn, name: str):
    if effect_fn in active_effects:
        active_effects.remove(effect_fn)
        if effect_fn == apply_reverb:
            reset_reverb()
        print(f"{name}: OFF")
    else:
        active_effects.append(effect_fn)
        print(f"{name}: ON")


def _change_volume(delta: float):
    global _current_volume
    _current_volume = max(0.0, min(2.0, _current_volume + delta))
    set_volume(_current_volume)


if __name__ == "__main__":
    main()

