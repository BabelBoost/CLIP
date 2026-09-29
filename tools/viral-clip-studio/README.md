# Viral Clip Studio

Lokalna aplikacja do zamiany długiego, pobranego wideo na krótkie klipy dla TikToka, Reels i YouTube Shorts.

## Co robi

1. Przyjmuje lokalny plik MP4, MOV, MKV lub WEBM.
2. Transkrybuje cały film lokalnie przez `faster-whisper`.
3. Szuka samodzielnych fragmentów około 15, 30 i 60 sekund.
4. Nadaje Viral Score 1–10 na podstawie tempa, puenty, napięcia, pytań, zaskoczenia i samodzielności fragmentu.
5. Wybiera TOP 5 bez długich wstępów i bez mocno nakładających się fragmentów.
6. Tworzy timecode, cytat, hook, tekst na ekran, emocję, opis, hashtagi, CTA i sugestię cięcia.
7. Generuje raport Markdown, JSON i CSV.
8. Renderuje pionowy film 1080×1920 z napisami przez FFmpeg.
9. Opcjonalnie ulepsza hooki i copy przez lokalny Ollama. Bez płatnego API.

## Polityka i publicystyka

W trybie `Polityka / publicystyka` aplikacja nie tworzy partyjnych ocen ani perswazyjnych dopisków. Hook bazuje na dosłownej wypowiedzi, a cięcie ma zachować jej sens i kontekst. Ten tryb służy do neutralnego wyboru czytelnych, samodzielnych fragmentów.

## Windows. Najprostszy start

### 1. Zainstaluj wymagania

Potrzebujesz:

- Python 3.11 lub 3.12
- FFmpeg dostępny w zmiennej `PATH`

Po instalacji FFmpeg sprawdź w `cmd`:

```bat
ffmpeg -version
```

### 2. Uruchom aplikację

Kliknij dwa razy:

```text
run_windows.bat
```

Przy pierwszym uruchomieniu program utworzy `.venv` i zainstaluje biblioteki. Potem otworzy Streamlit w przeglądarce.

### 3. Użycie

1. Wybierz pobrany plik wideo.
2. Ustaw język i rodzaj materiału.
3. Kliknij `1. Przeanalizuj cały film`.
4. Przejrzyj TOP 5 i ranking.
5. Kliknij `2. Wyrenderuj pionowe klipy 9:16`.
6. Pobierz gotowe MP4 oraz raport.

## Tryb lokalnego AI przez Ollama

To opcja. Bez Ollama aplikacja nadal działa.

Jeśli masz Ollama, uruchom lokalny model, np. `qwen3:8b`, a w aplikacji zaznacz `Ulepsz hooki lokalnym Ollama`.

## CLI

```bash
python cli.py "C:\\Filmy\\material.mp4" --language pl --mode auto --render 5
```

Dla publicystyki:

```bash
python cli.py "C:\\Filmy\\wywiad.mp4" --language pl --mode public_affairs --render 5
```

Z Ollama:

```bash
python cli.py "C:\\Filmy\\material.mp4" --ollama --ollama-model qwen3:8b --render 5
```

## Wyniki

W katalogu `output/` powstają:

```text
viral_report.md
viral_report.json
viral_ranking.csv
clips/
  clip_01_..._9x16.mp4
  clip_01_....srt
```

## Struktura

```text
viral-clip-studio/
├── app.py
├── cli.py
├── requirements.txt
├── run_windows.bat
├── run_linux_mac.sh
├── prompts/
│   └── viral_analysis_pl.txt
├── tests/
│   └── test_analyzer.py
└── viralclip/
    ├── analyzer.py
    ├── models.py
    ├── renderer.py
    ├── report.py
    └── transcriber.py
```

## Ważne

Używaj materiałów, które masz prawo pobrać, przetwarzać i publikować. Samo znalezienie dobrego fragmentu nie zastępuje weryfikacji praw do nagrania ani sprawdzenia, czy cięcie nie zmienia sensu wypowiedzi.
