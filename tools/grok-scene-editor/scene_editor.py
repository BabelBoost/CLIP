#!/usr/bin/env python3
"""Offline scene editor for clips generated with Grok or other video tools.

Requires FFmpeg and ffprobe on PATH. Uses no API and sends no media anywhere.
"""
from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

APP_NAME = "Babel Boost Grok Scene Editor"


def find_binary(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    if os.name == "nt":
        exe = shutil.which(name + ".exe")
        if exe:
            return exe
    return None


def probe(path: str, ffprobe: str) -> tuple[float, bool]:
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-show_entries", "stream=codec_type", "-of", "json", path],
        capture_output=True, text=True, check=True
    )
    data = json.loads(result.stdout)
    duration = float(data.get("format", {}).get("duration", 0))
    has_audio = any(s.get("codec_type") == "audio" for s in data.get("streams", []))
    if duration <= 0:
        raise ValueError("Nie udało się odczytać długości pliku.")
    return duration, has_audio


def filter_escape(value: str) -> str:
    """Escape text for FFmpeg drawtext filter syntax."""
    return (value.replace("\\", "\\\\").replace(":", "\\:")
            .replace("'", "\\'").replace("%", "\\%")
            .replace(",", "\\,").replace("[", "\\[").replace("]", "\\]"))


def font_path() -> str | None:
    candidates = []
    if os.name == "nt":
        windir = os.environ.get("WINDIR", r"C:\Windows")
        candidates += [Path(windir) / "Fonts" / "arialbd.ttf",
                       Path(windir) / "Fonts" / "segoeuib.ttf"]
    elif __import__("sys").platform == "darwin":
        candidates += [Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
                       Path("/System/Library/Fonts/Supplemental/Verdana Bold.ttf")]
    else:
        candidates += [Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
                       Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf")]
    return next((str(p) for p in candidates if p.exists()), None)


class SceneEditor(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.geometry("960x720")
        self.minsize(780, 600)
        self.scenes: list[dict] = []
        self.events: queue.Queue = queue.Queue()
        self.worker: threading.Thread | None = None
        self.process: subprocess.Popen | None = None
        self.cancel_requested = False
        self._build_ui()
        self.after(120, self._poll_events)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=16)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text="Montaż scen z Grok", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(root, text="Lokalny montaż MP4. Bez API i wysyłania plików.",
                  foreground="#555").pack(anchor="w", pady=(2, 12))

        controls = ttk.Frame(root)
        controls.pack(fill="x", pady=(0, 8))
        ttk.Button(controls, text="Dodaj sceny", command=self.add_scenes).pack(side="left")
        ttk.Button(controls, text="Usuń zaznaczone", command=self.remove_scenes).pack(side="left", padx=6)
        ttk.Button(controls, text="W górę", command=lambda: self.move_scene(-1)).pack(side="left", padx=(12, 3))
        ttk.Button(controls, text="W dół", command=lambda: self.move_scene(1)).pack(side="left")

        columns = ("scene", "duration", "audio")
        self.table = ttk.Treeview(root, columns=columns, show="headings", height=8, selectmode="extended")
        self.table.heading("scene", text="Scena")
        self.table.heading("duration", text="Długość")
        self.table.heading("audio", text="Dźwięk")
        self.table.column("scene", width=620, anchor="w")
        self.table.column("duration", width=100, anchor="center")
        self.table.column("audio", width=100, anchor="center")
        self.table.pack(fill="both", expand=True)

        settings = ttk.LabelFrame(root, text="Ustawienia klipu", padding=10)
        settings.pack(fill="x", pady=12)
        self.ratio = tk.StringVar(value="9:16 · TikTok / Reels / Shorts")
        self.transition = tk.StringVar(value="0.35")
        self.ai_label = tk.StringVar(value="AI CONCEPT")
        self.opening = tk.StringVar(value="ICELAND IN 2126")
        self.closing = tk.StringVar(value="WOULD YOU LIVE HERE?")
        self.output = tk.StringVar(value="")

        row1 = ttk.Frame(settings)
        row1.pack(fill="x", pady=3)
        ttk.Label(row1, text="Format").pack(side="left")
        ttk.Combobox(row1, textvariable=self.ratio, state="readonly", width=28,
                     values=("9:16 · TikTok / Reels / Shorts", "16:9 · YouTube", "1:1 · Kwadrat")).pack(side="left", padx=(8, 20))
        ttk.Label(row1, text="Przejście (sek.)").pack(side="left")
        ttk.Spinbox(row1, from_=0, to=1.5, increment=0.05, textvariable=self.transition, width=7).pack(side="left", padx=8)
        ttk.Label(row1, text="0 = cięcie", foreground="#666").pack(side="left")

        row2 = ttk.Frame(settings)
        row2.pack(fill="x", pady=4)
        ttk.Label(row2, text="Etykieta").pack(side="left")
        ttk.Entry(row2, textvariable=self.ai_label, width=19).pack(side="left", padx=(8, 18))
        ttk.Label(row2, text="Tytuł początkowy").pack(side="left")
        ttk.Entry(row2, textvariable=self.opening, width=27).pack(side="left", padx=8)
        ttk.Label(row2, text="Napis końcowy").pack(side="left")
        ttk.Entry(row2, textvariable=self.closing, width=27).pack(side="left", padx=8)

        row3 = ttk.Frame(settings)
        row3.pack(fill="x", pady=(5, 1))
        ttk.Label(row3, text="Plik wynikowy").pack(side="left")
        ttk.Entry(row3, textvariable=self.output).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(row3, text="Wybierz…", command=self.choose_output).pack(side="left")

        footer = ttk.Frame(root)
        footer.pack(fill="x")
        self.render_button = ttk.Button(footer, text="Zmontuj klip", command=self.start_render)
        self.render_button.pack(side="left")
        self.cancel_button = ttk.Button(footer, text="Anuluj", command=self.cancel_render, state="disabled")
        self.cancel_button.pack(side="left", padx=6)
        self.progress = ttk.Progressbar(footer, mode="determinate", maximum=100)
        self.progress.pack(side="left", fill="x", expand=True, padx=12)
        self.status = ttk.Label(footer, text="Dodaj pliki w kolejności scen.")
        self.status.pack(side="right")

    def add_scenes(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Wybierz sceny w kolejności",
            filetypes=(("Pliki wideo", "*.mp4 *.mov *.mkv *.webm *.avi"), ("Wszystkie pliki", "*.*"))
        )
        if not paths:
            return
        ffprobe = find_binary("ffprobe")
        if not ffprobe:
            messagebox.showerror("Brak ffprobe", "Zainstaluj FFmpeg i dodaj folder bin do PATH.")
            return
        for path in paths:
            if any(s["path"] == path for s in self.scenes):
                continue
            try:
                duration, audio = probe(path, ffprobe)
                scene = {"path": path, "duration": duration, "audio": audio}
                self.scenes.append(scene)
                self.table.insert("", "end", values=(Path(path).name, f"{duration:.2f} s",
                                                       "Tak" if audio else "Brak"))
            except Exception as exc:
                messagebox.showerror("Nie można odczytać pliku", f"{Path(path).name}\n{exc}")

    def _sync_table(self) -> None:
        for item in self.table.get_children():
            self.table.delete(item)
        for scene in self.scenes:
            self.table.insert("", "end", values=(Path(scene["path"]).name,
                f'{scene["duration"]:.2f} s', "Tak" if scene["audio"] else "Brak"))

    def remove_scenes(self) -> None:
        selected = list(self.table.selection())
        for index in reversed([self.table.index(item) for item in selected]):
            self.scenes.pop(index)
        self._sync_table()

    def move_scene(self, direction: int) -> None:
        selected = self.table.selection()
        if len(selected) != 1:
            return
        index = self.table.index(selected[0])
        target = index + direction
        if 0 <= target < len(self.scenes):
            self.scenes[index], self.scenes[target] = self.scenes[target], self.scenes[index]
            self._sync_table()
            items = self.table.get_children()
            self.table.selection_set(items[target])

    def choose_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Zapisz gotowy klip", defaultextension=".mp4",
            filetypes=(("MP4", "*.mp4"),), initialfile="grok_scenes_tiktok.mp4"
        )
        if path:
            self.output.set(path)

    def start_render(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        if not self.scenes:
            messagebox.showinfo("Brak scen", "Dodaj przynajmniej jeden klip.")
            return
        ffmpeg = find_binary("ffmpeg")
        ffprobe = find_binary("ffprobe")
        if not ffmpeg or not ffprobe:
            messagebox.showerror("Brak FFmpeg", "Zainstaluj FFmpeg i ffprobe, a następnie dodaj ich folder bin do PATH.")
            return
        try:
            transition = float(self.transition.get().replace(",", "."))
            if not 0 <= transition <= 1.5:
                raise ValueError
        except ValueError:
            messagebox.showerror("Błędne przejście", "Wpisz wartość od 0 do 1,5 sekundy.")
            return
        output = self.output.get().strip()
        if not output:
            first = Path(self.scenes[0]["path"])
            output = str(first.with_name("grok_scenes_tiktok.mp4"))
            self.output.set(output)
        if Path(output).resolve() in [Path(s["path"]).resolve() for s in self.scenes]:
            messagebox.showerror("Błędna nazwa", "Plik wynikowy nie może nadpisać jednej ze scen.")
            return
        self.cancel_requested = False
        self.progress["value"] = 0
        self.status.config(text="Przygotowuję montaż…")
        self.render_button.config(state="disabled")
        self.cancel_button.config(state="normal")
        snapshot = [dict(s) for s in self.scenes]
        self.worker = threading.Thread(
            target=self._render_worker,
            args=(snapshot, output, ffmpeg, transition, self.ratio.get(), self.ai_label.get(),
                  self.opening.get(), self.closing.get()), daemon=True)
        self.worker.start()

    def _render_worker(self, scenes: list[dict], output: str, ffmpeg: str, transition: float,
                       ratio: str, label: str, title: str, closing: str) -> None:
        try:
            command, total = build_command(scenes, output, ffmpeg, transition, ratio, label, title, closing)
            self.events.put(("status", f"Renderowanie… 0%"))
            self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                            text=True, encoding="utf-8", errors="replace", bufsize=1)
            error_lines: list[str] = []
            assert self.process.stdout is not None
            for line in self.process.stdout:
                line = line.strip()
                if line.startswith("out_time_ms="):
                    try:
                        seconds = int(line.split("=", 1)[1]) / 1_000_000
                        pct = min(99, int(seconds / total * 100))
                        self.events.put(("progress", pct))
                    except ValueError:
                        pass
                elif line.startswith("progress=end"):
                    self.events.put(("progress", 100))
                elif line and ("Error" in line or "error" in line):
                    error_lines.append(line)
                    error_lines = error_lines[-8:]
                if self.cancel_requested and self.process.poll() is None:
                    self.process.terminate()
            code = self.process.wait()
            self.process = None
            if self.cancel_requested:
                self.events.put(("cancelled", None))
            elif code == 0 and Path(output).exists():
                self.events.put(("done", output))
            else:
                self.events.put(("error", "\n".join(error_lines) or f"FFmpeg zakończył pracę kodem {code}."))
        except Exception as exc:
            self.process = None
            self.events.put(("error", str(exc)))

    def cancel_render(self) -> None:
        self.cancel_requested = True
        self.status.config(text="Anulowanie…")

    def _poll_events(self) -> None:
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "progress":
                    self.progress["value"] = value
                    self.status.config(text=f"Renderowanie… {value}%")
                elif kind == "status":
                    self.status.config(text=value)
                elif kind == "done":
                    self.render_button.config(state="normal")
                    self.cancel_button.config(state="disabled")
                    self.status.config(text="Gotowe.")
                    messagebox.showinfo("Gotowe", f"Zapisano plik:\n{value}")
                elif kind == "cancelled":
                    self.render_button.config(state="normal")
                    self.cancel_button.config(state="disabled")
                    self.status.config(text="Montaż anulowany.")
                elif kind == "error":
                    self.render_button.config(state="normal")
                    self.cancel_button.config(state="disabled")
                    self.status.config(text="Wystąpił błąd.")
                    messagebox.showerror("Błąd montażu", str(value))
        except queue.Empty:
            pass
        self.after(120, self._poll_events)


def build_command(scenes: list[dict], output: str, ffmpeg: str, transition: float,
                  ratio: str, label: str, title: str, closing: str) -> tuple[list[str], float]:
    dimensions = {
        "9:16 · TikTok / Reels / Shorts": (1080, 1920),
        "16:9 · YouTube": (1920, 1080),
        "1:1 · Kwadrat": (1080, 1080),
    }
    width, height = dimensions.get(ratio, (1080, 1920))
    lengths = [float(s["duration"]) for s in scenes]
    transition = min(transition, max(0, min(lengths) / 2 - 0.05)) if len(scenes) > 1 else 0
    total = sum(lengths) - transition * (len(scenes) - 1)
    args = [ffmpeg, "-hide_banner", "-y"]
    for scene in scenes:
        args += ["-i", scene["path"]]

    graph: list[str] = []
    for i, scene in enumerate(scenes):
        graph.append(
            f"[{i}:v]trim=duration={lengths[i]:.4f},setpts=PTS-STARTPTS,"
            f"fps=30,scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,"
            f"eq=contrast=1.03:saturation=0.98,format=yuv420p[v{i}]"
        )
        if scene["audio"]:
            graph.append(f"[{i}:a]aresample=48000,atrim=duration={lengths[i]:.4f},asetpts=PTS-STARTPTS[a{i}]")
        else:
            graph.append(f"anullsrc=channel_layout=stereo:sample_rate=48000,atrim=duration={lengths[i]:.4f},asetpts=PTS-STARTPTS[a{i}]")

    if len(scenes) == 1:
        video_tag, audio_tag = "v0", "a0"
    elif transition <= 0.001:
        inputs = "".join(f"[v{i}][a{i}]" for i in range(len(scenes)))
        graph.append(f"{inputs}concat=n={len(scenes)}:v=1:a=1[vjoin][ajoin]")
        video_tag, audio_tag = "vjoin", "ajoin"
    else:
        previous = "v0"
        for i in range(1, len(scenes)):
            offset = sum(lengths[:i]) - transition * i
            target = f"vx{i}"
            graph.append(f"[{previous}][v{i}]xfade=transition=fade:duration={transition:.3f}:offset={offset:.4f}[{target}]")
            previous = target
        video_tag = previous

        previous_audio = "a0"
        for i in range(1, len(scenes)):
            target_audio = f"ax{i}"
            graph.append(f"[{previous_audio}][a{i}]acrossfade=d={transition:.3f}:c1=tri:c2=tri[{target_audio}]")
            previous_audio = target_audio
        audio_tag = previous_audio

    vf = f"[{video_tag}]"
    filters = []
    font = font_path()
    font_arg = f":fontfile='{filter_escape(font)}'" if font else ""
    if label.strip():
        filters.append(
            f"drawbox=x=w-270:y=48:w=230:h=54:color=black@0.42:t=fill,"
            f"drawtext=text='{filter_escape(label.strip())}'{font_arg}:fontcolor=white:fontsize=27:"
            f"x=w-252:y=60"
        )
    if title.strip():
        filters.append(
            f"drawtext=text='{filter_escape(title.strip())}'{font_arg}:fontcolor=white:fontsize=58:"
            f"borderw=3:bordercolor=black@0.65:x=(w-text_w)/2:y=150:enable='between(t,0,2.5)'"
        )
    if closing.strip():
        start = max(0, total - 2.4)
        filters.append(
            f"drawbox=x=(w-920)/2:y=h-250:w=920:h=100:color=black@0.48:t=fill:"
            f"enable='between(t,{start:.3f},{total:.3f})',"
            f"drawtext=text='{filter_escape(closing.strip())}'{font_arg}:fontcolor=white:fontsize=42:"
            f"borderw=2:bordercolor=black@0.4:x=(w-text_w)/2:y=h-225:"
            f"enable='between(t,{start:.3f},{total:.3f})'"
        )
    if filters:
        graph.append(f"{vf}{','.join(filters)},format=yuv420p[vout]")
    else:
        graph.append(f"{vf}format=yuv420p[vout]")

    fade_start = max(0, total - 0.4)
    graph.append(f"[{audio_tag}]afade=t=in:st=0:d=0.18,afade=t=out:st={fade_start:.3f}:d=0.4[aout]")
    args += ["-filter_complex", ";".join(graph), "-map", "[vout]", "-map", "[aout]",
             "-c:v", "libx264", "-preset", "medium", "-crf", "20",
             "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
             "-progress", "pipe:1", "-nostats", output]
    return args, total


if __name__ == "__main__":
    SceneEditor().mainloop()
