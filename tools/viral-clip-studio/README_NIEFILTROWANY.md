# NieFiltrowanyPL AutoClip Studio

Lokalny panel Streamlit do automatycznego przygotowania krótkich filmów z oryginalnych wypowiedzi polityków. Wykorzystuje silnik Viral Clip Studio z repozytorium.

## Funkcje

1. Wczytaj własny lub dozwolony plik MP4/MOV/MKV/WEBM/M4V albo dozwolony link YouTube.
2. Wygeneruj polską transkrypcję z czasami wypowiedzi przez Faster-Whisper.
3. Wybierz maksymalnie pięć propozycji 20–35 sekund. Otrzymasz cytaty, czas początku i końca oraz ocenę montażową (heurystyka, nie przewidywanie wyświetleń).
4. Zaznacz klipy do eksportu, zmień hook i napisz własny komentarz.
5. Jednym przyciskiem wygeneruj pionowy MP4 1080 × 1920, napisy na wideo, dodatkowe SRT, osobną planszę z wyraźnie oznaczonym komentarzem oraz plik TXT z opisem.
6. Opcjonalnie włącz polskiego lektora AI `pl-PL-MarekNeural` przez Edge TTS. Wymaga połączenia z internetem i dostępności usługi. Bez niego komentarz jest widoczny jako tekst, bez narracji.
7. Pobierz pojedyncze filmy albo zbiorczy ZIP.

Program **nie publikuje filmów automatycznie**, **nie sprawdza prawdziwości cytatów** i **nie gwarantuje praw do materiałów**. Przegląd redakcyjny jest obowiązkowy. Fragment oryginalny jest pokazany w normalnej kolejności, bez automatycznego usuwania pauz. Hook jest tekstem redakcyjnym, nigdy udawanym cytatem.

## Windows 11: uruchamianie

Wymagania: Python 3.11 lub 3.12, FFmpeg i FFprobe w PATH, około 8 GB RAM lub więcej.

1. Pobierz repozytorium ze wskazanej gałęzi albo po scaleniu PR z gałęzi main.
2. Otwórz folder `tools/viral-clip-studio`.
3. Kliknij dwukrotnie `run_niefiltrowany_windows.bat`.
4. Instalator utworzy `.venv` i pobierze biblioteki Python. Przy pierwszej transkrypcji pobierze też model Whisper.
5. W przeglądarce wybierz plik lub link. Model `base` działa szybciej na słabszym laptopie, `small` może dawać lepszą transkrypcję.
6. Kliknij `ANALIZUJ I ZNAJDŹ FRAGMENTY`.
7. Zaznacz klipy, sprawdź hook i komentarz, uzupełnij link źródłowy, potwierdź prawa do nagrania.
8. Kliknij `GENERUJ MP4 + POLSKIE NAPISY + ZIP` i pobierz paczkę.

Ręczne uruchomienie:

```bat
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-niefiltrowany.txt
.venv\Scripts\python -m streamlit run niefiltrowany_app.py
```

FFmpeg:

```bat
ffmpeg -version
ffprobe -version
```

Streamlit ma limit pliku 2 GB w `.streamlit/config.toml`. Pliki są przetwarzane lokalnie, więc przy dużych nagraniach potrzebne jest wolne miejsce na dysku, a render może długo obciążać procesor.

## Format eksportu

```text
niefiltrowany_autoclip.zip
  clip_01/
    niefiltrowany_01_final.mp4
    clip_01.srt
    niefiltrowany_01_opis.txt
  clip_02/
    ...
```

Dodatkowa plansza jest podpisana `NIEFILTROWANYPL | KOMENTARZ`. Polski głos syntetyczny nie udaje żadnego polityka. Nie używaj tego narzędzia do tworzenia fałszywych cytatów, nie wprowadzaj w błąd przy porównywaniu wypowiedzi.

## Testy

```bat
.venv\Scripts\python -m pip install pytest
.venv\Scripts\python -m pytest -q tests/test_niefiltrowany_export.py
```

## Ograniczenia

- Narzędzie nie zastępuje fact-checkingu, nie wykrywa samodzielnie fałszywych stwierdzeń i nie pobiera automatycznie materiałów ze wszystkich platform.
- Nagrane wypowiedzi mogą być chronione prawami autorskimi. Samo podanie źródła nie daje zgody na publikację.
- Przed publikacją trzeba obejrzeć cały kontekst, zweryfikować datę, nazwiska i poprawić błędy Whisper.
- Generowany plik SRT dotyczy wyłącznie fragmentu źródłowego. Końcowa plansza komentarza ma tekst na obrazie.
- Wideo i lektor AI powstają lokalnie lub z opcjonalnym połączeniem do usługi TTS. Nie ma integracji z TikTok API.
