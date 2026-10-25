# TikTok Clip Finder dla @niefiltrowanypl

Osobny ekran do analizy własnego pliku wideo lub linku YouTube. Wybiera maksymalnie pięć propozycji o długości 20–35 sekund i przygotowuje dokładne timecode’y, cytat z transkrypcji, trzy krótkie hooki, plan cięć, napisy, komentarz, opis oraz cztery hashtagi.

## Jak uruchomić w Windows

1. Zainstaluj Python 3.11 lub 3.12 oraz FFmpeg.
2. Otwórz folder `tools/viral-clip-studio` w terminalu.
3. Uruchom `run_niefiltrowany_windows.bat`.
4. Przy pierwszym uruchomieniu skrypt utworzy środowisko Python i zainstaluje wymagane biblioteki.
5. Aplikacja otworzy się w przeglądarce. Wybierz plik lub wklej link YouTube, ustaw język i kliknij analizę.

Możesz też uruchomić ręcznie:

```bat
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-niefiltrowany.txt
.venv\Scripts\python -m streamlit run niefiltrowany_app.py
```

Transkrypcja działa lokalnie przez Faster-Whisper. Pierwsze uruchomienie może pobrać model. Większy model zwykle lepiej rozpoznaje mowę, ale działa wolniej.

## Zasady oceny

- Narzędzie szuka fragmentów 20–35 sekund.
- Ocena 0–100 jest heurystyką dotyczącą budowy klipu. Nie przewiduje zasięgu i nie sprawdza prawdziwości wypowiedzi.
- Hook oznaczony jako cytat pochodzi z transkrypcji. Pozostałe hooki są propozycjami tekstu ekranowego, nie cytatami.
- Jeśli cytat zaczyna się później niż 3 sekundy po starcie, najlepszym hookiem na otwarcie jest tekst redakcyjny. Aplikacja ostrzega, by nie przedstawiać go jako słów wypowiedzianych na początku.
- Napisy i timecode’y trzeba sprawdzić z oryginalnym dźwiękiem przed publikacją.
- Jeśli wszystkie kandydaty są słabe, aplikacja to pokaże. Nie traktuj niskiego wyniku jako rekomendacji publikacji.

Pobieraj i przetwarzaj tylko materiały, do których masz prawa lub których użycie jest dozwolone. Link YouTube jest źródłem filmu do lokalnej analizy; narzędzie nie publikuje klipów.
