# Babel Boost Video Downloader

Lokalne narzędzie do pobierania materiałów z:

- YouTube
- X / Twitter
- Facebook

Obsługuje MP4, wybór jakości oraz MP3.

## Ważne

Używaj narzędzia wyłącznie do materiałów, które należą do Ciebie, są udostępnione do pobrania albo masz zgodę na ich zapis. Aplikacja nie omija DRM ani zabezpieczeń prywatnych treści.

## Windows

1. Zainstaluj Python 3.11 lub nowszy.
2. Zainstaluj FFmpeg i dodaj go do PATH.
3. Otwórz folder `tools/video-downloader`.
4. Uruchom `run_windows.bat`.
5. Aplikacja otworzy się w przeglądarce.

Alternatywnie:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## FFmpeg na Windows

Najprościej przez Winget:

```powershell
winget install Gyan.FFmpeg
```

Potem otwórz nowy terminal i sprawdź:

```powershell
ffmpeg -version
```

## Linux i macOS

```bash
chmod +x run_linux_mac.sh
./run_linux_mac.sh
```

Na macOS FFmpeg można zainstalować przez Homebrew:

```bash
brew install ffmpeg
```

## Treści wymagające logowania

W aplikacji możesz wybrać Chrome, Edge lub Firefox. `yt-dlp` spróbuje użyć cookies z lokalnej przeglądarki. Korzystaj z tej opcji wyłącznie dla treści, do których masz legalny dostęp.

## Struktura modułu

```text
video-downloader/
├── app.py
├── downloader/
│   ├── __init__.py
│   └── core.py
├── tests/
│   └── test_core.py
├── requirements.txt
├── requirements-dev.txt
├── run_windows.bat
├── run_linux_mac.sh
├── ROADMAP.md
└── .gitignore
```

`app.py` odpowiada za interfejs Streamlit. `downloader/core.py` zawiera logikę, którą później można wykorzystać również w wersji desktopowej albo CLI.

## Testy

```bash
python -m pip install -r requirements-dev.txt
pytest -q
```

## Aktualizacja yt-dlp

Serwisy często zmieniają sposób publikacji wideo. Jeśli pobieranie przestanie działać:

```bash
python -m pip install -U yt-dlp
```
