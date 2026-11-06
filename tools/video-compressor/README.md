# Babel Boost Video Compressor

Prosta aplikacja okienkowa do zmniejszania rozmiaru plików wideo na Windows.

## Co potrafi

- kompresuje MP4, MOV, MKV, AVI, WEBM i M4V
- zapisuje wynik jako MP4
- ma gotowy tryb TikTok / Reels / YouTube Shorts 1080p
- ma tryb wysokiej jakości
- ma tryby H.265 do mocniejszej kompresji
- pozwala wpisać docelowy rozmiar pliku w MB
- pokazuje postęp kompresji
- po zakończeniu pokazuje rozmiar przed i po kompresji
- działa lokalnie, bez wysyłania filmu do internetu

## Wymagania

1. Windows 10 lub 11
2. Python 3.10 lub nowszy
3. FFmpeg i FFprobe dostępne w PATH

Najprostsza instalacja FFmpeg w PowerShell:

```powershell
winget install Gyan.FFmpeg
```

Po instalacji zamknij i uruchom ponownie terminal.

Sprawdzenie:

```powershell
ffmpeg -version
ffprobe -version
```

## Uruchomienie

Kliknij dwukrotnie:

```
run_windows.bat
```

albo uruchom:

```powershell
python app.py
```

## Jak używać

1. Kliknij **Wybierz plik**.
2. Wybierz tryb kompresji.
3. Opcjonalnie wpisz docelowy rozmiar, np. **100 MB**.
4. Kliknij **KOMPRESUJ WIDEO**.
5. Gotowy plik otrzyma nazwę `nazwa_compressed.mp4`.

## Tryby

### TikTok / Shorts 1080p

H.264, maksymalnie 1080 px szerokości, 30 FPS. Dobry wybór do TikTok, Instagram Reels, Facebook Reels i YouTube Shorts.

### Wysoka jakość

H.264 CRF 20. Zachowuje oryginalną rozdzielczość i daje dobrą jakość.

### Mały plik H.265

H.265 CRF 28, maksymalnie 1280 px szerokości. Zwykle daje znacznie mniejszy plik niż H.264.

### Bardzo mały plik

H.265 CRF 31, maksymalnie 960 px szerokości. Do sytuacji, gdy rozmiar jest ważniejszy niż maksymalna jakość.

## Docelowy rozmiar

Jeśli wpiszesz np. `100`, program obliczy bitrate na podstawie długości filmu i spróbuje utworzyć plik o rozmiarze około 100 MB.

Rzeczywisty wynik może różnić się o kilka procent, ponieważ kompresja wideo nie daje idealnie stałego rozmiaru w jednym przebiegu.

## Prywatność

Całe przetwarzanie odbywa się lokalnie na komputerze.
