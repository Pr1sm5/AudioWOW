from audio.processor import load_file, start_stream, active_effects
from effects.lowpass import apply_lowpass
from effects.reverb import apply_reverb


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

    print("Tschüss!")


def _toggle(effect_fn, name: str):
    if effect_fn in active_effects:
        active_effects.remove(effect_fn)
        print(f"{name}: OFF")
    else:
        active_effects.append(effect_fn)
        print(f"{name}: ON")


if __name__ == "__main__":
    main()