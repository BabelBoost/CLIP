# Babel Boost Ad Studio

Lokalny edytor reklam z gotowych plików Grok AI i AutoShorts.ai. Polski interfejs otwierany w przeglądarce. Renderowanie na własnym komputerze przez FFmpeg.

## Co potrafi

* Import MP4, MOV, WebM i MKV, również klipów bez dźwięku.
* Zmiana kolejności, pomijanie ujęć i przycinanie z dokładnością do dziesiątych części sekundy.
* Hook z własnym tekstem i czasem wyświetlania.
* Napisy SRT, również polskie znaki. Możliwość poprawienia tekstu i czasu przed eksportem.
* Muzyka zapętlana do długości filmu, osobny plik lektora i oryginalny dźwięk klipów.
* Niezależna regulacja głośności. Ochrona przed przesterowaniem i wygaszenie dźwięku na końcu.
* Plansza końcowa z prawdziwą okładką, tytułem, CTA oraz BabelBoost.com lub własnym adresem.
* MP4 H.264/AAC, 30 fps: 720×1280, 1080×1920, 1920×1080 lub 1080×1080.
* Cały obraz z marginesami albo wypełnienie kadru przez centralne przycięcie.
* Podgląd źródeł i gotowego filmu. Zapis i odczyt ustawień projektu JSON.

Nie wymaga kluczy API. Nie pobiera filmów z kont Grok lub AutoShorts. Nie generuje lektora AI ani transkrypcji. Importuje gotowe nagranie lektora i napisy. Nie usuwa tekstu ani znaków wodnych zapisanych już w obrazie. Łączy ujęcia prostymi cięciami.

## Windows: uruchomienie

1. Pobierz repozytorium jako ZIP z GitHub i rozpakuj je.
2. Zainstaluj Python 3.11 lub 3.12 z https://www.python.org/downloads/windows/ wraz z Python Launcher.
3. W terminalu zainstaluj FFmpeg:

   ```powershell
   winget install --id Gyan.FFmpeg -e
   ```

4. Zamknij terminal po instalacji. Otwórz folder `tools/ad-studio`.
5. Uruchom dwuklikiem `START_WINDOWS.bat`. Pierwszy start instaluje biblioteki i wymaga internetu.
6. Otworzy się lokalny interfejs. Gdy przeglądarka nie otworzy się sama, wejdź na http://localhost:8501.

Program potrzebuje `ffmpeg` oraz `ffprobe` w PATH. Można je także zainstalować ręcznie z dystrybucji wskazanych na https://ffmpeg.org/download.html.

## Linux i macOS

Zainstaluj Python 3.11/3.12, FFmpeg i czcionkę Arial albo DejaVu Sans. Następnie:

```bash
cd tools/ad-studio
bash start.sh
```

Na Ubuntu potrzebne mogą być pakiety `python3-venv`, `ffmpeg`, `fonts-dejavu-core`.
Jeśli czcionka jest w innym miejscu, ustaw zmienną `AD_STUDIO_FONT` na pełną ścieżkę pliku TTF.

## Pierwsza reklama Babel Boost

1. Dodaj ujęcia pobrane z Grok i AutoShorts.
2. W tabeli ustaw: droga, osoba planująca podróż, krajobraz. Odznacz materiały, których nie chcesz używać.
3. Ustaw początek i koniec każdego ujęcia. Kolejność wynika z kolumny „Kolejność”. Przy równych numerach zachowana jest kolejność wczytania.
4. Wpisz hook, np. `Your Iceland plan looks perfect. Until the weather changes.`
5. Dodaj muzykę oraz opcjonalny plik lektora. Lektor rozpoczyna się od 0:00. Jeśli jest dłuższy od filmu, eksport poprosi o zmianę długości zamiast ucinać wypowiedź.
6. Jeśli film AutoShorts zawiera już głos, ustaw „Oryginalny dźwięk klipów” na 1.0. Nie nakładaj drugiego lektora na ten sam fragment.
7. Opcjonalnie wczytaj SRT. Czasy odnoszą się do finalnej osi czasu, już po przycięciu i połączeniu ujęć.
8. Wgraj okładkę PNG/JPG. Ustaw tytuł, CTA i adres sklepu. Zakończenie można wyłączyć wartością 0.
9. Najpierw wybierz 720p. Kliknij „Zmontuj i eksportuj MP4”, obejrzyj wynik i pobierz film.

Gotowy plik nie jest publikowany automatycznie. Zwiększenie rozdzielczości nie odtworzy szczegółów, których nie ma w źródle.

## Projekty i pliki

JSON zawiera ustawienia, kolejność, przycięcia i identyfikatory plików obliczone z ich zawartości. Nie zawiera filmów, muzyki ani okładki. Po odczycie projektu wgraj ponownie te same pliki oraz dodatkowe materiały audio i obraz. Podgląd wynikowy dotyczy ostatniego eksportu; po zmianach wykonaj eksport ponownie.

Źródła nie są nadpisywane. Pliki sesji znajdują się w lokalnym katalogu tymczasowym. Pobierz wynik i JSON przed zamknięciem programu. Po awaryjnym zamknięciu system może pozostawić katalog `babel-ad-studio-*` w folderze tymczasowym.

Limit w launcherze: 500 MB na plik. Limit projektu: 40 ujęć, 10 minut i 150 napisów. Eksport dużego filmu wymaga wolnego miejsca na wersje pośrednie. Dłuższe teksty należy podzielić na kilka napisów. Aplikacja jest przeznaczona do pracy lokalnej, nie jako publiczny serwer z uploadem.

## Testy

```bash
python -m unittest discover -s tools/ad-studio/tests -v
```

Testy integracyjne wymagają FFmpeg. Sprawdzają mieszane proporcje obrazu, brak audio w źródle, muzykę, lektora, okładkę, napisy, długość wyniku, przycięcia i ochronę istniejącego pliku przy błędzie. Testowane w Linux; launcher Windows wymaga Pythona i FFmpeg na komputerze użytkownika.
