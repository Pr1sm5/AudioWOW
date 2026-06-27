"""
visualizer/spectrum.py

Berechnungsmodul für FFT-Spektrum und Waveform-Analyse.
Kann von pygame_app, tkinter app oder standalone genutzt werden.

Standalone starten:
    python -m visualizer.spectrum
"""

import numpy as np

# ── Konfiguration ─────────────────────────────────────────────────────────────
SAMPLERATE = 44100
BLOCKSIZE  = 2048    # Höher = bessere Frequenzauflösung, aber träger
MAX_FREQ   = 8000    # Maximale angezeigte Frequenz in Hz

# ── Interner State ────────────────────────────────────────────────────────────
_smoothed: np.ndarray | None = None
_smooth_factor = 0.75   # 0.0 = kein Smoothing, 1.0 = eingefroren


def set_smooth_factor(value: float) -> None:
    """Smoothing-Stärke einstellen. 0.0 = reaktiv, 0.9 = sehr träge."""
    global _smooth_factor
    _smooth_factor = max(0.0, min(0.99, value))


def reset() -> None:
    """Smoothing-Buffer zurücksetzen (z.B. bei Quellenwechsel)."""
    global _smoothed
    _smoothed = None


# ── Kern-Berechnungen ─────────────────────────────────────────────────────────

def compute_spectrum(
    signal: np.ndarray,
    samplerate: int = SAMPLERATE,
    max_freq: int = MAX_FREQ,
    smooth: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Berechnet das FFT-Spektrum eines Audio-Signals.

    Returns:
        frequencies: Frequenz-Achse in Hz
        magnitudes:  Amplitude in dB (geglättet, >= 0)

    Verwendung in pygame:
        freqs, mags = compute_spectrum(signal)
        # freqs und mags haben dieselbe Länge → direkt plotten/zeichnen
    """
    global _smoothed

    n = len(signal)
    if n < 64:
        empty = np.zeros(1, dtype='float32')
        return empty, empty

    # Hann-Fenster gegen Spectral Leakage
    window   = np.hanning(n)
    windowed = signal * window

    # Reelle FFT (reicht für reelle Audiosignale)
    fft_mag = np.abs(np.fft.rfft(windowed))

    # dB-Skalierung — log(0) vermeiden mit 1e-5 Offset
    db = 20.0 * np.log10(fft_mag + 1e-5)
    db = np.maximum(0.0, db)  # Negative Werte abschneiden

    # Smoothing (exponentieller gleitender Durchschnitt)
    if smooth:
        if _smoothed is None or len(_smoothed) != len(db):
            _smoothed = db.copy()
        else:
            _smoothed = _smooth_factor * _smoothed + (1.0 - _smooth_factor) * db
        result = _smoothed
    else:
        result = db

    # Frequenz-Achse berechnen und auf max_freq begrenzen
    freqs   = np.fft.rfftfreq(n, d=1.0 / samplerate)
    max_idx = int(np.searchsorted(freqs, max_freq)) + 1
    max_idx = min(max_idx, len(freqs))

    return freqs[:max_idx].astype('float32'), result[:max_idx].astype('float32')


def compute_waveform(
    signal: np.ndarray,
    n_points: int = 512,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Downsampled das Signal auf n_points für die Waveform-Darstellung.

    Returns:
        t:       Zeitachse in Millisekunden
        samples: Amplitude-Werte (-1.0 bis 1.0)

    Verwendung in pygame:
        t_ms, samples = compute_waveform(signal, n_points=rect_width)
    """
    n = len(signal)
    if n < 2:
        return np.zeros(1, dtype='float32'), np.zeros(1, dtype='float32')

    # Auf n_points downsamplen
    indices = np.linspace(0, n - 1, min(n_points, n), dtype=int)
    samples = signal[indices].astype('float32')

    # Zeitachse in Millisekunden
    t_ms = (indices / SAMPLERATE * 1000.0).astype('float32')

    return t_ms, samples


def peak_amplitude(signal: np.ndarray) -> float:
    """Gibt den Spitzenwert des Signals zurück (0.0 - 1.0+)."""
    if signal.size == 0:
        return 0.0
    return float(np.max(np.abs(signal)))


def dominant_frequency(
    signal: np.ndarray,
    samplerate: int = SAMPLERATE,
) -> float:
    """Gibt die dominante Frequenz im Signal zurück (in Hz)."""
    if len(signal) < 64:
        return 0.0

    windowed = signal * np.hanning(len(signal))
    fft_mag  = np.abs(np.fft.rfft(windowed))
    freqs    = np.fft.rfftfreq(len(signal), d=1.0 / samplerate)

    # DC-Anteil ignorieren (Index 0)
    dominant_idx = np.argmax(fft_mag[1:]) + 1
    return float(freqs[dominant_idx])


# ── Standalone matplotlib Runner ──────────────────────────────────────────────

def _run_standalone() -> None:
    """
    Startet einen eigenständigen Echtzeit-Spektrum-Analyzer mit matplotlib.
    Nutzt processor.get_latest_signal() falls verfügbar,
    sonst eigenen Mic-InputStream.
    """
    import sounddevice as sd
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation

    print("=== DASP Echtzeit Spektrum-Analyzer ===")
    print("Strg+C oder Fenster schließen zum Beenden.\n")

    # Versuche processor-Buffer zu nutzen, sonst eigener Mic-Stream
    try:
        from audio.processor import get_latest_signal
        _get_signal = get_latest_signal
        _stream     = None
        print("Nutze processor-Signal (WAV / Sine / Mic)")
    except ImportError:
        _buffer = np.zeros(BLOCKSIZE, dtype='float32')

        def _mic_callback(indata, frames, time, status):
            nonlocal _buffer
            if status:
                print(status)
            _buffer = indata[:, 0].copy()

        _stream = sd.InputStream(
            samplerate=SAMPLERATE,
            blocksize=BLOCKSIZE,
            channels=1,
            callback=_mic_callback,
        )
        _get_signal = lambda: _buffer
        print("Nutze Mikrofon-Input (processor nicht gefunden)")

    # Matplotlib Setup
    fig, (ax_spec, ax_wave) = plt.subplots(2, 1, figsize=(10, 6))
    fig.canvas.manager.set_window_title('DASP Spectrum Analyzer')
    fig.tight_layout(pad=2.5)

    # Spektrum-Plot
    ax_spec.set_xlim(0, MAX_FREQ)
    ax_spec.set_ylim(0, 80)
    ax_spec.set_xlabel('Frequenz (Hz)')
    ax_spec.set_ylabel('Amplitude (dB)')
    ax_spec.set_title('Frequenzspektrum (FFT)')
    ax_spec.grid(True, linestyle='--', alpha=0.5)
    line_spec, = ax_spec.plot([], [], color='#1f77b4', lw=1.5)

    # Waveform-Plot
    t_axis = np.linspace(0, BLOCKSIZE / SAMPLERATE * 1000, 512)
    ax_wave.set_xlim(0, t_axis[-1])
    ax_wave.set_ylim(-1.1, 1.1)
    ax_wave.set_xlabel('Zeit (ms)')
    ax_wave.set_ylabel('Amplitude')
    ax_wave.set_title('Waveform')
    ax_wave.grid(True, linestyle='--', alpha=0.5)
    ax_wave.axhline(0, color='#aaaaaa', lw=0.8)
    line_wave, = ax_wave.plot([], [], color='#e05c00', lw=1.0)

    def update(_frame):
        signal = _get_signal()

        # Spektrum
        freqs, mags = compute_spectrum(signal, smooth=True)
        if len(freqs) > 1:
            line_spec.set_data(freqs, mags)

        # Waveform
        t_ms, samples = compute_waveform(signal, n_points=512)
        if len(t_ms) > 1:
            line_wave.set_data(t_ms, samples)

        # Dominante Frequenz im Titel anzeigen
        dom_freq = dominant_frequency(signal)
        peak     = peak_amplitude(signal)
        ax_spec.set_title(f'Frequenzspektrum (FFT) — Peak: {peak:.2f} | Dominant: {dom_freq:.1f} Hz')

        return line_spec, line_wave

    if _stream:
        with _stream:
            ani = FuncAnimation(fig, update, interval=30, blit=True, cache_frame_data=False)
            plt.show()
    else:
        ani = FuncAnimation(fig, update, interval=30, blit=True, cache_frame_data=False)
        plt.show()


if __name__ == "__main__":
    _run_standalone()