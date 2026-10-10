"""NieFiltrowanyPL Podcast Studio. Python 3.11+, Windows, FFmpeg."""
from __future__ import annotations
import json, os, re, shutil, subprocess, threading, urllib.request, wave
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
OUTPUT.mkdir(exist_ok=True)
CHANNEL = "NieFiltrowanyPL"
WIDTH, HEIGHT = 1920, 1080

def font(size):
    for p in [r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\arial.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def wrap(text, draw, ft, limit):
    out, line = [], ""
    for word in text.split():
        next_line = (line + " " + word).strip()
        if draw.textbbox((0, 0), next_line, font=ft)[2] > limit and line:
            out.append(line); line = word
        else:
            line = next_line
    if line: out.append(line)
    return out

def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n{2,}", text.strip()) if s.strip()]

def create_slide(text, dest, image_path=None):
    if image_path and Path(image_path).is_file():
        im = Image.open(image_path).convert("RGB")
        ratio = max(WIDTH / im.width, HEIGHT / im.height)
        sw, sh = int(im.width * ratio), int(im.height * ratio)
        im = im.resize((sw, sh), Image.Resampling.LANCZOS)
        x, y = (sw-WIDTH)//2, (sh-HEIGHT)//2
        im = im.crop((x,y,x+WIDTH,y+HEIGHT))
        veil = Image.new("RGBA", im.size, (0,0,0,145))
        im = Image.alpha_composite(im.convert("RGBA"), veil).convert("RGB")
    else:
        im = Image.new("RGB", (WIDTH, HEIGHT), (15,17,24))
    d = ImageDraw.Draw(im)
    d.rectangle((0,0,WIDTH,22), fill=(204,30,45))
    d.text((100,105), "NIEFILTROWANYPL  |  POLSKA BEZ FILTRA", font=font(43), fill=(250,65,75))
    headline = " ".join(text.split())
    ft = font(78)
    lines = wrap(headline[:240], d, ft, WIDTH - 230)[:6]
    start = max(255, 535 - len(lines)*53)
    for i,line in enumerate(lines):
        d.text((110,start+i*105), line, font=ft, fill="white")
    d.rectangle((100,HEIGHT-110,WIDTH-100,HEIGHT-104), fill=(204,30,45))
    d.text((100,HEIGHT-85), "youtube.com/@NieFiltrowanyPL", font=font(30), fill=(225,225,225))
    im.save(dest, quality=91)

def ps_tts(text, path, rate=0):
    if os.name != "nt":
        raise RuntimeError("Wbudowany głos Windows działa tylko na Windows. Wybierz własny plik WAV/MP3.")
    ps = OUTPUT / "voice_tmp.ps1"
    wav = str(path).replace("'","''")
    # Escape Polish text via JSON, then embed as base64 to avoid PowerShell quoting.
    import base64
    b = base64.b64encode(text.encode("utf-8")).decode("ascii")
    src = ("Add-Type -AssemblyName System.Speech\n"
           "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer\n"
           "$voices = @($s.GetInstalledVoices() | Where-Object { $_.Enabled })\n"
           "$pl = $voices | Where-Object { $_.VoiceInfo.Culture.Name -like 'pl-*' } | Select-Object -First 1\n"
           "if ($pl) { $s.SelectVoice($pl.VoiceInfo.Name) }\n"
           f"$s.Rate = {int(rate)}\n"
           f"$t = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{b}'))\n"
           f"$s.SetOutputToWaveFile('{wav}')\n"
           "$s.Speak($t)\n$s.Dispose()\n")
    ps.write_text(src, encoding="utf-8-sig")
    try:
        p = subprocess.run(["powershell","-NoProfile","-ExecutionPolicy","Bypass","-File",str(ps)],
                            capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError("Synteza Windows nie powiodła się: " + p.stderr[-700:])
    finally:
        ps.unlink(missing_ok=True)

def probe_duration(path):
    p = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                        "-of","default=noprint_wrappers=1:nokey=1",str(path)],
                       capture_output=True,text=True,check=True)
    return float(p.stdout.strip())

def stamp(s):
    h=int(s//3600); m=int(s%3600//60); sec=int(s%60); ms=int((s-int(s))*1000)
    return f"{h:02}:{m:02}:{sec:02},{ms:03}"

def build_srt(text, duration, path):
    chunks = sentences(text)
    if not chunks: raise ValueError("Brak scenariusza.")
    sizes=[max(1,len(x.split())) for x in chunks]; total=sum(sizes); pos=0.0
    with path.open("w",encoding="utf-8-sig") as f:
        for i,(s,n) in enumerate(zip(chunks,sizes),1):
            end=duration if i==len(chunks) else pos+duration*n/total
            f.write(f"{i}\n{stamp(pos)} --> {stamp(end)}\n{s}\n\n")
            pos=end

def produce(text, title, voice_file, photos, log):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("Brak FFmpeg lub ffprobe w PATH. Zainstaluj FFmpeg i uruchom ponownie.")
    folder=OUTPUT / datetime.now().strftime("%Y%m%d_%H%M%S")
    folder.mkdir(parents=True,exist_ok=True)
    (folder/"scenariusz.txt").write_text(text,encoding="utf-8")
    log("Przygotowuję głos...")
    audio=folder/"voice.wav"
    if voice_file:
        subprocess.run(["ffmpeg","-y","-i",voice_file,"-ar","44100","-ac","2",str(audio)],
                       check=True,capture_output=True)
    else:
        ps_tts(text,audio)
    duration=probe_duration(audio)
    log(f"Długość nagrania: {duration/60:.1f} min")
    srt=folder/"napisy.srt"
    build_srt(text,duration,srt)
    ss=sentences(text)
    # Use a manageable number of cards for a long podcast; one for ~20 seconds.
    cards_count=max(1,int(duration/20+0.5))
    cards=[]
    for i in range(cards_count):
        idx=min(len(ss)-1,int(i*len(ss)/cards_count))
        frame=folder/f"scene_{i+1:03}.jpg"
        create_slide(ss[idx],frame,photos[i%len(photos)] if photos else None)
        cards.append(frame)
    length=duration/len(cards)
    concat=folder/"slides.txt"
    with concat.open("w",encoding="utf-8") as f:
        for card in cards:
            f.write("file '"+card.as_posix().replace("'","'\\''")+"'\n")
            f.write(f"duration {length:.6f}\n")
        f.write("file '"+cards[-1].as_posix().replace("'","'\\''")+"'\n")
    log("Renderuję wideo MP4. To może potrwać.")
    video=folder/"podcast_youtube.mp4"
    cmd=["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),
         "-i",str(audio),"-map","0:v:0","-map","1:a:0",
         "-r","25","-vf","scale=1280:720,format=yuv420p",
         "-c:v","libx264","-preset","veryfast","-crf","24",
         "-c:a","aac","-b:a","160k","-pix_fmt","yuv420p",
         "-t",str(duration),"-movflags","+faststart",str(video)]
    p=subprocess.run(cmd,capture_output=True,text=True)
    if p.returncode: raise RuntimeError("Błąd renderowania FFmpeg:\n"+p.stderr[-1600:])
    description=(f"{title}\n\nPodcast NieFiltrowanyPL. Komentarz i opinie.\n"
                 "Źródła materiałów i cytatów dodaj przed publikacją.\n\n"
                 "https://www.youtube.com/@NieFiltrowanyPL\n"
                 "#NieFiltrowanyPL #PolskaBezFiltra #Podcast #Polityka")
    (folder/"youtube_opis.txt").write_text(description,encoding="utf-8")
    log("GOTOWE: "+str(video))
    return folder

def ollama_script(topic, minutes, model):
    prompt=(f"Napisz po polsku kompletny tekst narracji do podcastu NieFiltrowanyPL na temat: {topic}. "
            f"Długość około {minutes} minut. Styl satyryczny, krytyczny wobec wszystkich partii, "
            "wyważony faktograficznie. Wyraźnie rozróżniaj opinię i fakty. "
            "Nie wymyślaj danych, cytatów ani źródeł. Jeśli nie znasz faktu, oznacz [DO WERYFIKACJI]. "
            "Bez uwag reżyserskich, sam tekst dla lektora. Zakończ pytaniem do widzów.")
    payload=json.dumps({"model":model,"prompt":prompt,"stream":False,
                        "options":{"num_predict":max(1200,int(minutes)*180)}}).encode()
    req=urllib.request.Request("http://127.0.0.1:11434/api/generate",data=payload,
                               headers={"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=600) as r:
        return json.load(r)["response"].strip()

class App:
    def __init__(self,root):
        self.root=root
        root.title("NieFiltrowanyPL Podcast Studio")
        root.geometry("1000x760")
        root.configure(bg="#14161d")
        self.topic=tk.StringVar(value="Politycy obiecują. Kto płaci rachunek?")
        self.minutes=tk.StringVar(value="12")
        self.model=tk.StringVar(value="gemma3:1b")
        self.audio=tk.StringVar()
        self.images=tk.StringVar()
        style=ttk.Style(); style.theme_use("clam")
        panel=ttk.Frame(root,padding=18);panel.pack(fill="both",expand=True)
        ttk.Label(panel,text="NIEFILTROWANYPL  |  PODCAST STUDIO",font=("Segoe UI",18,"bold")).pack(anchor="w",pady=(0,12))
        def line(label,var):
            x=ttk.Frame(panel);x.pack(fill="x",pady=3)
            ttk.Label(x,text=label,width=20).pack(side="left")
            ttk.Entry(x,textvariable=var).pack(side="left",fill="x",expand=True)
        line("Temat odcinka",self.topic)
        line("Minuty",self.minutes)
        line("Model Ollama",self.model)
        actions=ttk.Frame(panel);actions.pack(fill="x",pady=10)
        ttk.Button(actions,text="AI: napisz scenariusz",command=self.generate).pack(side="left",padx=4)
        ttk.Button(actions,text="Wczytaj scenariusz TXT",command=self.load_text).pack(side="left",padx=4)
        ttk.Button(actions,text="Wybierz głos MP3/WAV",command=self.choose_audio).pack(side="left",padx=4)
        ttk.Button(actions,text="Wybierz grafiki",command=self.choose_images).pack(side="left",padx=4)
        ttk.Label(panel,text="Scenariusz. Edytuj i sprawdź fakty przed renderowaniem.").pack(anchor="w")
        self.editor=tk.Text(panel,wrap="word",font=("Segoe UI",11),height=19)
        self.editor.pack(fill="both",expand=True,pady=5)
        self.editor.insert("1.0", "Witajcie w NieFiltrowanyPL. Dzisiaj rozmawiamy o obietnicach polityków.\n\n"
                           "Zanim ocenimy którąkolwiek partię, sprawdźmy fakty i daty.\n\n"
                           "Jaką obietnicę pamiętacie najlepiej? Napiszcie w komentarzach.")
        self.status=tk.StringVar(value="Gotowy. Wybierz własny głos lub użyj syntezatora Windows.")
        ttk.Label(panel,textvariable=self.status,wraplength=910).pack(anchor="w",pady=8)
        ttk.Button(panel,text="RENDERUJ PODCAST MP4 + WAV + SRT",command=self.render).pack(fill="x",ipady=12)
        ttk.Label(panel,text="AI wymaga opcjonalnego Ollama. Renderowanie działa bez AI. "
                            "Głos Windows zależy od zainstalowanych głosów. "
                            "Napisy są czasowane szacunkowo.",wraplength=910).pack(anchor="w",pady=8)
    def update_status(self,msg):
        self.root.after(0,lambda:self.status.set(str(msg)))
    def worker(self,func):
        def run():
            try: func()
            except Exception as e:
                self.root.after(0,lambda err=str(e):messagebox.showerror("Błąd",err))
                self.update_status("Błąd. Sprawdź komunikat.")
        threading.Thread(target=run,daemon=True).start()
    def generate(self):
        topic=self.topic.get().strip(); model=self.model.get().strip()
        try: minutes=int(self.minutes.get())
        except ValueError: messagebox.showerror("Błąd","Minuty muszą być liczbą.");return
        if not topic or not model or not 1<=minutes<=60: messagebox.showerror("Błąd","Sprawdź temat, model i czas 1–60 min.");return
        self.update_status("Generuję scenariusz przez lokalny Ollama...")
        def job():
            txt=ollama_script(topic,minutes,model)
            self.root.after(0,lambda:(self.editor.delete("1.0","end"),self.editor.insert("1.0",txt)))
            self.update_status("Scenariusz gotowy. Zweryfikuj dane i cytaty.")
        self.worker(job)
    def choose_audio(self):
        f=filedialog.askopenfilename(filetypes=[("Audio","*.mp3 *.wav *.m4a")])
        if f:self.audio.set(f);self.update_status("Głos: "+f)
    def choose_images(self):
        folder=filedialog.askdirectory(title="Folder z grafikami JPG/PNG")
        if folder:self.images.set(folder);self.update_status("Grafiki: "+folder)
    def load_text(self):
        f=filedialog.askopenfilename(filetypes=[("Tekst UTF-8","*.txt")])
        if f:
            txt=Path(f).read_text(encoding="utf-8-sig")
            self.editor.delete("1.0","end");self.editor.insert("1.0",txt)
    def render(self):
        text=self.editor.get("1.0","end").strip()
        if len(text)<40: messagebox.showerror("Błąd","Wpisz scenariusz.");return
        photos=[]
        if self.images.get():
            photos=sorted(str(p) for p in Path(self.images.get()).iterdir() if p.suffix.lower() in (".jpg",".jpeg",".png"))
        voice=self.audio.get()
        self.update_status("Uruchamiam render...")
        self.worker(lambda:produce(text,self.topic.get(),voice,photos,self.update_status))

if __name__=="__main__":
    root=tk.Tk()
    App(root)
    root.mainloop()
