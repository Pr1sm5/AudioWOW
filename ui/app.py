import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import numpy as np

from audio.input_handler import get_microphone_devices
from audio.processor import (
    active_effects,
    clear_sources,
    enable_mic,
    load_audio_data,
    load_file,
    set_volume,
    start_stream,
)
from effects.delay import apply_delay, reset_delay, set_delay, set_feedback
from effects.distortion import apply_distortion, reset_distortion, set_drive, set_level
from effects.highpass import apply_highpass, reset_highpass
from effects.highpass import set_cutoff as set_highpass_cutoff
from effects.lowpass import apply_lowpass, reset_lowpass
from effects.lowpass import set_cutoff as set_lowpass_cutoff
from effects.reverb import apply_reverb, reset as reset_reverb


EFFECTS = {
    "reverb": ("Reverb", apply_reverb, reset_reverb),
    "delay": ("Delay", apply_delay, reset_delay),
    "lowpass": ("Lowpass", apply_lowpass, reset_lowpass),
    "highpass": ("Highpass", apply_highpass, reset_highpass),
    "distortion": ("Distortion", apply_distortion, reset_distortion),
}


class AudioWowApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AudioWOW")
        self.geometry("680x560")
        self.minsize(620, 500)

        self.stream = None
        self.effect_vars = {}
        self.mic_devices = []
        self.mic_device_by_label = {}
        self.source_label = tk.StringVar(value="No source selected")
        self.status_label = tk.StringVar(value="Stopped")
        self.volume_label = tk.StringVar(value="100%")

        self._build_styles()
        self._build_layout()
        self._refresh_mics()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_styles(self):
        style = ttk.Style(self)
        style.configure("TFrame", padding=8)
        style.configure("Header.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Section.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("Status.TLabel", foreground="#31505f")

    def _build_layout(self):
        root = ttk.Frame(self, padding=16)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text="AudioWOW", style="Header.TLabel").pack(anchor="w")
        ttk.Label(root, textvariable=self.status_label, style="Status.TLabel").pack(anchor="w", pady=(2, 12))

        source_frame = ttk.LabelFrame(root, text="Source", padding=12)
        source_frame.pack(fill="x", pady=(0, 12))

        source_buttons = ttk.Frame(source_frame)
        source_buttons.pack(fill="x")
        ttk.Button(source_buttons, text="Load WAV", command=self._choose_wav).pack(side="left", padx=(0, 8))
        ttk.Button(source_buttons, text="Use Sine Wave", command=self._use_sine).pack(side="left", padx=(0, 8))
        ttk.Button(source_buttons, text="Use Microphone", command=self._use_microphone).pack(side="left")

        ttk.Label(source_frame, textvariable=self.source_label).pack(anchor="w", pady=(10, 0))

        mic_row = ttk.Frame(source_frame)
        mic_row.pack(fill="x", pady=(10, 0))
        ttk.Label(mic_row, text="Microphone").pack(side="left")
        self.mic_combo = ttk.Combobox(mic_row, state="readonly")
        self.mic_combo.pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(mic_row, text="Refresh", command=self._refresh_mics).pack(side="left")

        sine_frame = ttk.LabelFrame(root, text="Sine Wave", padding=12)
        sine_frame.pack(fill="x", pady=(0, 12))
        self.sine_freq = tk.DoubleVar(value=440.0)
        self.sine_duration = tk.DoubleVar(value=5.0)
        self._add_number_row(sine_frame, "Frequency Hz", self.sine_freq, 20.0, 20000.0)
        self._add_number_row(sine_frame, "Duration sec", self.sine_duration, 0.25, 30.0)

        effects_frame = ttk.LabelFrame(root, text="Effects", padding=12)
        effects_frame.pack(fill="both", expand=True, pady=(0, 12))

        toggle_frame = ttk.Frame(effects_frame)
        toggle_frame.pack(fill="x")
        for key, (name, _effect_fn, _reset_fn) in EFFECTS.items():
            var = tk.BooleanVar(value=False)
            self.effect_vars[key] = var
            ttk.Checkbutton(
                toggle_frame,
                text=name,
                variable=var,
                command=lambda effect_key=key: self._toggle_effect(effect_key),
            ).pack(side="left", padx=(0, 12))

        params = ttk.Frame(effects_frame)
        params.pack(fill="both", expand=True, pady=(12, 0))
        self._add_slider(params, "Delay seconds", 0.01, 2.0, 0.35, set_delay)
        self._add_slider(params, "Delay feedback", 0.0, 0.9, 0.4, set_feedback)
        self._add_slider(params, "Lowpass cutoff", 20.0, 20000.0, 1000.0, set_lowpass_cutoff)
        self._add_slider(params, "Highpass cutoff", 20.0, 20000.0, 500.0, set_highpass_cutoff)
        self._add_slider(params, "Distortion drive", 1.0, 20.0, 8.0, set_drive)
        self._add_slider(params, "Distortion level", 0.0, 1.0, 0.7, set_level)

        output_frame = ttk.LabelFrame(root, text="Output", padding=12)
        output_frame.pack(fill="x")
        volume_row = ttk.Frame(output_frame)
        volume_row.pack(fill="x")
        ttk.Label(volume_row, text="Volume").pack(side="left")
        volume = ttk.Scale(volume_row, from_=0.0, to=2.0, value=1.0, command=self._set_volume)
        volume.pack(side="left", fill="x", expand=True, padx=8)
        ttk.Label(volume_row, textvariable=self.volume_label, width=6).pack(side="left")

        controls = ttk.Frame(output_frame)
        controls.pack(fill="x", pady=(12, 0))
        ttk.Button(controls, text="Stop", command=self._stop_stream).pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="Clear Effects", command=self._clear_effects).pack(side="left")

    def _add_number_row(self, parent, label, variable, minimum, maximum):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=2)
        ttk.Label(row, text=label, width=16).pack(side="left")
        spin = ttk.Spinbox(row, from_=minimum, to=maximum, textvariable=variable, increment=1.0)
        spin.pack(side="left", fill="x", expand=True)

    def _add_slider(self, parent, label, minimum, maximum, value, setter):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=3)
        value_label = tk.StringVar(value=self._format_value(value))

        ttk.Label(row, text=label, width=18).pack(side="left")

        def on_change(raw_value):
            numeric_value = float(raw_value)
            setter(numeric_value)
            value_label.set(self._format_value(numeric_value))

        scale = ttk.Scale(row, from_=minimum, to=maximum, value=value, command=on_change)
        scale.pack(side="left", fill="x", expand=True, padx=8)
        ttk.Label(row, textvariable=value_label, width=8).pack(side="left")

    def _format_value(self, value):
        if value >= 100:
            return f"{value:.0f}"
        if value >= 10:
            return f"{value:.1f}"
        return f"{value:.2f}"

    def _choose_wav(self):
        filepath = filedialog.askopenfilename(
            title="Choose WAV file",
            filetypes=[("WAV files", "*.wav"), ("All files", "*.*")],
        )
        if not filepath:
            return

        try:
            self._prepare_new_source()
            load_file(filepath)
            self.source_label.set(f"WAV: {os.path.basename(filepath)}")
            self._start_stream()
        except Exception as exc:
            self._show_error("Could not load WAV file", exc)

    def _use_sine(self):
        try:
            frequency = float(self.sine_freq.get())
            duration = float(self.sine_duration.get())
            data = self._generate_sine(frequency, duration)
            self._prepare_new_source()
            load_audio_data(data)
            self.source_label.set(f"Sine wave: {frequency:.1f} Hz for {duration:.1f} sec")
            self._start_stream()
        except Exception as exc:
            self._show_error("Could not start sine wave", exc)

    def _use_microphone(self):
        try:
            label = self.mic_combo.get()
            device_index = self.mic_device_by_label.get(label)
            self._prepare_new_source()
            enable_mic(device_index)
            self.source_label.set(f"Microphone: {label or 'default input'}")
            self._start_stream()
        except Exception as exc:
            self._show_error("Could not start microphone", exc)

    def _generate_sine(self, frequency, duration, samplerate=44100):
        t = np.linspace(0, duration, int(samplerate * duration), endpoint=False)
        return np.sin(2 * np.pi * frequency * t).astype("float32")

    def _refresh_mics(self):
        try:
            self.mic_devices = get_microphone_devices()
        except Exception as exc:
            self.mic_devices = []
            self._show_error("Could not list microphones", exc)
            return

        self.mic_device_by_label = {}
        labels = []
        for device in self.mic_devices:
            label = f"{device['name']} ({device['index']})"
            labels.append(label)
            self.mic_device_by_label[label] = device["index"]

        self.mic_combo["values"] = labels
        if labels:
            self.mic_combo.current(0)

    def _toggle_effect(self, key):
        name, effect_fn, reset_fn = EFFECTS[key]
        if self.effect_vars[key].get():
            if effect_fn not in active_effects:
                active_effects.append(effect_fn)
        else:
            if effect_fn in active_effects:
                active_effects.remove(effect_fn)
            reset_fn()
        self.status_label.set(f"{name} {'enabled' if self.effect_vars[key].get() else 'disabled'}")

    def _clear_effects(self):
        active_effects.clear()
        for key, var in self.effect_vars.items():
            var.set(False)
            EFFECTS[key][2]()
        self.status_label.set("Effects cleared")

    def _set_volume(self, raw_value):
        value = float(raw_value)
        set_volume(value)
        self.volume_label.set(f"{int(value * 100)}%")

    def _prepare_new_source(self):
        self._stop_stream()
        clear_sources()

    def _start_stream(self):
        self._stop_stream()
        self.stream = start_stream()
        self.stream.start()
        self.status_label.set("Playing")

    def _stop_stream(self):
        if self.stream is None:
            return
        try:
            self.stream.stop()
            self.stream.close()
        finally:
            self.stream = None
            self.status_label.set("Stopped")

    def _show_error(self, title, exc):
        self.status_label.set(title)
        messagebox.showerror(title, str(exc))

    def _on_close(self):
        self._stop_stream()
        self.destroy()


def run_ui():
    app = AudioWowApp()
    app.mainloop()
