# Babel Boost Social Shorts Maker

Aplikacja do tworzenia krótkich klipów z filmu YouTube albo przesłanego pliku wideo.

Obsługiwane platformy:

- TikTok
- X
- Facebook Reels
- YouTube Shorts

Aplikacja transkrybuje film, ocenia fragmenty, renderuje pionowe klipy 9:16 z napisami i przygotowuje pliki copy dla wybranych platform. Przesyłanie plików jest ustawione na maksymalnie 1 GB.

Domyślny format TikTok `@niefiltrowanypl` wybiera fragmenty 20–35 s, w których najmocniejsze zdanie pada na początku. Raport zawiera trzy hooki ekranowe z oznaczeniem najlepszego, klikalne timecode'y dla źródła YouTube, plan cięć, transkrypcję napisów, osobno oznaczony komentarz autora, opis i cztery hashtagi. Jeśli mocnego fragmentu nie ma, aplikacja wyświetla informację zamiast wymuszać wybór.

Analiza i montaż działają jako osobny proces. Możesz odświeżyć stronę albo otworzyć ją ponownie, a stan zadania będzie widoczny pod tym samym adresem. Pliki tymczasowe i wyniki są przechowywane przez 7 dni w folderze tymczasowym systemu.

## Windows

1. Zainstaluj Python 3.11 lub 3.12.
2. Zainstaluj FFmpeg i sprawdź w terminalu poleceniem `ffmpeg -version`.
3. Uruchom `START_WINDOWS.bat`. Skrypt utworzy środowisko aplikacji i zainstaluje wymagane biblioteki.
4. Wybierz jedno źródło: publiczny link YouTube albo plik wideo do 1 GB.
5. Wybierz język, model, próg wyniku i platformy.
6. Kliknij `URUCHOM ANALIZĘ I TWORZENIE KLIPÓW`.
7. Pobierz gotowe MP4 osobno albo całą paczkę ZIP.

Przy pierwszym uruchomieniu transkrypcji Faster-Whisper pobierze wybrany model. Model `tiny` jest najszybszy, a `base` daje lepszy wynik. Po pobraniu filmu z YouTube aplikacja wybiera gotowy plik wideo z dźwiękiem. Pliki są obrabiane lokalnie.

## Skrót na pulpicie

Pliki `UTWORZ_SKROT_NA_PULPICIE.ps1` i `social-shorts-maker.ico` znajdują się obok `START_WINDOWS.bat`.

Kliknij prawym przyciskiem skrypt PowerShell i wybierz `Uruchom za pomocą programu PowerShell`. Na pulpicie powstanie skrót z ikoną. Skrót uruchamia aplikację.

## Linux i macOS

W katalogu modułu uruchom:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

FFmpeg musi być dostępny w PATH.

## Uwagi

- Przetwarzaj materiały, do których masz prawa lub zgodę.
- Obsługiwane są publiczne linki YouTube. Dostępność zależy od ustawień filmu i serwisu.
- Aplikacja nie omija DRM ani zabezpieczeń prywatnych materiałów.
- Viral Score to ranking heurystyczny, nie prognoza zasięgu.
- Wideo jest renderowane w formacie pionowym 9:16, 1080×1920.
- Przed publikacją przejrzyj klipy, napisy i opisy.
