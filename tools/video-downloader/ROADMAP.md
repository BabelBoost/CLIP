# Roadmap

## v2.0 — gotowe

- kolejka wielu linków
- pasek postępu całej kolejki
- podgląd tytułu, autora, długości i miniatury
- pobieranie miniatur i napisów
- pełna wersja TikTok 9:16 w 1080×1920
- testy modułów oraz GitHub Actions

## v3.0 — gotowe

- wykrywanie twarzy przez OpenCV
- analiza ruchu i zmian scen
- ranking kandydatów na krótkie klipy
- inteligentne kadrowanie poziomego materiału do 9:16
- generowanie MP4 1080×1920
- raport JSON

## v3.1 — gotowe

- analiza mowy i ciszy
- Faster-Whisper do lokalnej transkrypcji
- automatyczne i wypalane napisy
- podgląd propozycji przed renderowaniem
- ręczne zaznaczanie klipów

## v3.2 — gotowe: Smart Viral Clips

- większa pula kandydatów na klipy
- analiza tekstu transkrypcji
- ocena hooka na początku fragmentu
- wykrywanie pytań, liczb, kontrastu i mocnych fraz
- analiza tempa mowy i słów na sekundę
- premiowanie małej ilości ciszy
- połączenie sygnałów tekstowych, audio i obrazu
- `Viral Potential 0–100`
- krótkie wyjaśnienie, dlaczego fragment dostał wysoki wynik
- ranking najlepszych propozycji przed renderowaniem
- testy `test_viral.py`

Viral Potential jest wskaźnikiem heurystycznym i nie gwarantuje popularności ani zasięgu.

## v3.3

- śledzenie twarzy w czasie zamiast jednego położenia dla całego fragmentu
- płynne przesuwanie kadru za rozmówcą
- wykrywanie kilku rozmówców
- tryb split-screen przy dwóch osobach
- możliwość ręcznej korekty początku i końca propozycji

## v3.4

- automatyczne łamanie napisów do 1–2 krótkich linii
- style napisów TikTok / clean / bold
- podświetlanie aktualnie wypowiadanego słowa
- bezpieczne strefy dla elementów interfejsu TikToka

## v4.0

- głębsza analiza semantyczna transkrypcji
- automatyczne propozycje hooków i tytułów
- opis i hashtagi do klipu
- eksport paczki do katalogu `tiktok/`
- opcjonalna aplikacja desktopowa

## Zasady bezpieczeństwa

- brak zapisywania cookies w repozytorium
- brak tokenów i haseł w kodzie
- brak mechanizmów omijających DRM
- pobieranie i obróbka wyłącznie materiałów, do których użytkownik ma prawo lub zgodę
