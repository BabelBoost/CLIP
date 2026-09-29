# Babel Boost Video Downloader 3.0

Lokalna aplikacja do pracy z dozwolonymi materiałami z YouTube, X/Twitter i Facebooka.

## Funkcje 3.0

- wiele linków w jednej kolejce
- podgląd tytułu, autora, długości i miniatury przed pobraniem
- pasek postępu całej kolejki
- MP4 w najlepszej jakości, 1080p, 720p albo 480p
- MP3 192 kb/s
- opcjonalne napisy zwykłe i automatyczne, jeżeli źródło je udostępnia
- wybór języków napisów, np. `pl,en,is`
- zapis miniatury jako osobnego pliku
- pełna wersja TikTok 9:16 w 1080×1920 z rozmytym tłem
- Smart Clips 3.0 z wykrywaniem twarzy przez OpenCV
- automatyczne propozycje krótkich fragmentów na podstawie twarzy, ruchu i zmian scen
- inteligentne kadrowanie 9:16 z przesunięciem kadru w stronę wykrytej twarzy
- automatyczne generowanie 1–5 gotowych pionowych klipów
- raport `smartclip_analysis.json` z oceną i czasami wybranych fragmentów
- cookies z Chrome, Edge lub Firefox dla treści, do których użytkownik ma legalny dostęp
- automatyczne testy GitHub Actions

## Jak działa Smart Clips

Smart Clips analizuje próbki obrazu z filmu. Dla każdej próbki sprawdza obecność twarzy, ilość ruchu i zmianę sceny. Następnie tworzy nakładające się okna czasowe, nadaje im wynik i wybiera najwyżej ocenione fragmenty bez wzajemnego nakładania.

Waga rankingu:

- obecność twarzy: 50%
- ruch: 32%
- zmiany scen: 18%

To ranking heurystyczny. Nie rozumie znaczenia wypowiedzi ani nie ocenia treści merytorycznej. Dlatego najlepszy fragment według algorytmu oznacza fragment najbardziej aktywny wizualnie według tych kryteriów.

## Inteligentne kadrowanie 9:16

Jeżeli film jest poziomy, aplikacja wykrywa położenie największej twarzy w analizowanych klatkach. Dla wybranego fragmentu oblicza medianę położenia twarzy i przesuwa pionowy crop w jej stronę. Gdy twarz nie zostanie wykryta, używany jest środek kadru.

Gotowe Smart Clips mają format MP4 1080×1920.

## Ważne

Używaj aplikacji wyłącznie do materiałów, które należą do Ciebie, są udostępnione do pobrania albo masz zgodę na ich zapis. Aplikacja nie omija DRM ani zabezpieczeń prywatnych treści.

## Windows

1. Zainstaluj Python 3.11 lub nowszy.
2. Zainstaluj FFmpeg i dodaj go do PATH.
3. Otwórz folder `tools/video-downloader`.
4. Uruchom `run_windows.bat`.
5. Aplikacja otworzy się w przeglądarce.

Przy pierwszym uruchomieniu zostaną zainstalowane również OpenCV i NumPy potrzebne do Smart Clips.

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

## Jak używać Smart Clips 3.0

1. Wklej link lub kilka linków.
2. Wybierz `Wideo MP4`.
3. Zaznacz `Smart Clips 3.0`.
4. Ustaw liczbę klipów od 1 do 5.
5. Ustaw długość klipu od 10 do 45 sekund.
6. Wybierz dokładność analizy.
7. Kliknij `Pobierz i przetwórz`.
8. Pobierz gotowe pliki `*_smartclip_XX_9x16.mp4`.

Aplikacja pokaże również czas początku i końca fragmentu, wynik rankingu oraz procent próbek z wykrytą twarzą.

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
│   ├── media.py
│   └── smartclip.py
├── tests/
│   ├── test_core.py
│   ├── test_media.py
│   └── test_smartclip.py
├── requirements.txt
├── requirements-dev.txt
├── run_windows.bat
├── run_linux_mac.sh
├── ROADMAP.md
└── .gitignore
```

`app.py` obsługuje interfejs i kolejkę. `downloader/core.py` odpowiada za linki, yt-dlp, napisy, miniatury i pliki wynikowe. `downloader/media.py` tworzy bezpieczną pełną wersję 9:16 z rozmytym tłem. `downloader/smartclip.py` odpowiada za wykrywanie twarzy, analizę ruchu i scen, ranking fragmentów oraz inteligentne kadrowanie.

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
