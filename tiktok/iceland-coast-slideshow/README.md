# Iceland Coast TikTok Clip

Generator for a short Babel Boost TikTok made from seven landscape photos.

Output:
- 1080×1920
- 30 fps
- about 15 seconds
- H.264 MP4
- smooth pan/zoom
- cross-dissolve transitions
- built-in Babel Boost branding
- English hook and CTA

## Run

```bash
python make_clip.py 01.jpg 02.jpg 03.jpg 04.jpg 05.jpg 06.jpg 07.jpg -o iceland_coast_tiktok.mp4
```

Install Python packages first:

```bash
pip install pillow opencv-python numpy
```

FFmpeg must be available on PATH.

## Current edit

Hook: **ICELAND WITHOUT THE CROWDS**

Middle copy:
- **THIS IS ICELAND TOO**
- **SLOW DOWN. LOOK CLOSER.**

CTA: **FOLLOW @BABELBOOST FOR REAL ICELAND**

The exported clip is intended to receive a current/trending TikTok audio track during upload.
