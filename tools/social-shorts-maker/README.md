# Babel Boost Social Shorts Maker

Jedna lokalna aplikacja do tworzenia krótkich klipów z filmu na YouTube albo pliku wideo.

Obsługiwane platformy:

- TikTok
- X
- Facebook Reels
- YouTube Shorts

Aplikacja korzysta z silnika Viral Clip Studio znajdującego się obok w repozytorium. Transkrybuje film, ocenia fragmenty, renderuje pionowe klipy 9:16 z napisami i przygotowuje pliki copy dla wybranych platform.

## Windows

1. Zainstaluj Python 3.11 lub 3.12.
2. Zainstaluj FFmpeg i sprawdź poleceniem `ffmpeg -version`.
3. Uruchom `START_WINDOWS.bat`.
4. Wklej link YouTube albo wybierz plik wideo.
5. Wybierz język, długość pracy i platformy.
6. Kliknij `ANALIZUJ I UTWÓRZ KLIPY`.
7. Pobierz klipy osobno lub całą paczkę ZIP.

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

- Pobieraj i przetwarzaj tylko materiały, do których masz prawa lub zgodę.
- Aplikacja obsługuje publiczne linki YouTube. Dostępność zależy od ustawień filmu i serwisu.
- Nie omija DRM ani zabezpieczeń prywatnych materiałów.
- Wynik Viral Score jest oceną heurystyczną, a nie prognozą zasięgu.
- Wideo jest renderowane w formacie pionowym 9:16, 1080×1920, który pasuje do krótkich publikacji na wymienionych platformach.
- Przejrzyj klipy, napisy i copy przed publikacją.
