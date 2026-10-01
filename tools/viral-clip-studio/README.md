# Viral Clip Studio 2.0

Lokalna aplikacja do oceny długiego materiału wideo i wyboru fragmentów z największym potencjałem na TikTok, Reels i YouTube Shorts.

## Co robi

1. Przyjmuje lokalny plik MP4, MOV, MKV, WEBM lub M4V.
2. Transkrybuje cały film lokalnie przez `faster-whisper`.
3. Szuka samodzielnych fragmentów około 15, 30 i 60 sekund.
4. Dla każdego fragmentu liczy osobne wskaźniki w skali 0–100:
   - `Viral Score`
   - `Hook Score`
   - `Emotion Score`
   - `Comment Potential`
   - `Retention Score`
   - `Context Dependency`
5. `Context Dependency` działa odwrotnie. Im niższy wynik, tym lepiej fragment działa bez oglądania wcześniejszej części filmu.
6. Dobiera rekomendowany czas finalnego klipu: 15, 30 albo 60 sekund.
7. Tworzy mocny hook na pierwsze 3 sekundy.
8. Tworzy krótki tekst na ekran.
9. Podaje dokładny timecode start i koniec.
10. Generuje cytat, emocję, opis, hashtagi, CTA i sugestię cięcia.
11. Wybiera TOP 5 bez mocno nakładających się fragmentów.
12. Generuje raport Markdown, JSON i CSV.
13. Renderuje pionowy film 1080×1920 z napisami przez FFmpeg.
14. Opcjonalnie ulepsza hooki i copy przez lokalny Ollama. Bez płatnego API.

## Jak liczony jest Viral Score

Wynik 0–100 jest wskaźnikiem heurystycznym. Uwzględnia między innymi siłę pierwszego zdania, emocję, pytania i kontrast, tempo wypowiedzi, potencjał komentarzy, utrzymanie uwagi oraz to, czy fragment jest zrozumiały bez dużego kontekstu.

Nie jest to gwarancja wyświetleń ani zasięgu.

## Polityka i publicystyka

W trybie `Polityka / publicystyka` aplikacja nie dopisuje partyjnych ocen ani perswazyjnych tez. Hook bazuje na źródłowej wypowiedzi, a cięcie ma zachować jej sens i kontekst.

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
4. Sprawdź TOP 5 oraz sześć wskaźników każdego fragmentu.
5. Zwróć uwagę szczególnie na wysoki `Hook Score`, `Comment Potential` i `Retention Score` oraz niski `Context Dependency`.
6. Skopiuj proponowany hook i tekst na ekran albo od razu wyrenderuj klip.
7. Kliknij `2. Wyrenderuj pionowe klipy 9:16`.
8. Pobierz gotowe MP4 i raport.

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

## Ważne

Używaj materiałów, które masz prawo pobrać, przetwarzać i publikować. Samo znalezienie dobrego fragmentu nie zastępuje sprawdzenia praw do nagrania ani weryfikacji, czy cięcie nie zmienia sensu wypowiedzi.
