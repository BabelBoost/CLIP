# Viral Clip Studio 3.0

Lokalne narzędzie do automatycznego tworzenia krótkich klipów z długiego materiału wideo.

## Co robi automatycznie

1. Przyjmuje MP4, MOV, MKV, WEBM lub M4V.
2. Transkrybuje cały film lokalnie przez `faster-whisper`.
3. Szuka fragmentów około 15, 30 i 60 sekund.
4. Liczy `Viral Score`, `Hook Score`, `Emotion Score`, `Comment Potential`, `Retention Score` i `Context Dependency`.
5. Wybiera TOP 5 bez mocno nakładających się fragmentów.
6. Tworzy hook na pierwsze 3 sekundy.
7. Generuje krótkie dynamiczne napisy po około 3 słowa.
8. Renderuje każdy klip jako pionowe MP4 1080×1920.
9. Zachowuje cały główny kadr na środku i wypełnia tło rozmytą wersją filmu, zamiast obcinać boki.
10. Koduje H.264 + AAC z `faststart`, gotowe do publikacji w TikToku, Reels i Shorts.
11. Pakuje pięć MP4 do `viral_top5_tiktok.zip`.
12. Nadal zapisuje raport Markdown, JSON i CSV.

## Polityka i publicystyka

Tryb `Polityka / publicystyka` nie dopisuje partyjnych ocen ani perswazyjnych tez. Hook bazuje na źródłowej wypowiedzi, a wybór fragmentu ma zachować sens i możliwie niski `Context Dependency`.

## Windows

Potrzebujesz:

- Python 3.11 lub 3.12
- FFmpeg dostępny w `PATH`

Sprawdzenie FFmpeg:

```bat
ffmpeg -version
```

Uruchom:

```text
run_windows.bat
```

## Najprostsze użycie

1. Wybierz film.
2. Ustaw język. Zwykle `pl`.
3. Dla debat, wywiadów i wypowiedzi politycznych wybierz `Polityka / publicystyka`.
4. Zostaw włączone `Hook przez pierwsze 3 sekundy`, `Dynamiczne napisy` i `Wypal napisy w MP4`.
5. Kliknij `ANALIZUJ I STWÓRZ TOP 5 KLIPÓW`.
6. Program sam zrobi analizę i pięć gotowych MP4.
7. Pobierz klipy osobno albo kliknij `POBIERZ TOP 5 JAKO ZIP`.

## Dynamiczne napisy

Napisy są generowane w ASS i dzielone na krótkie porcje słów. Hook jest wyświetlany osobno przez pierwsze 3 sekundy. Dzięki temu tekst zmienia się szybciej niż klasyczne pełne zdania i lepiej pasuje do krótkiego pionowego wideo.

## CLI

Domyślnie CLI analizuje film i od razu renderuje TOP 5:

```bash
python cli.py "C:\\Filmy\\material.mp4" --language pl --mode auto
```

Publicystyka:

```bash
python cli.py "C:\\Filmy\\wywiad.mp4" --language pl --mode public_affairs
```

Inna liczba klipów:

```bash
python cli.py "C:\\Filmy\\material.mp4" --render 3
```

Bez hooka:

```bash
python cli.py "C:\\Filmy\\material.mp4" --no-hook
```

Klasyczne napisy zamiast dynamicznych:

```bash
python cli.py "C:\\Filmy\\material.mp4" --static-subtitles
```

Bez wypalonych napisów:

```bash
python cli.py "C:\\Filmy\\material.mp4" --no-subtitles
```

## Wyniki

```text
output/
├── viral_report.md
├── viral_report.json
├── viral_ranking.csv
├── viral_top5_tiktok.zip
└── clips/
    ├── clip_01_..._tiktok.mp4
    ├── clip_01_....ass
    ├── clip_02_..._tiktok.mp4
    └── ...
```

## Oceny

Wskaźniki mają skalę 0–100. Dla `Viral`, `Hook`, `Emotion`, `Comment Potential` i `Retention` wyższy wynik jest lepszy. Dla `Context Dependency` lepszy jest wynik niższy.

To ocena heurystyczna, nie gwarancja zasięgu.

## Ważne

Publikuj materiały, do których masz odpowiednie prawa. Przy wycinaniu wypowiedzi sprawdź też, czy skrót nie zmienia znaczenia oryginalnej wypowiedzi.
