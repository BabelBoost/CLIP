"""Local FFmpeg montage engine. No shell interpolation or cloud calls."""
from __future__ import annotations
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont, ImageOps

class StudioError(Exception):
    pass


def run(args, cwd=None):
    try:
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    except FileNotFoundError as exc:
        raise StudioError('Zainstaluj FFmpeg i ffprobe, następnie uruchom aplikację ponownie.') from exc
    if result.returncode:
        raise StudioError(result.stderr[-3500:] or 'Nie udało się przetworzyć pliku.')
    return result.stdout


def probe(path):
    data = json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))
    streams = data.get('streams', [])
    video = next((s for s in streams if s['codec_type']=='video' and not s.get('disposition',{}).get('attached_pic')), None)
    return {'duration':float(data.get('format',{}).get('duration',0)), 'video':video, 'audio':any(s['codec_type']=='audio' for s in streams)}


def finite(value, label, low, high):
    try:
        n = float(value)
    except (ValueError, TypeError) as exc:
        raise StudioError(f'Niepoprawna wartość: {label}.') from exc
    if not math.isfinite(n) or not low <= n <= high:
        raise StudioError(f'{label}: dozwolony zakres {low}–{high}.')
    return n


def parse_srt(text):
    entries=[]
    def seconds(value):
        h,m,s,ms=re.split('[:,.]',value)
        if int(m)>59 or int(s)>59:
            raise StudioError('Niepoprawny czas w SRT.')
        return int(h)*3600+int(m)*60+int(s)+int(ms)/1000
    for block in re.split(r'\n\s*\n',text.replace('\r','').strip('\ufeff\n ')):
        if not block.strip():
            continue
        lines=block.splitlines()
        if lines[0].strip().isdigit():
            lines=lines[1:]
        match=re.fullmatch(r'(\d{2,}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2,}:\d{2}:\d{2}[,.]\d{3})',lines[0].strip()) if lines else None
        if not match or len(lines)<2:
            raise StudioError('Niepoprawny SRT. Podaj początek, koniec i tekst każdego napisu.')
        start,end=map(seconds,match.groups())
        if end<=start:
            raise StudioError('Koniec napisu musi być późniejszy niż początek.')
        entries.append({'start':start,'end':end,'text':'\n'.join(lines[1:])})
    return entries


def font_path():
    for p in [os.environ.get('AD_STUDIO_FONT',''),'C:/Windows/Fonts/arialbd.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf','/System/Library/Fonts/Supplemental/Arial Bold.ttf']:
        if p and Path(p).is_file():
            return p
    raise StudioError('Brak czcionki. Ustaw AD_STUDIO_FONT na plik TTF obsługujący polskie znaki.')


def text_panel(text,width,font_size,color='white'):
    if len(text)>600:
        raise StudioError('Skróć pojedynczy napis do 600 znaków.')
    font=ImageFont.truetype(font_path(),font_size)
    draw=ImageDraw.Draw(Image.new('RGBA',(width,1)))
    lines=[]
    for paragraph in text.splitlines():
        line=''
        for word in paragraph.split():
            candidate=(line+' '+word).strip()
            if draw.textlength(candidate,font=font)<=width-40:
                line=candidate
                continue
            if line:
                lines.append(line)
            line=''
            for char in word:
                if draw.textlength(line+char,font=font)>width-40:
                    lines.append(line);line=''
                line+=char
        lines.append(line)
    height=len(lines)*int(font_size*1.35)+28
    image=Image.new('RGBA',(width,height),(8,21,33,215))
    draw=ImageDraw.Draw(image)
    for i,line in enumerate(lines):
        draw.text((width/2,14+i*int(font_size*1.35)),line,font=font,fill=color,anchor='mt')
    return image


def cover_card(path,width,height,title,cta,website,destination):
    canvas=Image.new('RGB',(width,height),'#081521')
    if path:
        with Image.open(path) as image:
            art=ImageOps.contain(ImageOps.exif_transpose(image).convert('RGB'),(int(width*.72),int(height*.53)))
        canvas.paste(art,((width-art.width)//2,int(height*.18)))
    for text,y,size,color in [(title,.06,.045,'white'),(cta,.75,.037,'#FFD479'),(website,.82,.05,'white')]:
        if text:
            panel=text_panel(text,int(width*.84),int(min(width,height*.8)*size),color)
            if panel.height>height*.17:
                raise StudioError('Skróć tytuł lub tekst zakończenia.')
            canvas.paste(panel,(int(width*.08),int(height*y)),panel)
    canvas.save(destination)


def render(project,output,progress=lambda value,label:None):
    """Render absolute asset paths. Publish output only after successful verification."""
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        raise StudioError('Brak FFmpeg lub ffprobe w PATH.')
    clips=project.get('clips',[])
    if not 1<=len(clips)<=40:
        raise StudioError('Dodaj od 1 do 40 klipów.')
    width,height=project.get('size',[1080,1920])
    if (width,height) not in [(1080,1920),(720,1280),(1920,1080),(1080,1080)]:
        raise StudioError('Nieobsługiwany rozmiar eksportu.')
    fit=project.get('fit','contain')
    if fit not in ['contain','crop']:
        raise StudioError('Niepoprawny sposób kadrowania.')
    original=finite(project.get('original_volume',0),'Dźwięk klipów',0,2)
    music_gain=finite(project.get('music_volume',.12),'Muzyka',0,1)
    voice_gain=finite(project.get('voice_volume',1),'Lektor',0,2)
    prepared=[]
    for clip in clips:
        path=Path(clip['path']).resolve();info=probe(path)
        if not info['video']:
            raise StudioError(f'Brak obrazu: {path.name}')
        start=finite(clip.get('start',0),'Początek',0,info['duration'])
        end=finite(clip.get('end',info['duration']),'Koniec',0,info['duration'])
        if end-start<.1:
            raise StudioError('Każdy klip musi mieć przynajmniej 0,1 sekundy.')
        prepared.append((path,info,start,end-start))
    outro=finite(project.get('outro_seconds',4),'Zakończenie',0,15)
    total=sum(x[3] for x in prepared)+outro
    if total>600:
        raise StudioError('Maksymalny czas projektu wynosi 10 minut.')
    overlays=list(project.get('captions',[]))
    if project.get('hook','').strip():
        overlays.append({'start':0,'end':min(total,finite(project.get('hook_seconds',3),'Czas hooka',.1,15)),'text':project['hook'],'hook':True})
    for item in overlays:
        a=finite(item['start'],'Początek napisu',0,total);b=finite(item['end'],'Koniec napisu',0,total)
        if b<=a:
            raise StudioError('Niepoprawny zakres napisu.')
    if len(overlays)>150:
        raise StudioError('Limit wynosi 150 napisów.')
    voice=project.get('voice');music=project.get('music')
    for audio in [voice,music]:
        if audio and not probe(audio)['audio']:
            raise StudioError('Wybrany plik nie zawiera dźwięku.')
    if voice and probe(voice)['duration']>total+.1:
        raise StudioError('Nagranie lektora jest dłuższe niż film. Wydłuż klipy lub skróć nagranie.')
    output=Path(output).resolve()
    inputs=[x[0] for x in prepared]+[Path(p).resolve() for p in [voice,music,project.get('cover')] if p]
    if output in inputs:
        raise StudioError('Plik wynikowy nie może zastąpić źródła.')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ad-studio-',dir=output.parent) as temp:
        work=Path(temp)
        scale=(f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=0x081521' if fit=='contain' else f'scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}')
        encode=['-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-ar','48000','-ac','2']
        def ff(args):
            run(['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y','-filter_complex_threads','1',*args],cwd=work)
        for i,(path,info,start,duration) in enumerate(prepared):
            progress(.65*i/(len(prepared)+1),f'Klip {i+1}/{len(prepared)}')
            args=['-ss',str(start),'-i',str(path)]
            if not info['audio']:
                args+=['-f','lavfi','-i','anullsrc=r=48000:cl=stereo']
            args+=['-map','0:v:0','-map','0:a:0' if info['audio'] else '1:a:0','-t',str(duration),'-vf',scale+',setsar=1,fps=30','-af',f'aresample=48000,volume={original},apad',*encode,f's{i}.mp4']
            ff(args)
        count=len(prepared)
        if outro:
            progress(.65,'Zakończenie z okładką')
            cover_card(project.get('cover'),width,height,project.get('title','BABEL BOOST'),project.get('cta','GET THE EBOOK'),project.get('website','BabelBoost.com'),work/'card.png')
            ff(['-loop','1','-i','card.png','-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-t',str(outro),'-vf','fps=30,setsar=1',*encode,f's{count}.mp4'])
            count+=1
        (work/'list.txt').write_text(''.join(f"file 's{i}.mp4'\n" for i in range(count)))
        ff(['-f','concat','-safe','1','-i','list.txt','-c','copy','joined.mp4'])
        progress(.72,'Napisy i miks dźwięku')
        args=['-i','joined.mp4'];graph=[];previous='0:v';index=1
        for i,item in enumerate(overlays):
            panel=text_panel(item['text'],int(width*.82),int(min(width,height*.8)*(.052 if item.get('hook') else .042)))
            if panel.height>height*.28:
                raise StudioError('Napis jest za długi. Podziel go na krótsze fragmenty.')
            panel.save(work/f'caption{i}.png')
            args+=['-loop','1','-i',f'caption{i}.png']
            y=int(height*.17) if item.get('hook') else int(height*.70)-panel.height//2
            graph.append(f"[{previous}][{index}:v]overlay=x=(W-w)/2:y={y}:enable='gte(t,{float(item['start'])})*lt(t,{float(item['end'])})'[v{i}]")
            previous=f'v{i}';index+=1
        audio_labels=['[0:a]']
        for name,path,gain in [('music',music,music_gain),('voice',voice,voice_gain)]:
            if not path:
                continue
            if name=='music':
                args+=['-stream_loop','-1']
            args+=['-i',str(Path(path).resolve())]
            graph.append(f'[{index}:a]aresample=48000,volume={gain},apad,atrim=duration={total}[{name}]')
            audio_labels.append(f'[{name}]');index+=1
        graph.append(''.join(audio_labels)+f'amix=inputs={len(audio_labels)}:duration=first:normalize=0,alimiter=limit=0.95:level=0,afade=t=out:st={max(0,total-.6)}:d=0.6[aout]')
        args+=['-filter_complex',';'.join(graph),'-map',f'[{previous}]' if previous!='0:v' else '0:v:0','-map','[aout]','-t',str(total),*encode,'-movflags','+faststart','finished.mp4']
        ff(args)
        result=probe(work/'finished.mp4')
        if abs(result['duration']-total)>.25 or not result['audio']:
            raise StudioError('Eksport nie przeszedł kontroli długości lub dźwięku.')
        os.replace(work/'finished.mp4',output)
    progress(1,'Gotowe')
    return output
