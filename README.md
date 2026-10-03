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
  viral-clip-studio/
  iceland-shorts-studio/
  autoshorts-analyzer/
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

### Viral Clip Studio 3.3

Moduł do analizy już pobranego pliku wideo. Transkrybuje cały materiał, wyszukuje samodzielne fragmenty około 15, 30 i 60 sekund, wybiera TOP 5 i przygotowuje raport do TikToka, Reels oraz YouTube Shorts.

Generuje:

- dokładny timecode start i koniec
- rekomendowany czas finalnego klipu: 15, 30 albo 60 sekund
- najmocniejszy cytat
- hook na pierwsze 3 sekundy
- tekst na ekran
- `Viral Score 0–100`
- `Hook Score 0–100`
- `Emotion Score 0–100`
- `Comment Potential 0–100`
- `Retention Score 0–100`
- `Share Potential 0–100`
- `Context Dependency 0–100`, gdzie niżej znaczy lepiej
- automatyczne progi jakości: 85+, 70–84, 55–69 i odrzucenie słabszych fragmentów
- 3 automatyczne warianty hooka dla każdego klipu, scoring 0–100 i wybór najlepszego przed renderowaniem
- emocję i krótkie uzasadnienie
- sugestię dokładnego cięcia
- zsynchronizowane napisy
- opis, hashtagi i CTA
- tabelę TOP 5
- plan montażu najlepszzego klipu sekunda po sekundzie
- pionowe MP4 1080×1920 z napisami

Dla polityki i publicystyki dostępny jest neutralny tryb zachowujący sens oraz kontekst wypowiedzi.

Kod i instrukcja: `tools/viral-clip-studio/`

### AutoShorts Analyzer

Generator angielskich promptów do AutoShorts.ai dla:

- TikTok
- YouTube Shorts
- X
- Facebook Reels

Może działać bez danych historycznych albo analizować CSV z wynikami poprzednich filmów. Oblicza heurystyczny `Viral Score 0–100`, wykrywa najlepszy wzorzec tematu i hooka, a następnie generuje nowe warianty bez kopiowania zwycięskiego filmu.

Analizowane sygnały:

- średni procent obejrzenia
- engagement rate
- wyświetlenia względem własnej próbki
- udostępnienia na 1000 wyświetleń
- komentarze na 1000 wyświetleń
- subskrypcje na 1000 wyświetleń

Każdy prompt zawiera:

- platformę i cel filmu
- hook na 0–2 sekundy
- strukturę historii
- tempo i zmiany wizualne
- wskazówki do napisów
- CTA lub pytanie końcowe
- reguły dokładności faktów
- docelową długość dopasowaną do platformy

Kod i instrukcja: `tools/autoshorts-analyzer/`

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
