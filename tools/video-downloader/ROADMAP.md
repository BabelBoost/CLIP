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
- wybór 1–5 niepokrywających się fragmentów
- inteligentne kadrowanie poziomego materiału do 9:16
- generowanie MP4 1080×1920
- raport JSON

## v3.1 — gotowe

- analiza mowy i ciszy przez FFmpeg `silencedetect`
- udział mowy jako część rankingu Smart Clips
- Faster-Whisper do lokalnej automatycznej transkrypcji
- modele Tiny, Base i Small
- język Auto / PL / EN / IS
- pełna transkrypcja SRT
- osobne SRT dopasowane do każdego Smart Clip
- opcjonalne wypalanie automatycznych napisów w MP4
- podgląd proponowanych fragmentów przed renderowaniem
- tekst transkrypcji obok propozycji
- ręczne zaznaczanie klipów do renderowania
- ranking 3.1: twarz 35%, mowa 30%, ruch 20%, sceny 15%
- testy analizy ciszy, SRT i napisów

## v3.2

- śledzenie twarzy w czasie zamiast jednego położenia dla całego fragmentu
- płynne przesuwanie kadru za rozmówcą
- wykrywanie kilku rozmówców
- tryb split-screen przy dwóch osobach
- możliwość ręcznej korekty początku i końca propozycji

## v3.3

- automatyczne łamanie napisów do 1–2 krótkich linii
- style napisów TikTok / clean / bold
- podświetlanie aktualnie wypowiadanego słowa
- bezpieczne strefy dla elementów interfejsu TikToka

## v4.0

- analiza treści transkrypcji
- ranking fragmentów również na podstawie wypowiedzi
- automatyczne hooki i tytuły
- opis i hashtagi do klipu
- eksport paczki do katalogu `tiktok/`
- opcjonalna aplikacja desktopowa

## Zasady bezpieczeństwa

- brak zapisywania cookies w repozytorium
- brak tokenów i haseł w kodzie
- brak mechanizmów omijających DRM
- pobieranie i obróbka wyłącznie materiałów, do których użytkownik ma prawo lub zgodę
