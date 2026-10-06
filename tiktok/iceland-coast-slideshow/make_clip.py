#!/usr/bin/env python3
"""
Babel Boost TikTok Coast Slideshow
Creates a 1080x1920, 30 fps, 15 s MP4 from seven landscape JPGs.

Usage:
  python make_clip.py img1.jpg img2.jpg img3.jpg img4.jpg img5.jpg img6.jpg img7.jpg -o tiktok.mp4

Requires:
  pip install pillow opencv-python numpy
  ffmpeg available on PATH
"""
from PIL import Image, ImageDraw, ImageFont
import argparse, subprocess
import numpy as np
import cv2

W, H, FPS, TRANS = 1080, 1920, 30, 9
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

SCENE_PRESETS = [
    dict(dur=2.7, x0=.34, x1=.58, z0=1.00, z1=1.05, text="ICELAND WITHOUT\nTHE CROWDS", y=210),
    dict(dur=2.6, x0=.40, x1=.46, z0=1.00, z1=1.06, text="THIS IS ICELAND TOO", y=245),
    dict(dur=2.4, x0=.10, x1=.34, z0=1.01, z1=1.06, text=None),
    dict(dur=2.1, x0=.45, x1=.52, z0=1.00, z1=1.10, text=None),
    dict(dur=2.1, x0=.42, x1=.55, z0=1.00, z1=1.07, text="SLOW DOWN.\nLOOK CLOSER.", y=240),
    dict(dur=2.4, x0=.00, x1=.38, z0=1.00, z1=1.05, text=None),
    dict(dur=2.5, x0=.00, x1=.30, z0=1.00, z1=1.06, text="FOLLOW @BABELBOOST\nFOR REAL ICELAND", y=1240),
]

def ease(t):
    return t*t*(3-2*t)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs=7)
    ap.add_argument("-o", "--output", default="iceland_coast_tiktok.mp4")
    ap.add_argument("--cover", default="iceland_coast_tiktok_cover.jpg")
    args = ap.parse_args()

    scenes = []
    for p, preset in zip(args.images, SCENE_PRESETS):
        s = dict(preset)
        s["img"] = np.array(Image.open(p).convert("RGB"))
        s["frames"] = round(s["dur"] * FPS)
        scenes.append(s)

    font_big = ImageFont.truetype(FONT_BOLD, 74)
    font_small = ImageFont.truetype(FONT_BOLD, 60)
    font_brand = ImageFont.truetype(FONT_BOLD, 32)

    def render(s, i):
        n = max(2, s["frames"])
        t = min(1.0, max(0.0, i/(n-1)))
        e = ease(t)
        zoom = s["z0"] + (s["z1"]-s["z0"])*e
        xfrac = s["x0"] + (s["x1"]-s["x0"])*e
        src = s["img"]
        sh, sw = src.shape[:2]
        nh = int(round(H*zoom))
        nw = int(round(sw*(nh/sh)))
        r = cv2.resize(src, (nw, nh), interpolation=cv2.INTER_CUBIC)
        x = int(round(max(0, nw-W)*xfrac))
        y = max(0, (nh-H)//2)
        frame = r[y:y+H, x:x+W]
        if frame.shape[:2] != (H, W):
            frame = cv2.resize(frame, (W,H), interpolation=cv2.INTER_CUBIC)

        f = frame.astype(np.float32)
        grad = np.ones((H,1,1), np.float32)
        grad[:340,0,0] = np.linspace(.78, 1.0, 340)
        grad[-320:,0,0] = np.linspace(1.0, .86, 320)
        frame = np.clip(f*grad, 0,255).astype(np.uint8)

        pil = Image.fromarray(frame).convert("RGBA")
        d = ImageDraw.Draw(pil, "RGBA")

        brand = "BABEL BOOST | ICELAND"
        bb = d.textbbox((0,0), brand, font=font_brand)
        bw = bb[2]-bb[0]
        bx, by = 54, 1680
        d.rounded_rectangle((bx-18, by-12, bx+bw+18, by+48), 18, fill=(0,0,0,95))
        d.text((bx,by), brand, font=font_brand, fill=(255,255,255,220))

        if s.get("text"):
            txt = s["text"]
            font = font_small if "FOLLOW" in txt else font_big
            bb = d.multiline_textbbox((0,0), txt, font=font, spacing=10, align="center", stroke_width=2)
            tw, th = bb[2]-bb[0], bb[3]-bb[1]
            tx, ty = (W-tw)//2, s.get("y",230)
            d.rounded_rectangle((tx-34,ty-24,tx+tw+34,ty+th+24),28,fill=(0,0,0,120))
            d.multiline_text((tx,ty), txt, font=font, fill="white", spacing=10, align="center",
                             stroke_width=2, stroke_fill=(0,0,0,180))
        return np.array(pil.convert("RGB"))

    Image.fromarray(render(scenes[0], scenes[0]["frames"]//2)).save(args.cover, quality=94)

    cmd = [
        "ffmpeg","-y","-loglevel","error",
        "-f","rawvideo","-vcodec","rawvideo","-pix_fmt","rgb24",
        "-s",f"{W}x{H}","-r",str(FPS),"-i","-",
        "-f","lavfi","-i","anullsrc=channel_layout=stereo:sample_rate=44100",
        "-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p",
        "-c:a","aac","-b:a","128k","-shortest","-movflags","+faststart",args.output
    ]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    for si, s in enumerate(scenes):
        start = 0 if si == 0 else TRANS
        end = s["frames"] if si == len(scenes)-1 else s["frames"]-TRANS
        for i in range(start, end):
            p.stdin.write(render(s,i).tobytes())
        if si < len(scenes)-1:
            nxt = scenes[si+1]
            for k in range(TRANS):
                a = render(s, s["frames"]-TRANS+k).astype(np.float32)
                b = render(nxt, k).astype(np.float32)
                alpha = (k+1)/(TRANS+1)
                p.stdin.write(np.clip(a*(1-alpha)+b*alpha,0,255).astype(np.uint8).tobytes())
    p.stdin.close()
    raise SystemExit(p.wait())

if __name__ == "__main__":
    main()
