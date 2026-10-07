from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


APP_TITLE = "Babel Boost Video Compressor"

PRESETS = {
    "TikTok / Shorts 1080p": {
        "codec": "libx264",
        "crf": "23",
        "preset": "medium",
        "audio": "128k",
        "max_width": 1080,
        "fps": 30,
        "description": "Dobry balans jakości i rozmiaru do TikTok, Reels i Shorts.",
    },
    "Wysoka jakość": {
        "codec": "libx264",
        "crf": "20",
        "preset": "medium",
        "audio": "160k",
        "max_width": None,
        "fps": None,
        "description": "Mniejszy plik przy bardzo dobrej jakości obrazu.",
    },
    "Mały plik H.265": {
        "codec": "libx265",
        "crf": "28",
        "preset": "medium",
        "audio": "96k",
        "max_width": 1280,
        "fps": 30,
        "description": "Mocniejsza kompresja. H.265 daje mniejszy plik niż H.264.",
    },
    "Bardzo mały plik": {
        "codec": "libx265",
        "crf": "31",
        "preset": "medium",
        "audio": "80k",
        "max_width": 960,
        "fps": 30,
        "description": "Do wysyłania i archiwizacji, gdy rozmiar jest ważniejszy niż detal.",
    },
}


def human_size(value: int | float) -> str:
    value = float(value)
    units = ["B", "KB", "MB", "GB"]
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def find_tool(name: str) -> str | None:
    return shutil.which(name)


def probe_video(path: Path) -> dict:
    ffprobe = find_tool("ffprobe")
    if not ffprobe:
        raise RuntimeError("Nie znaleziono ffprobe. Zainstaluj FFmpeg i uruchom aplikację ponownie.")

    cmd = [
        ffprobe,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,r_frame_rate:format=duration",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Nie udało się odczytać informacji o wideo.")

    data = json.loads(result.stdout)
    stream = (data.get("streams") or [{}])[0]
    fmt = data.get("format") or {}

    return {
        "width": int(stream.get("width") or 0),
        "height": int(stream.get("height") or 0),
        "duration": float(fmt.get("duration") or 0),
    }


class VideoCompressorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("760x570")
        self.minsize(720, 540)

        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.preset_name = tk.StringVar(value="TikTok / Shorts 1080p")
        self.target_mb = tk.StringVar()
        self.status_text = tk.StringVar(value="Wybierz plik wideo.")
        self.file_info = tk.StringVar(value="")
        self.preset_info = tk.StringVar(value=PRESETS[self.preset_name.get()]["description"])
        self.progress = tk.DoubleVar(value=0.0)
        self.running = False

        self._build_ui()
        self.preset_name.trace_add("write", self._preset_changed)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=18)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text="Babel Boost Video Compressor", font=("Segoe UI", 19, "bold")).pack(anchor="w")
        ttk.Label(
            root,
            text="Zmniejsz rozmiar MP4, MOV, MKV i innych plików obsługiwanych przez FFmpeg.",
        ).pack(anchor="w", pady=(2, 18))

        file_frame = ttk.LabelFrame(root, text="1. Plik wejściowy", padding=12)
        file_frame.pack(fill="x")

        row = ttk.Frame(file_frame)
        row.pack(fill="x")
        ttk.Entry(row, textvariable=self.input_path).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Wybierz plik", command=self.choose_input).pack(side="left", padx=(8, 0))
        ttk.Label(file_frame, textvariable=self.file_info).pack(anchor="w", pady=(7, 0))

        settings = ttk.LabelFrame(root, text="2. Kompresja", padding=12)
        settings.pack(fill="x", pady=12)

        ttk.Label(settings, text="Tryb:").grid(row=0, column=0, sticky="w")
        preset_box = ttk.Combobox(
            settings,
            textvariable=self.preset_name,
            values=list(PRESETS.keys()),
            state="readonly",
            width=28,
        )
        preset_box.grid(row=0, column=1, sticky="w", padx=(10, 20))

        ttk.Label(settings, text="Docelowy rozmiar MB:").grid(row=0, column=2, sticky="w")
        ttk.Entry(settings, textvariable=self.target_mb, width=10).grid(row=0, column=3, sticky="w", padx=(10, 0))

        ttk.Label(
            settings,
            text="Pole opcjonalne. Jeśli wpiszesz np. 100, aplikacja dobierze bitrate do około 100 MB.",
            wraplength=690,
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(8, 3))
        ttk.Label(settings, textvariable=self.preset_info, wraplength=690).grid(
            row=2, column=0, columnspan=4, sticky="w"
        )

        output_frame = ttk.LabelFrame(root, text="3. Plik wynikowy", padding=12)
        output_frame.pack(fill="x")

        row2 = ttk.Frame(output_frame)
        row2.pack(fill="x")
        ttk.Entry(row2, textvariable=self.output_path).pack(side="left", fill="x", expand=True)
        ttk.Button(row2, text="Zmień miejsce", command=self.choose_output).pack(side="left", padx=(8, 0))

        progress_frame = ttk.LabelFrame(root, text="4. Kompresja", padding=12)
        progress_frame.pack(fill="both", expand=True, pady=(12, 0))

        self.progressbar = ttk.Progressbar(progress_frame, variable=self.progress, maximum=100)
        self.progressbar.pack(fill="x", pady=(0, 10))

        ttk.Label(progress_frame, textvariable=self.status_text, wraplength=690).pack(anchor="w")

        buttons = ttk.Frame(progress_frame)
        buttons.pack(fill="x", pady=(16, 0))

        self.start_button = ttk.Button(buttons, text="KOMPRESUJ WIDEO", command=self.start_compression)
        self.start_button.pack(side="left")

        ttk.Button(buttons, text="Otwórz folder wynikowy", command=self.open_output_folder).pack(
            side="left", padx=(8, 0)
        )

        ttk.Label(
            progress_frame,
            text="Wymagane: FFmpeg + FFprobe dostępne w PATH.",
        ).pack(anchor="w", pady=(16, 0))

    def _preset_changed(self, *_args) -> None:
        preset = PRESETS.get(self.preset_name.get())
        if preset:
            self.preset_info.set(preset["description"])

    def choose_input(self) -> None:
        filename = filedialog.askopenfilename(
            title="Wybierz plik wideo",
            filetypes=[
                ("Pliki wideo", "*.mp4 *.mov *.mkv *.avi *.webm *.m4v"),
                ("Wszystkie pliki", "*.*"),
            ],
        )
        if not filename:
            return

        path = Path(filename)
        self.input_path.set(str(path))
        default_output = path.with_name(f"{path.stem}_compressed.mp4")
        self.output_path.set(str(default_output))

        try:
            info = probe_video(path)
            size = path.stat().st_size
            duration = info["duration"]
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            self.file_info.set(
                f"{info['width']}x{info['height']} | {minutes:02d}:{seconds:02d} | {human_size(size)}"
            )
            self.status_text.set("Plik gotowy do kompresji.")
        except Exception as exc:
            self.file_info.set(human_size(path.stat().st_size))
            self.status_text.set(str(exc))

    def choose_output(self) -> None:
        initial = Path(self.output_path.get()) if self.output_path.get() else Path("compressed.mp4")
        filename = filedialog.asksaveasfilename(
            title="Zapisz plik wynikowy",
            defaultextension=".mp4",
            initialfile=initial.name,
            filetypes=[("MP4", "*.mp4")],
        )
        if filename:
            self.output_path.set(filename)

    def _build_command(self, input_path: Path, output_path: Path) -> tuple[list[str], float]:
        ffmpeg = find_tool("ffmpeg")
        if not ffmpeg:
            raise RuntimeError(
                "Nie znaleziono FFmpeg. W PowerShell uruchom: winget install Gyan.FFmpeg"
            )

        info = probe_video(input_path)
        duration = max(info["duration"], 0.1)
        preset = PRESETS[self.preset_name.get()]

        cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(input_path),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c:v",
            preset["codec"],
            "-preset",
            preset["preset"],
        ]

        target_text = self.target_mb.get().strip().replace(",", ".")
        if target_text:
            try:
                target_mb = float(target_text)
            except ValueError as exc:
                raise RuntimeError("Docelowy rozmiar musi być liczbą, np. 100.") from exc

            if target_mb <= 1:
                raise RuntimeError("Docelowy rozmiar powinien być większy niż 1 MB.")

            audio_bitrate = 96_000
            total_bitrate = (target_mb * 1024 * 1024 * 8 / duration) * 0.96
            video_bitrate = max(int(total_bitrate - audio_bitrate), 180_000)
            cmd += ["-b:v", str(video_bitrate), "-maxrate", str(int(video_bitrate * 1.15))]
            cmd += ["-bufsize", str(int(video_bitrate * 2))]
            audio_value = "96k"
        else:
            cmd += ["-crf", preset["crf"]]
            audio_value = preset["audio"]

        max_width = preset["max_width"]
        if max_width and info["width"] > max_width:
            cmd += ["-vf", f"scale={max_width}:-2"]

        fps = preset["fps"]
        if fps:
            cmd += ["-r", str(fps)]

        cmd += [
            "-c:a",
            "aac",
            "-b:a",
            audio_value,
            "-movflags",
            "+faststart",
            "-progress",
            "pipe:1",
            "-nostats",
            str(output_path),
        ]
        return cmd, duration

    def start_compression(self) -> None:
        if self.running:
            return

        input_path = Path(self.input_path.get().strip())
        output_path = Path(self.output_path.get().strip())

        if not input_path.is_file():
            messagebox.showerror(APP_TITLE, "Wybierz poprawny plik wejściowy.")
            return

        if not self.output_path.get().strip():
            messagebox.showerror(APP_TITLE, "Wybierz nazwę pliku wynikowego.")
            return

        if input_path.resolve() == output_path.resolve():
            messagebox.showerror(APP_TITLE, "Plik wynikowy musi mieć inną nazwę niż wejściowy.")
            return

        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            cmd, duration = self._build_command(input_path, output_path)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return

        self.running = True
        self.progress.set(0)
        self.status_text.set("Kompresowanie...")
        self.start_button.config(state="disabled")

        worker = threading.Thread(
            target=self._run_ffmpeg,
            args=(cmd, duration, input_path, output_path),
            daemon=True,
        )
        worker.start()

    def _run_ffmpeg(self, cmd: list[str], duration: float, input_path: Path, output_path: Path) -> None:
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )

            log_tail: list[str] = []
            if process.stdout:
                for raw_line in process.stdout:
                    line = raw_line.strip()
                    if line:
                        log_tail.append(line)
                        log_tail = log_tail[-20:]

                    if line.startswith("out_time_ms="):
                        try:
                            out_time_us = int(line.split("=", 1)[1])
                            elapsed = out_time_us / 1_000_000
                            percent = min(99.0, max(0.0, elapsed / duration * 100))
                            self.after(0, self.progress.set, percent)
                            self.after(0, self.status_text.set, f"Kompresowanie... {percent:.0f}%")
                        except ValueError:
                            pass

            code = process.wait()
            if code != 0:
                details = "\n".join(log_tail[-8:])
                raise RuntimeError("FFmpeg zakończył pracę błędem.\n\n" + details)

            before = input_path.stat().st_size
            after = output_path.stat().st_size
            reduction = max(0.0, (1 - after / before) * 100) if before else 0.0

            message = (
                f"Gotowe. {human_size(before)} → {human_size(after)}. "
                f"Zmniejszenie: {reduction:.1f}%."
            )
            self.after(0, self._finish_success, message)
        except Exception as exc:
            self.after(0, self._finish_error, str(exc))

    def _finish_success(self, message: str) -> None:
        self.running = False
        self.progress.set(100)
        self.status_text.set(message)
        self.start_button.config(state="normal")
        messagebox.showinfo(APP_TITLE, message)

    def _finish_error(self, message: str) -> None:
        self.running = False
        self.progress.set(0)
        self.status_text.set(message)
        self.start_button.config(state="normal")
        messagebox.showerror(APP_TITLE, message)

    def open_output_folder(self) -> None:
        output = self.output_path.get().strip()
        if not output:
            return

        folder = Path(output).parent
        folder.mkdir(parents=True, exist_ok=True)

        if os.name == "nt":
            os.startfile(folder)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(folder)])
        else:
            subprocess.Popen(["xdg-open", str(folder)])


if __name__ == "__main__":
    app = VideoCompressorApp()
    app.mainloop()
