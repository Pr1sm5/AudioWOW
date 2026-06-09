from audio.processor import load_file, start_stream, active_effects, set_volume
from effects.lowpass import apply_lowpass
from effects.reverb import apply_reverb, reset


_current_volume = 1.0

def _change_volume(delta: float):
    global _current_volume
    _current_volume = max(0.0, min(2.0, _current_volume + delta))
    set_volume(_current_volume)


def main():
    print("=== DASP Live Audio FX ===")

    filepath = input("WAV-Datei Pfad: ").strip()
    load_file(filepath)

    stream = start_stream()

    with stream:
        print("\nKeybinds:")
        print("  [l] Lowpass toggle")
        print("  [r] Reverb toggle")
        print("  [q] Beenden\n")

        while True:
            key = input("> ").strip().lower()

            if key == 'q':
                break
            elif key == 'l':
               _toggle(apply_lowpass, "Lowpass")
            elif key == 'r':
               _toggle(apply_reverb, "Reverb")
            elif key == '+':
               _change_volume(+0.1)
            elif key == '-':
                _change_volume(-0.1)

    print("Tschüss!")


def _toggle(effect_fn, name: str):
    if effect_fn in active_effects:
        reset()
        active_effects.remove(effect_fn)
        print(f"{name}: OFF")
    else:
        active_effects.append(effect_fn)
        print(f"{name}: ON")


if __name__ == "__main__":
    main()