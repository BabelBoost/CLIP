# Babel Boost Video Downloader 2.0

Lokalna aplikacja do pracy z dozwolonymi materiałami z YouTube, X/Twitter i Facebooka.

## Funkcje 2.0

- wiele linków w jednej kolejce
- podgląd tytułu, autora, długości i miniatury przed pobraniem
- pasek postępu całej kolejki
- MP4 w najlepszej jakości, 1080p, 720p albo 480p
- MP3 192 kb/s
- opcjonalne napisy, w tym napisy automatyczne, jeżeli źródło je udostępnia
- wybór języków napisów, np. `pl,en,is`
- zapis miniatury jako osobnego pliku
- wersja TikTok 9:16 w 1080×1920
- pionowe wideo z rozmytym tłem i pełnym oryginalnym kadrem na środku
- cookies z Chrome, Edge lub Firefox dla treści, do których użytkownik ma legalny dostęp
- automatyczne testy GitHub Actions

## Ważne

Używaj aplikacji wyłącznie do materiałów, które należą do Ciebie, są udostępnione do pobrania albo masz zgodę na ich zapis. Aplikacja nie omija DRM ani zabezpieczeń prywatnych treści.

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

Następnie otwórz nowy terminal i sprawdź:

```powershell
ffmpeg -version
```

## Linux i macOS

```bash
chmod +x run_linux_mac.sh
./run_linux_mac.sh
```

Na macOS:

```bash
brew install ffmpeg
```

## Jak używać kolejki

Wklej kilka linków do pola tekstowego. Każdy może być w osobnym wierszu. Aplikacja usuwa duplikaty i pomija nieobsługiwane domeny.

Najpierw możesz kliknąć `Sprawdź linki`. Zobaczysz tytuł, miniaturę, autora i długość materiału. Potem ustaw format, jakość, napisy, miniaturę i opcję TikTok 9:16. Kliknij `Pobierz kolejkę`.

## TikTok 9:16

Opcja `Przygotuj TikTok 9:16` tworzy dodatkowy plik MP4 1080×1920. Oryginalny obraz nie jest agresywnie przycinany. Film jest skalowany do środka pionowego kadru, a puste miejsce wypełnia rozmyte tło z tego samego materiału.

Ten tryb wymaga FFmpeg.

## Napisy

Po zaznaczeniu `Pobierz napisy` aplikacja próbuje pobrać napisy zwykłe oraz automatyczne. Języki podaje się jako kody oddzielone przecinkami, np.:

```text
pl,en,is
```

Dostępność zależy od źródła.

## Treści wymagające logowania

W aplikacji możesz wybrać Chrome, Edge lub Firefox. `yt-dlp` spróbuje użyć cookies z lokalnej przeglądarki. Nie zapisuj cookies w repozytorium.

## Struktura modułu

```text
video-downloader/
├── app.py
├── downloader/
│   ├── __init__.py
│   ├── core.py
│   └── media.py
├── tests/
│   ├── test_core.py
│   └── test_media.py
├── requirements.txt
├── requirements-dev.txt
├── run_windows.bat
├── run_linux_mac.sh
├── ROADMAP.md
└── .gitignore
```

`app.py` obsługuje interfejs i kolejkę. `downloader/core.py` odpowiada za linki, opcje yt-dlp, napisy, miniatury i pliki wynikowe. `downloader/media.py` przygotowuje pionowe wideo przez FFmpeg.

## Testy

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

## Aktualizacja yt-dlp

YouTube, X i Facebook zmieniają sposób publikacji wideo. Gdy pobieranie przestanie działać, najpierw zaktualizuj yt-dlp:

```bash
python -m pip install -U yt-dlp
```
