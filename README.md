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

### Babel Boost Video Downloader

Lokalne narzędzie Streamlit do pobierania własnych lub dozwolonych materiałów z YouTube, X/Twitter i Facebooka.

Obsługuje:

- MP4
- 1080p, 720p i 480p
- MP3
- cookies lokalnej przeglądarki dla treści, do których użytkownik ma legalny dostęp

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
