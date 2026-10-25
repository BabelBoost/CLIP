# Babel Boost Grok Scene Editor

Prosty edytor offline do łączenia krótkich scen wygenerowanych w Grok AI. Działa też z klipami z innych generatorów wideo.

## Funkcje

- dodawanie wielu scen i zmiana ich kolejności
- łagodne przejścia albo zwykłe cięcia
- format 9:16 dla TikToka, Reels i Shorts, 16:9 dla YouTube albo 1:1
- tytuł otwierający, etykieta „AI CONCEPT” i napis końcowy
- automatyczne dopasowanie rozmiaru bez rozciągania obrazu
- wyrównanie koloru i płynne przejście dźwięku
- postęp renderowania i przycisk anulowania
- eksport MP4 H.264 z dźwiękiem AAC
- cała praca odbywa się lokalnie. Program nie używa API i nie wysyła klipów do sieci

## Wymagania

1. Python 3.10 lub nowszy.
2. FFmpeg wraz z ffprobe. Oba polecenia muszą być dostępne w systemowym `PATH`.

## Windows

Pobierz i zainstaluj FFmpeg. Dodaj folder `bin` FFmpeg do zmiennej PATH. Następnie uruchom `run_windows.bat`.

Możesz też uruchomić program poleceniem:

```powershell
py -3 scene_editor.py
```

## Linux i macOS

Zainstaluj FFmpeg z menedżera pakietów, a potem uruchom:

```bash
python3 scene_editor.py
```

## Montaż

1. Kliknij „Dodaj sceny” i wybierz klipy w kolejności opowiadanej historii.
2. Zmieniaj kolejność przyciskami „W górę” i „W dół”.
3. Ustaw format, czas przejścia oraz napisy.
4. Wybierz nazwę pliku i kliknij „Zmontuj klip”.

Czas przejść jest odejmowany od łącznej długości filmu. Sceny bez ścieżki dźwiękowej otrzymają ciszę, dzięki czemu cały montaż zachowa równą długość. Plik wynikowy nie może nadpisać jednego z plików źródłowych.

## Ograniczenia

- Program montuje dostarczone klipy. Nie generuje nowych scen ani głosu AI.
- Napisy ekranowe są tekstem z tytułu, etykiety i zakończenia. Nie tworzy automatycznej transkrypcji.
- Wymagany jest FFmpeg z filtrem `drawtext`, aby renderować napisy.
