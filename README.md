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

### Babel Boost Video Downloader 3.2 — Smart Viral Clips

Lokalne narzędzie Streamlit do pracy z własnymi lub dozwolonymi materiałami z YouTube, X/Twitter i Facebooka.

Obsługuje:

- kolejkę wielu linków
- MP4 i MP3
- wykrywanie twarzy, ruchu i zmian scen
- analizę mowy i ciszy
- lokalną transkrypcję Faster-Whisper
- automatyczne napisy SRT i wypalanie napisów w MP4
- Smart Viral Clips 3.2
- większą pulę kandydatów na klipy
- analizę hooka, pytań, liczb, kontrastu i tempa mowy
- ranking `Viral Potential 0–100`
- krótkie wyjaśnienie, dlaczego fragment dostał wysoki wynik
- podgląd propozycji przed renderowaniem
- ręczny wybór klipów
- inteligentne kadrowanie 9:16
- generowanie MP4 1080×1920
- testy GitHub Actions

`Viral Potential` jest wskaźnikiem heurystycznym, a nie gwarancją popularności lub zasięgu.

Kod i instrukcja: `tools/video-downloader/`

## Zasada pracy

Każdy klip powinien mieć:

- hook na pierwsze sekundy
- scenariusz
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
