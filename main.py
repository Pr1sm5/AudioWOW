<<<<<<< Updated upstream
=======
import numpy as np
from audio.processor import load_file, load_audio_data, enable_mic, start_stream, active_effects, set_volume
from effects.reverb import apply_reverb, reset as reset_reverb
from audio.input_handler import get_microphone_devices

_current_volume = 1.0


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
                dur = input("Dauer in Sekunden (Enter = 5s): ").strip()
                dur = float(dur) if dur else 5.0
                wave = generate_sine_wave(frequency=freq, duration=dur)
                load_audio_data(wave, samplerate=44100)
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

            if idx:
                device_index = devices[int(idx)]['index']  # ← echter sd-Index
            else:
                device_index = None

            enable_mic(device_index)
            break

        else:
            print("Bitte 1, 2 oder 3 eingeben.")


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
>>>>>>> Stashed changes
