# Babel Boost — CLIP

Repozytorium do produkcji krótkich filmów, reklam i materiałów social media.

## Struktura

```text
tiktok/
  pl/
  en/
prompts/
  grok/
  heygen/
ads/
  amazon-kdp/
  naffy/
  babelboost/
templates/
tools/
  video-downloader/
archive/
```

## Narzędzia

### Babel Boost Video Downloader 3.0

Lokalne narzędzie Streamlit do pracy z własnymi lub dozwolonymi materiałami z YouTube, X/Twitter i Facebooka.

Obsługuje:

- kolejkę wielu linków
- podgląd tytułu, autora, długości i miniatury
- MP4 w najlepszej jakości, 1080p, 720p i 480p
- MP3
- napisy zwykłe i automatyczne
- wybór języków napisów
- pobieranie miniatur
- pełne wideo TikTok 9:16 z rozmytym tłem
- Smart Clips 3.0
- wykrywanie twarzy przez OpenCV
- analizę ruchu i zmian scen
- automatyczne propozycje krótkich fragmentów
- inteligentne kadrowanie 9:16 w stronę twarzy
- generowanie 1–5 gotowych klipów 1080×1920
- raport JSON z wynikami analizy
- cookies lokalnej przeglądarki dla treści, do których użytkownik ma legalny dostęp
- testy GitHub Actions

Kod i instrukcja: `tools/video-downloader/`

## Zasada pracy

Każdy klip powinien mieć:

- hook na pierwsze sekundy
- scenariusz
- prompt do generatora wideo
- tekst na ekranie
- CTA
- opis
- hashtagi
- link docelowy

## Ruch sprzedażowy

```text
TikTok
  → profil
  → BabelBoost.com / Naffy / Amazon
  → konkretny ebook
```

## Nazewnictwo

Przykład:

```text
2026-09-iceland-northern-lights-01.md
2026-09-oszustwa-50plus-01.md
```

Nie przechowuj tu haseł, tokenów API, plików cookies ani danych logowania.
