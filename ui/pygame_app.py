import os
import tkinter as tk
from tkinter import filedialog

import numpy as np

from audio.input_handler import get_microphone_devices
from audio import mixer
from audio.processor import (
    active_effects,
    clear_sources,
    enable_mic,
    get_latest_signal,
    load_audio_data,
    load_file,
    set_volume,
    start_stream,
)

from effects.distortion import apply_distortion, reset_distortion, set_drive, set_level
from effects.highpass import apply_highpass, reset_highpass
from effects.highpass import set_cutoff as set_highpass_cutoff
from effects.lowpass import apply_lowpass, reset_lowpass
from effects.lowpass import set_cutoff as set_lowpass_cutoff
from visualizer.spectrum import compute_spectrum, compute_waveform, peak_amplitude, dominant_frequency, reset as reset_spectrum
from effects.reverb import apply_reverb, reset as reset_reverb, set_mix as set_reverb_mix
from effects.reverb import set_dry as set_reverb_dry, set_wet as set_reverb_wet  # ← neu
from effects.delay  import apply_delay, reset_delay, set_delay, set_feedback
from effects.delay  import set_dry as set_delay_dry, set_wet as set_delay_wet    # ← neu


WIDTH  = 1180
HEIGHT = 1120
FPS = 60

COLORS = {
    "bg": (14, 16, 20),
    "panel": (29, 34, 42),
    "panel_2": (38, 45, 54),
    "text": (235, 241, 245),
    "muted": (140, 154, 164),
    "line": (71, 84, 96),
    "green": (102, 224, 157),
    "cyan": (83, 196, 255),
    "pink": (255, 105, 156),
    "amber": (255, 190, 92),
    "red": (255, 104, 104),
}

EFFECTS = {
    "reverb": ("Reverb", apply_reverb, reset_reverb, COLORS["cyan"]),
    "delay": ("Delay", apply_delay, reset_delay, COLORS["amber"]),
    "lowpass": ("Lowpass", apply_lowpass, reset_lowpass, COLORS["green"]),
    "highpass": ("Highpass", apply_highpass, reset_highpass, COLORS["pink"]),
    "distortion": ("Distort", apply_distortion, reset_distortion, COLORS["red"]),
}

TRACK_FX_SLIDERS = [
    ("reverb",     "dry",      "Reverb dry",        1.0,     2.0),
    ("reverb",     "wet",      "Reverb wet",        0.0,     1.0),
    ("delay",      "seconds",  "Delay time (s)",    0.01,    2.0),
    ("delay",      "feedback", "Delay feedback",    0.0,     0.9),
    ("delay",      "dry",      "Delay dry",         1.0,     2.0),
    ("delay",      "wet",      "Delay wet",         0.0,     1.0),
    ("lowpass",    "cutoff",   "Lowpass cutoff",    20.0, 20000.0),
    ("highpass",   "cutoff",   "Highpass cutoff",   20.0, 20000.0),
    ("distortion", "drive",    "Distortion drive",  1.0,    40.0),
    ("distortion", "level",    "Distortion level",  0.0,     1.0),
]


class Button:
    """Clickable rectangular button with a pygame callback."""

    def __init__(self, rect, label, action, color=None):
        """Store button geometry, label, action callback, and color."""
        self.rect = pygame.Rect(rect)
        self.label = label
        self.action = action
        self.color = color or COLORS["panel_2"]

    def draw(self, screen, fonts, mouse_pos):
        """Draw the button and its hover state."""
        hovered = self.rect.collidepoint(mouse_pos)
        color = tuple(min(255, channel + 16) for channel in self.color) if hovered else self.color
        pygame.draw.rect(screen, color, self.rect, border_radius=8)
        pygame.draw.rect(screen, COLORS["line"], self.rect, width=1, border_radius=8)
        draw_text(screen, fonts["button"], self.label, self.rect.center, COLORS["text"], center=True)

    def handle_event(self, event):
        """Run the button action when a left click lands inside the rectangle."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.action()
            return True
        return False


class TogglePad:
    """Effect toggle button that keeps an on/off state."""

    def __init__(self, rect, key, label, color, action):
        """Store the effect identity and action callback for this pad."""
        self.rect = pygame.Rect(rect)
        self.key = key
        self.label = label
        self.color = color
        self.action = action
        self.enabled = False

    def draw(self, screen, fonts, mouse_pos):
        """Draw the pad with a lit style when enabled."""
        hovered = self.rect.collidepoint(mouse_pos)
        bg = self.color if self.enabled else COLORS["panel_2"]
        if hovered and not self.enabled:
            bg = tuple(min(255, channel + 18) for channel in bg)
        pygame.draw.rect(screen, bg, self.rect, border_radius=8)
        pygame.draw.rect(screen, self.color, self.rect, width=2, border_radius=8)
        label_color = COLORS["bg"] if self.enabled else COLORS["text"]
        draw_text(screen, fonts["button"], self.label, self.rect.center, label_color, center=True)
        led_rect = pygame.Rect(self.rect.right - 18, self.rect.top + 10, 8, 8)
        pygame.draw.circle(screen, COLORS["bg"] if self.enabled else self.color, led_rect.center, 4)

    def handle_event(self, event):
        """Toggle enabled state and notify the parent UI on click."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.enabled = not self.enabled
            self.action(self.key, self.enabled)
            return True
        return False


class Slider:
    """Horizontal value control used for volume and effect parameters."""

    def __init__(self, rect, label, minimum, maximum, value, setter, value_format=None):
        """Store the slider range, current value, and setter callback."""
        self.rect = pygame.Rect(rect)
        self.label = label
        self.minimum = minimum
        self.maximum = maximum
        self.value = value
        self.setter = setter
        self.value_format = value_format or format_slider_value
        self.dragging = False

    def draw(self, screen, fonts, mouse_pos):
        """Draw the slider track, filled range, knob, label, and value text."""
        if self.label:
            draw_text(screen, fonts["small"], self.label, (self.rect.left, self.rect.top - 18), COLORS["muted"])
        track = pygame.Rect(self.rect.left, self.rect.centery - 3, self.rect.width, 6)
        pygame.draw.rect(screen, COLORS["line"], track, border_radius=3)
        fill = pygame.Rect(track.left, track.top, self._knob_x() - track.left, track.height)
        pygame.draw.rect(screen, COLORS["cyan"], fill, border_radius=3)
        knob_color = COLORS["text"] if self.rect.collidepoint(mouse_pos) or self.dragging else COLORS["cyan"]
        pygame.draw.circle(screen, knob_color, (self._knob_x(), self.rect.centery), 9)
        value_text = self.value_format(self.value)
        if self.label:
            draw_text(screen, fonts["small"], value_text, (self.rect.right, self.rect.top - 18), COLORS["text"], right=True)
        else:
            draw_text(screen, fonts["small"], value_text, (self.rect.right + 52, self.rect.centery - 8), COLORS["text"], right=True)

    def handle_event(self, event):
        """Start, update, or stop dragging based on mouse events."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self._hit_area().collidepoint(event.pos):
            self.dragging = True
            self._set_from_x(event.pos[0])
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        if event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_from_x(event.pos[0])
            return True
        return False

    def _hit_area(self):
        """Return a slightly larger rectangle so the knob is easier to grab."""
        return self.rect.inflate(8, 20)

    def _knob_x(self):
        """Convert the current numeric value into a knob x-coordinate."""
        progress = (self.value - self.minimum) / (self.maximum - self.minimum)
        return int(self.rect.left + progress * self.rect.width)

    def _set_from_x(self, x_pos):
        """Convert mouse x-position into a clamped slider value."""
        progress = max(0.0, min(1.0, (x_pos - self.rect.left) / self.rect.width))
        self.value = self.minimum + progress * (self.maximum - self.minimum)
        self.setter(self.value)


def draw_text(screen, font, text, pos, color, center=False, right=False):
    """Render text at a top-left, centered, or top-right position."""
    surface = font.render(str(text), True, color)
    rect = surface.get_rect()
    if center:
        rect.center = pos
    elif right:
        rect.topright = pos
    else:
        rect.topleft = pos
    screen.blit(surface, rect)


def format_slider_value(value):
    """Format slider values with fewer decimals for larger numbers."""
    if value >= 100:
        return f"{value:.0f}"
    if value >= 10:
        return f"{value:.1f}"
    return f"{value:.2f}"


class AudioWowPygame:
    """Main pygame application that wires controls, streams, tracks, and visualization."""

    def __init__(self):
        """Initialize pygame, UI state, audio state, and all controls."""
        pygame.init()
        pygame.display.set_caption("AudioWOW")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.fonts = {
            "title": pygame.font.SysFont("Segoe UI", 34, bold=True),
            "section": pygame.font.SysFont("Segoe UI", 18, bold=True),
            "button": pygame.font.SysFont("Segoe UI", 16, bold=True),
            "body": pygame.font.SysFont("Segoe UI", 16),
            "small": pygame.font.SysFont("Segoe UI", 13),
        }
        self.stream = None
        self.status = "Ready"
        self.source = "No source selected"
        self.error = ""
        self.phase = 0.0
        self.mic_devices = []
        self.mic_index = 0
        self.sine_freq = 440.0
        self.sine_duration = 5.0
        self.running = True
        self.controls = []
        self.effect_pads = []
        self.track_controls = []
        self.track_snapshot = []
        self.track_effect_pads = []
        self.track_fx_controls = []
        self.track_fx_snapshot = None
        self.selected_track_index = None
        self.viz_mode = "waveform"   # "waveform" | "spectrum"
        reset_spectrum()
        self._refresh_mics(silent=True)
        self._build_controls()

    def _build_controls(self):
        """Create static buttons, global effect pads, and global sliders."""
        self.controls = [
            Button((42, 162, 136, 44), "Add WAV", self._choose_wav, COLORS["cyan"]),
            Button((194, 162, 136, 44), "Add Sine", self._use_sine, COLORS["green"]),
            Button((346, 162, 136, 44), "Mic", self._use_microphone, COLORS["pink"]),
            Button((498, 162, 116, 44), "Refresh", lambda: self._refresh_mics(), COLORS["panel_2"]),
            Button((42, 222, 136, 36), "Next Mic", self._next_mic, COLORS["panel_2"]),
            # In _build_controls, Footer Buttons: y: 982 → 1062
            Button((42, 1062, 116, 40), "Resume", self._resume_stream, COLORS["green"]),
            Button((172, 1062, 102, 40), "Stop", self._stop_stream, COLORS["red"]),
            Button((288, 1062, 132, 40), "Clear FX", self._clear_effects, COLORS["panel_2"]),
            Button((434, 1062, 148, 40), "Clear Sources", self._clear_sources, COLORS["panel_2"]),
            Button((596, 1062, 136, 40), "All Track FX", self._select_all_tracks, COLORS["cyan"]),
            Button((746, 1062, 136, 40), "Waveform/FFT", self._toggle_viz_mode, COLORS["panel_2"]),
        ]

        self.effect_pads = []
        x = 42
        for key, (label, _effect_fn, _reset_fn, color) in EFFECTS.items():
            pad = TogglePad((x, 330, 162, 52), key, label, color, self._toggle_effect)
            self.effect_pads.append(pad)
            x += 184

        self.sliders = [
            Slider((224, 238, 300, 28), "Sine frequency", 20.0, 20000.0, self.sine_freq, self._set_sine_freq),
            Slider((572, 238, 260, 28), "Sine duration", 0.25, 30.0, self.sine_duration, self._set_sine_duration),
            Slider((42, 482, 260, 28), "Master volume", 0.0, 2.0, 1.0, set_volume, lambda v: f"{int(v * 100)}%"),

            # Reverb
            Slider((342, 482, 220, 28), "Reverb dry", 0.0, 1.0, 1.0, set_reverb_dry),
            Slider((582, 482, 220, 28), "Reverb wet", 0.0, 1.0, 0.5, set_reverb_wet),

            # Delay
            Slider((42, 560, 200, 28), "Delay time (s)", 0.01, 2.0, 0.35, set_delay),
            Slider((262, 560, 180, 28), "Delay feedback", 0.0, 0.9, 0.4, set_feedback),
            Slider((462, 560, 180, 28), "Delay dry", 0.0, 1.0, 1.0, set_delay_dry),
            Slider((662, 560, 180, 28), "Delay wet", 0.0, 1.0, 0.5, set_delay_wet),

            # Filter & Distortion
            Slider((862, 560, 180, 28), "Lowpass cutoff", 20.0, 20000.0, 1000.0, set_lowpass_cutoff),
            Slider((42, 638, 260, 28), "Highpass cutoff", 20.0, 20000.0, 500.0, set_highpass_cutoff),
            Slider((342, 638, 240, 28), "Distortion drive", 1.0, 20.0, 8.0, set_drive),
            Slider((622, 638, 240, 28), "Distortion level", 0.0, 1.0, 0.7, set_level),
        ]
        self._sync_track_controls()
        self._sync_track_fx_controls(force=True)

    def run(self):
        """Run the pygame event loop until the window is closed."""
        while self.running:
            mouse_pos = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    self._handle_key(event.key)
                else:
                    self._handle_control_event(event)

            self._draw(mouse_pos)
            pygame.display.flip()
            self.clock.tick(FPS)

        self._stop_stream()
        pygame.quit()

    def _handle_key(self, key):
        """Map keyboard shortcuts to source and playback actions."""
        if key == pygame.K_ESCAPE:
            self.running = False
        elif key == pygame.K_SPACE:
            if self.stream is None:
                self._resume_stream()
            else:
                self._stop_stream()
        elif key == pygame.K_w:
            self._choose_wav()
        elif key == pygame.K_s:
            self._use_sine()
        elif key == pygame.K_m:
            self._use_microphone()

    def _handle_control_event(self, event):
        """Offer one pygame event to controls in priority order."""
        for control in self.controls:
            if control.handle_event(event):
                return
        for pad in self.effect_pads:
            if pad.handle_event(event):
                return
        for slider in self.sliders:
            if slider.handle_event(event):
                return
        for control in self.track_controls:
            if control.handle_event(event):
                return
        for pad in self.track_effect_pads:
            if pad.handle_event(event):
                return
        for control in self.track_fx_controls:
            if control.handle_event(event):
                return

    def _draw(self, mouse_pos):
        """Draw the full application frame."""
        self.screen.fill(COLORS["bg"])
        self._draw_header()
        self._draw_panel((28, 118, 1108, 164), "Sources")
        self._draw_panel((28, 292, 924, 108), "Effects")
        self._draw_panel((28, 420, 1108, 260), "Global Controls")  # h: 180 → 260
        self._draw_panel((28, 700, 1108, 144), "Tracks")  # y: 620 → 700
        self._draw_panel((28, 864, 1108, 190), "Selected Track Effects")  # y: 784 → 864
        self._draw_visualizer()
        self._draw_footer()

        for control in self.controls:
            control.draw(self.screen, self.fonts, mouse_pos)
        for pad in self.effect_pads:
            pad.draw(self.screen, self.fonts, mouse_pos)
        for slider in self.sliders:
            slider.draw(self.screen, self.fonts, mouse_pos)
        self._draw_tracks(mouse_pos)
        self._draw_track_fx(mouse_pos)

    def _draw_header(self):
        """Draw title, status, current source, and error text."""
        draw_text(self.screen, self.fonts["title"], "AudioWOW", (34, 26), COLORS["text"])
        draw_text(self.screen, self.fonts["body"], self.status, (36, 68), COLORS["green"])
        source = self.source
        if len(source) > 86:
            source = source[:83] + "..."
        draw_text(self.screen, self.fonts["small"], source, (36, 92), COLORS["muted"])
        if self.error:
            draw_text(self.screen, self.fonts["small"], self.error, (1136, 92), COLORS["red"], right=True)

    def _draw_panel(self, rect, title):
        """Draw one labelled background panel."""
        panel = pygame.Rect(rect)
        pygame.draw.rect(self.screen, COLORS["panel"], panel, border_radius=12)
        pygame.draw.rect(self.screen, COLORS["line"], panel, width=1, border_radius=12)
        draw_text(self.screen, self.fonts["section"], title, (panel.left + 14, panel.top + 12), COLORS["text"])

    def _draw_visualizer(self):
        """Draw the live waveform or FFT spectrum panel."""
        rect = pygame.Rect(660, 162, 446, 96)
        pygame.draw.rect(self.screen, (10, 12, 16), rect, border_radius=8)
        pygame.draw.rect(self.screen, COLORS["line"], rect, width=1, border_radius=8)

        signal = get_latest_signal()

        if self.viz_mode == "waveform":
            self._draw_waveform(signal, rect)
        else:
            self._draw_spectrum(signal, rect)

        # Modus-Label
        mode_label = "Waveform" if self.viz_mode == "waveform" else "Spectrum (FFT)"
        draw_text(self.screen, self.fonts["small"], mode_label,
                  (rect.right - 12, rect.top + 10), COLORS["amber"], right=True)

    def _draw_waveform(self, signal, rect):
        """Waveform-Darstellung via spectrum.compute_waveform()"""
        left   = rect.left + 10
        right  = rect.right - 10
        top    = rect.top + 24
        bottom = rect.bottom - 8
        width  = right - left
        height = bottom - top

        peak = peak_amplitude(signal)

        t_ms, samples = compute_waveform(signal, n_points=width)

        if len(samples) > 1:
            center_y  = top + height / 2
            amplitude = height * 0.45
            points = [
                (left + int(i * width / len(samples)),
                 int(center_y - float(s) * amplitude))
                for i, s in enumerate(samples)
            ]
            pygame.draw.lines(self.screen, COLORS["cyan"], False, points, 2)
        else:
            pygame.draw.line(self.screen, COLORS["line"],
                             (left, rect.centery), (right, rect.centery), 1)

        draw_text(self.screen, self.fonts["small"], "Live signal",
                  (rect.left + 12, rect.top + 10), COLORS["muted"])
        draw_text(self.screen, self.fonts["small"], f"Peak {peak:.2f}",
                  (rect.right - 12, rect.bottom - 20), COLORS["muted"], right=True)

    def _draw_spectrum(self, signal, rect):
        left = rect.left + 10
        right = rect.right - 10
        top = rect.top + 24
        bottom = rect.bottom - 8
        width = right - left
        height = bottom - top

        freqs, mags = compute_spectrum(signal, smooth=True)

        if len(mags) < 2:
            draw_text(self.screen, self.fonts["small"], "No signal",
                      (rect.left + 12, rect.top + 10), COLORS["muted"])
            return

        db_max = float(np.max(mags))
        # Kein Signal → nichts zeichnen statt durch 1.0 zu dividieren
        if db_max < 0.5:
            draw_text(self.screen, self.fonts["small"], "No signal",
                      (rect.left + 12, rect.top + 10), COLORS["muted"])
            return

        n_bars = min(width, 200)  # Feste Anzahl Balken, unabhängig von len(mags)
        bar_w = max(1, width // n_bars)
        n_bars = width // bar_w  # Anpassen an tatsächliche Breite

        indices = np.linspace(0, len(mags) - 1, n_bars, dtype=int)
        for i, idx in enumerate(indices):
            val = float(mags[idx])
            bar_h = max(1, int((val / db_max) * height))
            x = left + i * bar_w

            t = val / db_max
            if t < 0.5:
                color = (int(t * 2 * 200), 200, 80)
            else:
                color = (200, int((1.0 - t) * 2 * 200), 40)

            pygame.draw.rect(self.screen, color,
                             pygame.Rect(x, bottom - bar_h, bar_w - 1, bar_h))

        dom = dominant_frequency(signal)
        draw_text(self.screen, self.fonts["small"], f"0 Hz",
                  (left, bottom + 2), COLORS["muted"])
        draw_text(self.screen, self.fonts["small"], f"8k Hz",
                  (right, bottom + 2), COLORS["muted"], right=True)
        draw_text(self.screen, self.fonts["small"], f"↑ {dom:.0f} Hz",
                  (rect.left + 12, rect.top + 10), COLORS["green"])

    def _toggle_viz_mode(self):
        """Switch between waveform and spectrum visualization modes."""
        reset_spectrum()   # ← Smoothing-Buffer aus spectrum.py leeren
        if self.viz_mode == "waveform":
            self.viz_mode = "spectrum"
            self.status   = "Visualizer: Spectrum (FFT)"
        else:
            self.viz_mode = "waveform"
            self.status   = "Visualizer: Waveform"

    def _signal_points(self, signal, rect):
        """Convert an audio signal into drawable waveform points."""
        if signal.size < 2:
            return []

        left = rect.left + 10
        right = rect.right - 10
        top = rect.top + 24
        bottom = rect.bottom - 10
        width = right - left
        height = bottom - top

        if width <= 1 or height <= 1:
            return []

        step = max(1, signal.size // width)
        sampled = signal[::step][:width]
        peak = max(0.05, float(np.max(np.abs(sampled))))
        center_y = top + height / 2
        amplitude = height * 0.45

        points = []
        for index, sample in enumerate(sampled):
            x = left + index
            normalized = max(-1.0, min(1.0, float(sample) / peak))
            y = center_y - normalized * amplitude
            points.append((x, y))
        return points

    def _draw_footer(self):
        """Draw the selected microphone and keyboard shortcut hint."""
        mic_label = self._current_mic_label()
        draw_text(self.screen, self.fonts["small"], f"Mic: {mic_label}", (760, 1068), COLORS["muted"])
        draw_text(self.screen, self.fonts["small"], "Keys: W add WAV, S add sine, M mic, Space stop/resume, Esc quit",
                  (760, 1090), COLORS["muted"])

    def _draw_tracks(self, mouse_pos):
        """Draw tracks plus volume, mute, solo, select, and remove controls."""
        if not any(getattr(control, "dragging", False) for control in self.track_controls):
            self._sync_track_controls()
        tracks = mixer.get_tracks()
        if not tracks:
            draw_text(self.screen, self.fonts["body"], "No tracks loaded yet", (48, 680), COLORS["muted"])
            return

        for track in tracks[:4]:
            y = 748 + track["index"] * 24   # y: 668 → 748 (panel y=700 + header ~48)
            name = track["name"]
            if len(name) > 36:
                name = name[:33] + "..."
            flags = []
            if track["muted"]:
                flags.append("MUTE")
            if track["solo"]:
                flags.append("SOLO")
            if track["index"] == self.selected_track_index:
                flags.append("SELECTED")
            flag_text = f" {' / '.join(flags)}" if flags else ""
            draw_text(self.screen, self.fonts["small"], f"{track['index'] + 1}. {name}{flag_text}", (48, y - 13), COLORS["text"])

        if len(tracks) > 4:
            draw_text(self.screen, self.fonts["small"], f"+ {len(tracks) - 4} more track(s)", (984, 814), COLORS["muted"])

        for control in self.track_controls:
            control.draw(self.screen, self.fonts, mouse_pos)

    def _draw_track_fx(self, mouse_pos):
        """Draw controls for effects on the selected track or all tracks."""
        # Ghost-Fix: nur synchen wenn KEIN Slider gezogen wird UND kein Dragging aktiv
        any_dragging = any(getattr(c, "dragging", False) for c in self.track_fx_controls)
        if not any_dragging:
            self._sync_track_fx_controls()

        if self.selected_track_index is None or (
            self.selected_track_index != -1 and self.selected_track_index >= mixer.track_count()
        ):
            draw_text(self.screen, self.fonts["body"],
                      "Select a track to edit its own effects", (48, 900), COLORS["muted"])
            return

        tracks = mixer.get_tracks()
        if self.selected_track_index == -1:
            draw_text(self.screen, self.fonts["small"], "Editing: all loaded tracks", (48, 878), COLORS["muted"])
        else:
            track = tracks[self.selected_track_index]
            name  = track["name"]
            if len(name) > 44:
                name = name[:41] + "..."
            draw_text(self.screen, self.fonts["small"], f"Editing: {name}", (48, 878), COLORS["muted"])

        for pad in self.track_effect_pads:
            pad.draw(self.screen, self.fonts, mouse_pos)
        for control in self.track_fx_controls:
            control.draw(self.screen, self.fonts, mouse_pos)

    def _choose_wav(self):
        """Open a file picker, load the selected WAV, and start playback if needed."""
        filepath = choose_wav_file()
        if not filepath:
            return
        try:
            load_file(filepath)
            self.source = f"Added WAV: {os.path.basename(filepath)}"
            self.selected_track_index = mixer.track_count() - 1
            self._sync_track_controls(force=True)
            self._sync_track_fx_controls(force=True)
            self._ensure_stream()
        except Exception as exc:
            self._set_error("Could not load WAV", exc)

    def _use_sine(self):
        """Generate a sine wave source and add it as a new track."""
        try:
            data = self._generate_sine(self.sine_freq, self.sine_duration)
            load_audio_data(data)
            self.source = f"Added sine: {self.sine_freq:.1f} Hz for {self.sine_duration:.1f} sec"
            self.selected_track_index = mixer.track_count() - 1
            self._sync_track_controls(force=True)
            self._sync_track_fx_controls(force=True)
            self._ensure_stream()
        except Exception as exc:
            self._set_error("Could not start sine", exc)

    def _use_microphone(self):
        """Enable the selected microphone and start a duplex stream."""
        try:
            device_index = None
            if self.mic_devices:
                device_index = self.mic_devices[self.mic_index]["index"]
            self._stop_stream()
            enable_mic(device_index)
            self.source = f"Microphone: {self._current_mic_label()}"
            self._start_stream()
        except Exception as exc:
            self._set_error("Could not start mic", exc)

    def _refresh_mics(self, silent=False):
        """Reload the list of available microphone devices."""
        try:
            self.mic_devices = get_microphone_devices()
            self.mic_index = min(self.mic_index, max(0, len(self.mic_devices) - 1))
            if not silent:
                self.status = "Microphones refreshed"
                self.error = ""
        except Exception as exc:
            self.mic_devices = []
            if not silent:
                self._set_error("Could not list microphones", exc)

    def _next_mic(self):
        """Select the next detected microphone device."""
        if not self.mic_devices:
            self.status = "No microphone found"
            return
        self.mic_index = (self.mic_index + 1) % len(self.mic_devices)
        self.status = "Microphone selected"
        self.error = ""

    def _toggle_effect(self, key, enabled):
        """Toggle a global effect that applies after the whole mix."""
        name, effect_fn, reset_fn, _color = EFFECTS[key]
        if enabled:
            if effect_fn not in active_effects:
                active_effects.append(effect_fn)
            self.status = f"{name} enabled"
        else:
            if effect_fn in active_effects:
                active_effects.remove(effect_fn)
            reset_fn()
            self.status = f"{name} disabled"
        self.error = ""

    def _clear_effects(self):
        """Disable all global and per-track effects."""
        active_effects.clear()
        for pad in self.effect_pads:
            pad.enabled = False
            EFFECTS[pad.key][2]()
        for index in range(mixer.track_count()):
            for key in EFFECTS:
                mixer.set_track_effect_enabled(index, key, False)
        self.status = "Effects cleared"
        self.error = ""
        self._sync_track_fx_controls(force=True)

    def _clear_sources(self):
        """Stop playback and remove every track and microphone source."""
        self._stop_stream()
        clear_sources()
        self.source = "No source selected"
        self.status = "Sources cleared"
        self.error = ""
        self.selected_track_index = None
        self._sync_track_controls(force=True)
        self._sync_track_fx_controls(force=True)

    def _set_sine_freq(self, value):
        """Update the frequency used when generating the next sine track."""
        self.sine_freq = value

    def _set_sine_duration(self, value):
        """Update the duration used when generating the next sine track."""
        self.sine_duration = value

    def _generate_sine(self, frequency, duration, samplerate=44100):
        """Generate a mono float32 sine wave."""
        t = np.linspace(0, duration, int(samplerate * duration), endpoint=False)
        return np.sin(2 * np.pi * frequency * t).astype("float32")

    def _prepare_new_source(self):
        """Stop playback and clear old sources before replacing them."""
        self._stop_stream()
        clear_sources()

    def _ensure_stream(self):
        """Start playback if needed; otherwise mark the existing stream as playing."""
        if self.stream is None:
            self._start_stream()
        else:
            self.status = "Playing"
            self.error = ""

    def _resume_stream(self):
        """Restart playback only when at least one source exists."""
        if not mixer.has_sources():
            self.status = "No source to resume"
            return
        self._start_stream()

    def _start_stream(self):
        """Create and start a fresh audio stream."""
        self._stop_stream()
        self.stream = start_stream()
        self.stream.start()
        self.status = "Playing"
        self.error = ""

    def _stop_stream(self):
        """Stop and close the current audio stream if one is active."""
        if self.stream is None:
            self.status = "Stopped"
            return
        try:
            self.stream.stop()
            self.stream.close()
        finally:
            self.stream = None
            self.status = "Stopped"

    def _set_track_volume(self, index, value):
        """Forward a track volume change to the mixer."""
        mixer.set_track_volume(index, value)

    def _toggle_track_mute(self, index):
        """Toggle one track's muted state and rebuild the visible controls."""
        tracks = mixer.get_tracks()
        if 0 <= index < len(tracks):
            mixer.set_track_muted(index, not tracks[index]["muted"])
            self._sync_track_controls(force=True)

    def _toggle_track_solo(self, index):
        """Toggle solo mode for one track and rebuild the visible controls."""
        mixer.solo_track(index)
        self._sync_track_controls(force=True)

    def _remove_track(self, index):
        """Remove a track and keep the selected track index valid."""
        mixer.remove_track(index)
        if self.selected_track_index == index:
            self.selected_track_index = None
        elif self.selected_track_index is not None and self.selected_track_index > index:
            self.selected_track_index -= 1
        self._sync_track_controls(force=True)
        self._sync_track_fx_controls(force=True)

    def _select_track(self, index):
        """Select one track for per-track effect editing."""
        if 0 <= index < mixer.track_count():
            self.selected_track_index = index
            self.status = f"Track {index + 1} selected"
            self._sync_track_controls(force=True)
            self._sync_track_fx_controls(force=True)

    def _select_all_tracks(self):
        """Select all tracks so effect controls update every track."""
        if mixer.track_count() == 0:
            self.status = "No tracks loaded"
            return
        self.selected_track_index = -1
        self.status = "All tracks selected for FX"
        self._sync_track_controls(force=True)
        self._sync_track_fx_controls(force=True)

    # y: 680 → 760
    def _sync_track_controls(self, force=False):
        """Rebuild track-row controls when the track list or state changes."""
        tracks = mixer.get_tracks()[:4]
        snapshot = [(track["index"], track["muted"], track["solo"], track["name"]) for track in tracks]
        if not force and snapshot == self.track_snapshot:
            return

        self.track_snapshot = snapshot
        self.track_controls = []
        for row, track in enumerate(tracks):
            index = track["index"]
            y = 760 + row * 24  # ← 680 → 760
            self.track_controls.append(
                Slider(
                    (370, y - 2, 300, 20), "",
                    0.0, 2.0, track["volume"],
                    lambda value, track_index=index: self._set_track_volume(track_index, value),
                    lambda value: f"{int(value * 100)}%",
                )
            )
            mute_label = "Unmute" if track["muted"] else "Mute"
            solo_label = "Solo*" if track["solo"] else "Solo"
            self.track_controls.append(Button((702, y - 12, 74, 28), mute_label,
                                              lambda track_index=index: self._toggle_track_mute(track_index),
                                              COLORS["panel_2"]))
            self.track_controls.append(Button((790, y - 12, 68, 28), solo_label,
                                              lambda track_index=index: self._toggle_track_solo(track_index),
                                              COLORS["panel_2"]))
            self.track_controls.append(
                Button((872, y - 12, 82, 28), "Select", lambda track_index=index: self._select_track(track_index),
                       COLORS["cyan"]))
            self.track_controls.append(
                Button((968, y - 12, 82, 28), "Remove", lambda track_index=index: self._remove_track(track_index),
                       COLORS["red"]))

    def _toggle_track_effect(self, key, enabled):
        """Enable or disable one effect on the selected track set."""
        if self.selected_track_index is None:
            return
        for index in self._target_track_indices():
            mixer.set_track_effect_enabled(index, key, enabled)
        target = "All tracks" if self.selected_track_index == -1 else f"Track {self.selected_track_index + 1}"
        self.status = f"{target}: {EFFECTS[key][0]} {'on' if enabled else 'off'}"
        self._sync_track_fx_controls(force=True)

    def _set_track_effect_param(self, effect_name, param_name, value):
        """Apply one per-track effect parameter to the selected track set."""
        if self.selected_track_index is None:
            return
        for index in self._target_track_indices():
            mixer.set_track_effect_param(index, effect_name, param_name, value)

    def _target_track_indices(self):
        """Return the actual track indices represented by the current selection."""
        if self.selected_track_index == -1:
            return range(mixer.track_count())
        if 0 <= self.selected_track_index < mixer.track_count():
            return [self.selected_track_index]
        return []

    def _sync_track_fx_controls(self, force=False):
        """Rebuild per-track effect pads and parameter sliders when selection changes."""
        if self.selected_track_index is None or (
            self.selected_track_index != -1 and self.selected_track_index >= mixer.track_count()
        ):
            if not force and self.track_fx_snapshot is None:
                return
            self.track_fx_snapshot = None
            self.track_effect_pads = []
            self.track_fx_controls = []
            return

        if self.selected_track_index == -1:
            all_effects = [mixer.get_track_effects(i) for i in range(mixer.track_count())]
            enabled = set.intersection(*all_effects) if all_effects else set()
            params  = mixer.get_track_effect_params(0) if mixer.track_count() else mixer.get_track_effect_params(-1)
        else:
            enabled = mixer.get_track_effects(self.selected_track_index)
            params  = mixer.get_track_effect_params(self.selected_track_index)

        # Snapshot: detect changes
        try:
            snapshot = (
                self.selected_track_index,
                tuple(sorted(enabled)),
                tuple(
                    (effect, param, params[effect][param])
                    for effect, param, _label, _min, _max in TRACK_FX_SLIDERS
                    if effect in params and param in params[effect]
                ),
            )
        except Exception:
            snapshot = None

        if not force and snapshot == self.track_fx_snapshot:
            return

        self.track_fx_snapshot = snapshot

        # ── Effect Pads (toggle buttons) ──────────────────────────────────
        self.track_effect_pads = []
        x = 42
        for key, (label, _fn, _reset, color) in EFFECTS.items():
            pad = TogglePad((x, 902, 104, 34), key, label, color, self._toggle_track_effect)
            pad.enabled = key in enabled
            self.track_effect_pads.append(pad)
            x += 116

        # ── FX Sliders — 2 rows of 5 ──────────────────────────────────────
        # Row 1: y=952, Row 2: y=1012 — 5 sliders per row, width=194 each
        self.track_fx_controls = []
        col_w = 210
        row_y = [952, 1012]

        for i, (effect_name, param_name, label, minimum, maximum) in enumerate(TRACK_FX_SLIDERS):
            row = i // 5
            col = i % 5
            x   = 42 + col * col_w
            y   = row_y[row]
            w   = col_w - 16

            # Wert aus params holen, Fallback auf minimum
            value = minimum
            if effect_name in params and param_name in params[effect_name]:
                value = params[effect_name][param_name]

            self.track_fx_controls.append(
                Slider(
                    (x, y, w, 20),
                    label,
                    minimum,
                    maximum,
                    value,
                    lambda v, e=effect_name, p=param_name: self._set_track_effect_param(e, p, v),
                )
            )

    def _current_mic_label(self):
        """Return a display label for the selected microphone."""
        if not self.mic_devices:
            return "default input"
        device = self.mic_devices[self.mic_index]
        return f"{device['name']} ({device['index']})"

    def _set_error(self, title, exc):
        """Show an operation failure in the status and error areas."""
        self.status = title
        self.error = str(exc)


def choose_wav_file():
    """Open a topmost Tk file dialog and return the selected WAV path."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    filepath = filedialog.askopenfilename(
        title="Choose WAV file",
        filetypes=[("WAV files", "*.wav"), ("All files", "*.*")],
    )
    root.destroy()
    return filepath


def run_ui():
    """Import pygame lazily and start the pygame application."""
    global pygame
    import pygame

    AudioWowPygame().run()
