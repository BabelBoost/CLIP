# Roadmap

## v2.0 — gotowe

- kolejka wielu linków
- pasek postępu całej kolejki
- podgląd tytułu, autora, długości i miniatury
- pobieranie miniatur
- pobieranie napisów zwykłych i automatycznych
- wybór języków napisów
- pełna wersja TikTok 9:16 w 1080×1920
- rozmyte tło i zachowanie pełnego oryginalnego kadru
- testy modułów oraz GitHub Actions

## v3.0 — gotowe

- wykrywanie twarzy przez OpenCV
- analiza ruchu i zmian scen
- ranking kandydatów na krótkie klipy
- wybór 1–5 niepokrywających się fragmentów
- długość klipu 10–45 sekund
- inteligentne kadrowanie poziomego materiału do 9:16
- przesunięcie cropu w stronę wykrytej twarzy
- fallback do środka kadru, gdy twarz nie została wykryta
- generowanie gotowych MP4 1080×1920
- raport JSON z wynikami analizy
- trzy poziomy dokładności analizy
- testy Smart Clips w GitHub Actions

## v3.1

- analiza energii dźwięku i wykrywanie ciszy
- preferowanie fragmentów z wyraźną mową
- opcjonalne wypalanie pobranych napisów w Smart Clips
- ręczne zatwierdzanie proponowanych przedziałów przed renderowaniem

## v3.2

- śledzenie twarzy w czasie zamiast jednego położenia dla całego fragmentu
- płynne przesuwanie kadru za rozmówcą
- wykrywanie kilku rozmówców
- tryb split-screen przy dwóch osobach

## v4.0

- lokalna transkrypcja mowy
- ranking fragmentów również na podstawie treści wypowiedzi
- automatyczne hooki i tytuły do klipów
- eksport paczki klipu do katalogu `tiktok/`
- opcjonalna aplikacja desktopowa

## Zasady bezpieczeństwa

- brak zapisywania cookies w repozytorium
- brak tokenów i haseł w kodzie
- brak mechanizmów omijających DRM
- pobieranie i obróbka wyłącznie materiałów, do których użytkownik ma prawo lub zgodę
