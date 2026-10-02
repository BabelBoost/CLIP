@echo off
setlocal
cd /d %~dp0

if not exist .venv (
  py -m venv .venv
)

call .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

REM Verify that OpenCV is complete. A conflicting/broken cv2 package can import
REM successfully while missing CascadeClassifier, which used to crash auto-zoom.
python -c "import cv2,sys; sys.exit(0 if hasattr(cv2,'CascadeClassifier') else 1)" >nul 2>&1
if errorlevel 1 (
  echo.
  echo [Viral Clip Studio] Naprawiam instalacje OpenCV...
  python -m pip uninstall -y cv2 opencv-python opencv-python-headless opencv-contrib-python opencv-contrib-python-headless >nul 2>&1
  python -m pip install --no-cache-dir "opencv-python-headless>=4.10"
)

python -c "import cv2; print('[Viral Clip Studio] OpenCV:', getattr(cv2,'__version__','unknown'), '- CascadeClassifier:', hasattr(cv2,'CascadeClassifier'))"

streamlit run app.py
