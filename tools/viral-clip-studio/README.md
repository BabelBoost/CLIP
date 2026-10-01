# Viral Clip Studio 3.1

Lokalne narzędzie do analizy długiego materiału wideo i automatycznego tworzenia TOP 5 klipów do TikToka, Reels i YouTube Shorts.

## Co robi automatycznie

1. Przyjmuje MP4, MOV, MKV, WEBM lub M4V.
2. Transkrybuje cały film lokalnie przez `faster-whisper`.
3. Pobiera timestamp każdego słowa.
4. Szuka samodzielnych fragmentów około 15, 30 i 60 sekund.
5. Liczy `Viral Score`, `Hook Score`, `Emotion Score`, `Comment Potential`, `Retention Score` i `Context Dependency`.
6. Wybiera TOP 5 bez mocno nakładających się fragmentów.
7. Dodaje hook na pierwsze 3 sekundy.
8. Tworzy dynamiczne napisy.
9. Wyróżnia aktualnie wypowiadane słowo.
10. Wykrywa lokalnie twarz i robi delikatny punch-in/zoom w stronę dominującego mówcy.
11. Jeśli twarz nie zostanie wykryta, stosuje delikatny zoom centralny.
12. Wycina tylko dłuższe pauzy w mowie. Domyślny próg to 0,8 s.
13. Zachowuje krótsze naturalne pauzy, żeby mowa nie brzmiała poszarpanie.
14. Renderuje pion 1080×1920 z rozmytym tłem.
15. Koduje H.264 + AAC + faststart.
16. Generuje osobny plik TXT z hookiem, opisem TikTok, hashtagami i CTA dla każdego klipu.
17. Pakuje pięć MP4 i pięć plików copy do jednego ZIP.

## Jak działa wyróżnianie słów

Whisper zwraca prawdziwy czas początku i końca każdego słowa. Napisy nie są więc dzielone wyłącznie na równe odstępy. W danym momencie jedno aktualnie wypowiadane słowo jest wizualnie wyróżnione w całym krótkim bloku napisów.

Jeżeli timestampy słów nie są dostępne, program automatycznie wraca do bezpiecznego przybliżenia na podstawie segmentu transkrypcji.

## Auto-zoom na twarz / mówcę

OpenCV pobiera kilka klatek z wybranego fragmentu i szuka twarzy. Program wybiera największą widoczną twarz w kolejnych próbkach, wylicza wspólny punkt skupienia i przesuwa powiększony główny kadr w tę stronę.

To jest lokalne rozpoznawanie geometrii twarzy. Narzędzie nie identyfikuje osoby.

## Automatyczne cięcie ciszy

Domyślnie usuwane są pauzy dłuższe niż 0,8 sekundy. Obraz i dźwięk są cięte razem, a timestampy napisów są ponownie przeliczane do nowej osi czasu.

W panelu bocznym można zmienić próg od 0,5 do 1,5 sekundy albo całkiem wyłączyć usuwanie ciszy.

## Polityka i publicystyka

Tryb `Polityka / publicystyka` zachowuje źródłowe znaczenie wypowiedzi. Hook, opis i hashtagi nie mają dopisywać partyjnych ocen ani perswazyjnych tez. Opis przypomina o pełnym kontekście wypowiedzi.

## Windows. Najprostsze użycie

### 1. Wymagania

Potrzebujesz:

- Python 3.11 lub 3.12
- FFmpeg w `PATH`

Sprawdzenie FFmpeg:

```bat
ffmpeg -version
```

### 2. Uruchomienie

Kliknij dwa razy:

```text
run_windows.bat
```

Przy pierwszym uruchomieniu aplikacja utworzy `.venv` i zainstaluje wymagania, w tym OpenCV.

### 3. Tworzenie klipów

1. Wybierz film.
2. Ustaw język.
3. Wybierz `Auto`, `Ogólny` albo `Polityka / publicystyka`.
4. Zostaw domyślnie włączone:
   - hook 0–3 s,
   - dynamiczne napisy,
   - wyróżnianie słowa,
   - auto-zoom na twarz / mówcę,
   - automatyczne usuwanie dłuższych ciszy.
5. Kliknij:

```text
ANALIZUJ I STWÓRZ TOP 5 KLIPÓW
```

Po zakończeniu możesz pobrać każdy MP4 osobno, osobny TXT z opisem i hashtagami albo całą paczkę:

```text
viral_top5_tiktok_3_1.zip
```

## Co znajduje się w ZIP

Przykład:

```text
clip_01_000120_000150_tiktok.mp4
clip_02_000430_000500_tiktok.mp4
clip_03_...
clip_04_...
clip_05_...
clip_01_opis_hashtagi.txt
clip_02_opis_hashtagi.txt
clip_03_opis_hashtagi.txt
clip_04_opis_hashtagi.txt
clip_05_opis_hashtagi.txt
```

Każdy plik TXT zawiera:

```text
HOOK
OPIS TIKTOK
HASHTAGI
CTA
```

## CLI

Domyślny montaż 3.1:

```bash
python cli.py "C:\\Filmy\\material.mp4"
```

Publicystyka:

```bash
python cli.py "C:\\Filmy\\wywiad.mp4" --mode public_affairs
```

Nie usuwaj ciszy:

```bash
python cli.py "C:\\Filmy\\material.mp4" --keep-silence
```

Zmień próg ciszy na 1,1 s:

```bash
python cli.py "C:\\Filmy\\material.mp4" --silence-threshold 1.1
```

Wyłącz zoom:

```bash
python cli.py "C:\\Filmy\\material.mp4" --no-auto-zoom
```

Wyłącz wyróżnianie pojedynczych słów:

```bash
python cli.py "C:\\Filmy\\material.mp4" --no-word-highlight
```

## Wyniki

W `output/` powstają:

```text
viral_report.md
viral_report.json
viral_ranking.csv
viral_top5_tiktok_3_1.zip
clips/
  clip_01_..._tiktok.mp4
  clip_01_....ass
copy/
  clip_01_opis_hashtagi.txt
  ...
```

## Ważne

Używaj materiałów, które masz prawo przetwarzać i publikować. Przy wywiadach, wiadomościach i publicystyce sprawdź, czy skrót nie zmienia sensu pełnej wypowiedzi.
