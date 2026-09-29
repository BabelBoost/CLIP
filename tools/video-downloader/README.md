# Babel Boost Video Downloader 3.1

Lokalna aplikacja do pracy z własnymi lub dozwolonymi materiałami z YouTube, X/Twitter i Facebooka.

## Co nowego w 3.1

- analiza mowy i ciszy przez FFmpeg
- preferowanie fragmentów, w których faktycznie jest mowa
- lokalna transkrypcja przez Faster-Whisper
- automatyczny plik SRT z rozpoznanym tekstem
- opcjonalne wypalanie napisów bezpośrednio w pionowym Smart Clip
- podgląd proponowanych fragmentów **przed** renderowaniem
- ręczny wybór: zaznaczasz tylko te propozycje, które chcesz utworzyć
- tekst z transkrypcji pokazany obok każdej propozycji
- nadal działa wykrywanie twarzy, ruchu, zmian scen i inteligentne kadrowanie 9:16

## Jak teraz działa Smart Clips 3.1

Ranking fragmentów używa czterech sygnałów:

- obecność twarzy: 35%
- mowa zamiast ciszy: 30%
- ruch: 20%
- zmiany scen: 15%

To ranking heurystyczny. Program nie ocenia prawdziwości ani znaczenia wypowiedzi. Ma znaleźć fragmenty, które są wizualnie aktywne i zawierają mowę.

## Najprostsze użycie na Windows

1. Zainstaluj Python 3.11 lub nowszy.
2. Zainstaluj FFmpeg i dodaj go do PATH.
3. Otwórz folder `tools/video-downloader`.
4. Kliknij dwa razy `run_windows.bat`.
5. Poczekaj, aż otworzy się aplikacja w przeglądarce.
6. Wklej link do filmu.
7. Ustaw `Wideo MP4` i `1080p`.
8. Zaznacz `Smart Clips 3.1`.
9. Zostaw `Transkrybuj mowę` i `Wypal napisy w klipach` zaznaczone.
10. Kliknij `Pobierz i analizuj`.
11. Obejrzyj każdą propozycję. Film zacznie się od proponowanego miejsca.
12. Odznacz propozycje, których nie chcesz.
13. Kliknij `Renderuj zaznaczone Smart Clips`.
14. Gotowe MP4 pojawią się w sekcji `Pliki`.

## Automatyczne napisy

Faster-Whisper działa lokalnie na komputerze. Domyślnie aplikacja używa modelu `base`.

Dostępne tryby:

- `Tiny` — najszybszy, najmniej dokładny
- `Base` — polecany na start
- `Small` — dokładniejszy, ale wolniejszy

Przy pierwszym użyciu wybranego modelu Faster-Whisper musi pobrać pliki modelu z internetu. Kolejne transkrypcje korzystają z lokalnej kopii.

Możesz wybrać język:

- Auto
- Polski
- Angielski
- Islandzki

Aplikacja zapisuje pełną automatyczną transkrypcję jako `*_auto.srt`. Dla każdego renderowanego Smart Clip tworzy też osobny SRT dopasowany czasowo do klipu. Gdy opcja `Wypal napisy w klipach` jest zaznaczona, napisy trafiają bezpośrednio do obrazu.

## Podgląd przed renderowaniem

Wersja 3.1 nie tworzy Smart Clips od razu. Najpierw pokazuje propozycje.

Przy każdej zobaczysz:

- początek i koniec fragmentu
- wynik rankingu
- procent mowy
- procent próbek z twarzą
- poziom ruchu
- tekst wypowiedzi, jeśli transkrypcja się udała
- checkbox `Renderuj ten klip`

Dopiero przycisk `Renderuj zaznaczone Smart Clips` tworzy końcowe pliki 1080×1920.

## FFmpeg na Windows

Najprościej przez Winget:

```powershell
winget install Gyan.FFmpeg
```

Po instalacji zamknij terminal, otwórz go ponownie i sprawdź:

```powershell
ffmpeg -version
```

## Pozostałe funkcje

- wiele linków w jednej kolejce
- podgląd tytułu, autora, długości i miniatury
- MP4: najlepsza jakość, 1080p, 720p, 480p
- MP3 192 kb/s
- pobieranie napisów udostępnionych przez źródło
- pobieranie miniatur
- pełne wideo TikTok 9:16 z rozmytym tłem
- cookies z Chrome, Edge lub Firefox dla treści, do których użytkownik ma legalny dostęp
- raport `smartclip_analysis.json`
- automatyczne testy GitHub Actions

## Struktura modułu

```text
video-downloader/
├── app.py
├── downloader/
│   ├── __init__.py
│   ├── core.py
│   ├── media.py
│   ├── smartclip.py
│   └── speech.py
├── tests/
│   ├── test_core.py
│   ├── test_media.py
│   ├── test_smartclip.py
│   └── test_speech.py
├── requirements.txt
├── requirements-dev.txt
├── run_windows.bat
├── run_linux_mac.sh
├── ROADMAP.md
└── .gitignore
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

## Testy

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

## Aktualizacja yt-dlp

Gdy pobieranie z YouTube, X albo Facebooka przestanie działać, najpierw zaktualizuj yt-dlp:

```bash
python -m pip install -U yt-dlp
```

## Ważne

Używaj aplikacji wyłącznie do materiałów, które należą do Ciebie, są udostępnione do pobrania albo masz zgodę na ich zapis. Aplikacja nie omija DRM ani zabezpieczeń prywatnych treści. Nie zapisuj w repozytorium cookies, haseł ani tokenów.
