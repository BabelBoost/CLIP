# Iceland Shorts Studio

Narzędzie do produkcji anglojęzycznych faceless shortów o Islandii w stylu AutoShorts.

## Co robi

- tworzy temat, hook, voice-over i storyboard,
- może użyć Grok/xAI do generowania skryptu,
- może pobrać pionowe stocki z Pexels,
- może pracować wyłącznie na Twoich własnych nagraniach,
- generuje angielski voice-over przez Edge TTS,
- automatycznie składa ujęcia do 9:16,
- dodaje duże napisy,
- opcjonalnie dodaje muzykę,
- eksportuje MP4 1080 × 1920 do TikTok, Reels i Shorts,
- nie korzysta z OpenCV.

## Najprostsze uruchomienie na Windows

1. Zainstaluj Python 3.11 lub 3.12.
2. Zainstaluj FFmpeg i upewnij się, że działa polecenie `ffmpeg -version`.
3. Pobierz repozytorium.
4. Otwórz folder `tools\iceland-shorts-studio`.
5. Kliknij dwukrotnie `run_windows.bat`.

Skrypt sam utworzy środowisko Python, zainstaluje zależności i uruchomi panel w przeglądarce.

## Tryb bez płatnego API

Nie musisz mieć xAI ani Pexels.

1. Wybierz temat.
2. Zostaw wyłączone „Generuj skrypt przez Grok/xAI”.
3. Kliknij „GENERUJ PROJEKT”.
4. Popraw hook i voice-over.
5. Wgraj własne filmy z Islandii.
6. Kliknij „STWÓRZ GOTOWY MP4”.

## Tryb Auto

Dla bardziej automatycznej produkcji podaj:

- xAI API key, aby Grok tworzył oryginalny skrypt,
- Pexels API key, aby narzędzie pobierało stockowe ujęcia.

Model xAI jest polem edytowalnym w panelu. Dzięki temu można wpisać model aktualnie dostępny na Twoim koncie bez zmiany kodu.

## Pipeline

`topic -> hook -> script -> storyboard -> footage -> voice -> captions -> music -> MP4`

FFmpeg wykonuje cały montaż. Nie jest wymagany OpenCV.

## Założenie jakościowe

Klip ma wyglądać jak prawdziwy materiał podróżniczy o Islandii. Generator ma unikać fałszywych nazw miejsc, tekstu na wygenerowanych znakach, nierealistycznych tablic, niemożliwych sygnalizatorów i ogólnych montaży bez konkretnej porady.

Najlepszą jakość dają własne prawdziwe ujęcia Islandii plus automatyczny skrypt, voice-over, napisy i montaż.
