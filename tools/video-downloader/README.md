# Babel Boost Video Downloader 3.2

Lokalna aplikacja do pracy z własnymi lub dozwolonymi materiałami z YouTube, X/Twitter i Facebooka.

## Co nowego w 3.2 — Smart Viral Clips

Wersja 3.2 rozszerza Smart Clips o ranking **Viral Potential 0–100**. Program tworzy większą pulę kandydatów, analizuje ich transkrypcję i pokazuje najwyżej ocenione fragmenty przed renderowaniem.

Viral Potential bierze pod uwagę:

- mocny hook na początku fragmentu
- pytanie, liczby i konkretne sformułowania
- kontrast i mocne frazy w wypowiedzi
- tempo mowy
- małą ilość ciszy
- obecność twarzy
- ruch i zmiany scen

To ranking heurystyczny. Nie gwarantuje, że film stanie się viralem i nie przewiduje algorytmu TikToka.

## Najprostsze użycie na Windows

1. Otwórz `tools/video-downloader`.
2. Kliknij dwa razy `run_windows.bat`.
3. Wklej link do filmu.
4. Ustaw `Wideo MP4` i `1080p`.
5. Zaznacz `Smart Viral Clips 3.2`.
6. Zostaw `Priorytet viralowy` zaznaczony.
7. Zostaw `Transkrybuj mowę` zaznaczone.
8. Model Whisper: `Base — polecany`.
9. Język: `Auto` albo właściwy język filmu.
10. Kliknij `Pobierz i analizuj`.
11. Program pokaże proponowane fragmenty z wynikiem `Viral Potential`.
12. Obejrzyj każdą propozycję i odznacz słabsze.
13. Kliknij `Renderuj zaznaczone Smart Viral Clips`.
14. Gotowe MP4 1080×1920 pojawią się w sekcji `Pliki`.

## Co pokazuje ranking viralowy

Przy każdej propozycji zobaczysz:

- Viral Potential 0–100
- wynik hooka
- wynik tempa mowy
- procent mowy w klipie
- liczbę słów na sekundę
- krótkie wyjaśnienie, np. `pytanie na początku`, `konkret/liczba`, `mało ciszy`, `dynamiczne tempo mowy`
- tekst z transkrypcji
- podgląd oryginalnego filmu od początku proponowanego fragmentu

## Jak liczony jest Viral Potential

Waga 3.2:

- hook: 30%
- tempo mowy: 22%
- udział mowy / mało ciszy: 20%
- kontrast i mocne frazy: 13%
- dynamika obrazu: 15%

Dynamika obrazu łączy obecność twarzy, ruch i zmiany scen.

## Funkcje odziedziczone z 3.1

- analiza mowy i ciszy przez FFmpeg
- Faster-Whisper do lokalnej transkrypcji
- język Auto / Polski / Angielski / Islandzki
- modele Tiny / Base / Small
- automatyczny plik SRT
- opcjonalne wypalanie napisów w klipie
- podgląd propozycji przed renderowaniem
- ręczny wybór fragmentów
- inteligentne kadrowanie 9:16
- wykrywanie twarzy przez OpenCV
- analiza ruchu i zmian scen

## FFmpeg na Windows

Najprościej:

```powershell
winget install Gyan.FFmpeg
```

Po instalacji uruchom nowy terminal i sprawdź:

```powershell
ffmpeg -version
```

## Faster-Whisper

Przy pierwszym użyciu wybranego modelu program pobierze model językowy. Kolejne uruchomienia korzystają z lokalnej kopii.

## Pozostałe funkcje

- kolejka wielu linków
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
│   ├── speech.py
│   └── viral.py
├── tests/
│   ├── test_core.py
│   ├── test_media.py
│   ├── test_smartclip.py
│   ├── test_speech.py
│   └── test_viral.py
├── requirements.txt
├── requirements-dev.txt
├── run_windows.bat
├── run_linux_mac.sh
├── ROADMAP.md
└── .gitignore
```

## Testy

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

## Aktualizacja yt-dlp

Jeśli pobieranie z YouTube, X albo Facebooka przestanie działać:

```bash
python -m pip install -U yt-dlp
```

## Ważne

Używaj aplikacji wyłącznie do materiałów, które należą do Ciebie, są udostępnione do pobrania albo masz zgodę na ich zapis. Aplikacja nie omija DRM ani zabezpieczeń prywatnych treści. Nie zapisuj w repozytorium cookies, haseł ani tokenów.
