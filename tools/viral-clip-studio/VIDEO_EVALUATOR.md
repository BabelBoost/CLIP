# Viral Video Evaluator 1.0

Osobny tryb Viral Clip Studio do oceny całego materiału wideo i wyszukiwania fragmentów o największym potencjale na TikTok, Reels i YouTube Shorts.

## Co analizuje

Program transkrybuje cały film i szuka fragmentów około 15, 30 i 60 sekund. Następnie każdy kandydat otrzymuje ocenę 0–100 według 10 kryteriów:

1. Mocna, kontrowersyjna lub zaskakująca wypowiedź.
2. Emocje: śmiech, zdziwienie, oburzenie, niedowierzanie lub napięcie.
3. Krótkie zdanie, które może działać jako hook.
4. Sprzeczność, absurd, pomyłka lub niezręczna odpowiedź.
5. Mocna odpowiedź na pytanie.
6. Zrozumiałość bez oglądania całego filmu.
7. Potencjał do komentarzy i dyskusji.
8. Potencjał do hooka typu „Czy naprawdę to powiedział?”.
9. Możliwość rozpoczęcia od najmocniejszego zdania i pokazania kontekstu później.
10. Nagła zmiana tonu, emocji albo tematu.

Końcowy wynik `OCENA VIRAL` jest średnią z 10 kryteriów. Narzędzie korzysta też z istniejących wyników Viral Clip Studio: Hook Score, Emotion Score, Comment Potential, Retention Score i Context Dependency.

## Wynik dla każdego fragmentu

Raport zawiera:

```text
NUMER KLIPU
TIMECODE START
TIMECODE KONIEC
DŁUGOŚĆ
REKOMENDOWANA WERSJA 15 / 30 / 60 s
CYTAT / NAJMOCNIEJSZE ZDANIE
HOOK NA PIERWSZE 3 SEKUNDY
TEKST NA EKRAN
OCENA VIRAL 0–100
OCENY 10 KRYTERIÓW
DLACZEGO TEN FRAGMENT
SUGEROWANE CIĘCIE
```

## Windows. Uruchomienie jednym kliknięciem

W folderze `tools/viral-clip-studio` kliknij dwa razy:

```text
run_evaluator_windows.bat
```

Skrypt utworzy środowisko `.venv`, zainstaluje wymagane biblioteki i uruchomi stronę w przeglądarce.

## Jak używać

1. Wybierz film MP4, MOV, MKV, WEBM lub M4V.
2. Wybierz język.
3. Wybierz rodzaj materiału: Auto, Ogólny albo Polityka / publicystyka.
4. Ustaw liczbę wyników od 5 do 20.
5. Kliknij `ANALIZUJ CAŁE WIDEO`.
6. Otwórz wybrane klipy w rankingu.
7. Pobierz raport Markdown lub JSON.

## Pliki

```text
evaluator_app.py
viralclip/evaluator.py
run_evaluator_windows.bat
VIDEO_EVALUATOR.md
```

## Wymagania

Potrzebujesz Python 3.11 lub 3.12 oraz FFmpeg dostępnego w `PATH`.

Sprawdzenie:

```bat
ffmpeg -version
```

## Uwaga do publicystyki

Tryb `Polityka / publicystyka` zachowuje źródłowe znaczenie wypowiedzi. Ocena dotyczy konstrukcji klipu i potencjału zaangażowania, a nie oceny osób, partii ani stanowisk politycznych.
