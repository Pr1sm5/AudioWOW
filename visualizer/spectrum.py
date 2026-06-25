import numpy as np
import sounddevice as sd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# --- Konfiguration ---
SAMPLERATE = 44100  # Abtastrate in Hz
BLOCKSIZE = 2048    # Blockgröße (höher = bessere Frequenzauflösung, aber träger)
MAX_FREQ = 8000     # Maximale angezeigte Frequenz in Hz (menschliche Stimme/Musik Kernbereich)

# Globale Variable für den aktuellen Audio-Block
audio_buffer = np.zeros(BLOCKSIZE, dtype='float32')

def audio_callback(indata, frames, time, status):
    """Wird vom Audio-Stream aufgerufen, wenn neue Daten bereitstehen."""
    global audio_buffer
    if status:
        print(status)
    # Nutze den ersten Kanal (Mono) und kopiere die Daten in den Buffer
    audio_buffer = indata[:, 0]

def main():
    print("=== Echtzeit Audio-Spektrum ===")
    print("Drücke [Strg + C] im Terminal oder schließe das Fenster zum Beenden.")

    # Berechne die Frequenz-Achse für die FFT
    # rfftfreq liefert die passenden Frequenzen für reelle Signale
    frequencies = np.fft.rfftfreq(BLOCKSIZE, d=1/SAMPLERATE)
    
    # Finde den Index, bis zu dem wir Frequenzen anzeigen wollen (z.B. bis 8kHz)
    max_freq_idx = np.where(frequencies <= MAX_FREQ)[0][-1]
    plot_frequencies = frequencies[:max_freq_idx]

    # Matplotlib Setup
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.canvas.manager.set_window_title('DASP Real-Time Spectrum Analyzer')
    
    # Erstelle eine leere Linie, die wir im Loop aktualisieren
    line, = ax.plot(plot_frequencies, np.zeros(len(plot_frequencies)), color='#1f77b4', lw=1.5)
    
    # Achsen-Styling
    ax.set_xlim(0, MAX_FREQ)
    ax.set_ylim(0, 50)  # Skalierung der Amplitude (ggf. anpassen je nach Mikrofon-Pegel)
    ax.set_xlabel('Frequenz (Hz)')
    ax.set_ylabel('Amplitude (dB / Magnitudo)')
    ax.set_title('Echtzeit Frequenzspektrum')
    ax.grid(True, linestyle='--', alpha=0.6)

    def update_plot(frame):
        """Aktualisiert die Linie im Diagramm."""
        global audio_buffer
        
        # FFT berechnen (Reelle FFT reicht für Audio)
        # Anwendung eines Hann-Fensters verhindert "Spectral Leakage" (Frequenz-Schmieren)
        windowed_signal = audio_buffer * np.hanning(BLOCKSIZE)
        fft_data = np.abs(np.fft.rfft(windowed_signal))
        
        # Umrechnung in eine grobe dB-ähnliche Skalierung für bessere Sichtbarkeit
        # Vermeidet log(0) durch Addition von 1e-5
        magnitude = 20 * np.log10(fft_data + 1e-5)
        
        # Nur Frequenzen bis MAX_FREQ anwenden (und negative Werte auf 0 setzen)
        plot_magnitude = np.maximum(0, magnitude[:max_freq_idx])

        # Linie aktualisieren
        line.set_ydata(plot_magnitude)
        return line,

    # Starte den Sounddevice InputStream
    stream = sd.InputStream(
        samplerate=SAMPLERATE,
        blocksize=BLOCKSIZE,
        channels=1,
        callback=audio_callback
    )

    with stream:
        # FuncAnimation sorgt für das flüssige Update des Fensters (ca. 30-60 FPS)
        ani = FuncAnimation(fig, update_plot, interval=30, blit=True, cache_frame_data=False)
        plt.show()

if __name__ == "__main__":
    main()