# Babel Boost AutoClip Studio

Lokalna aplikacja do tworzenia krótkich filmów z promptu. Używa Pexels do wyszukiwania stockowych filmów i zdjęć, Microsoft Edge TTS do polskiego lub angielskiego lektora oraz FFmpeg do montażu MP4.

**Funkcje MVP**

- Temat lub pełny prompt → scenariusz w języku PL/EN (OpenAI API, opcjonalnie).
- Bez klucza OpenAI: prosty szkic do ręcznej korekty, a nie pełny AI writer.
- Edycja każdego tekstu lektora, napisu na ekranie i frazy wyszukiwania.
- Pexels videos first z przejściem na zdjęcia, albo tryb tylko zdjęcia/wideo.
- Możliwość użycia własnych zdjęć lub filmów zamiast stocku (po jednym na scenę, od początku).
- Polski lub angielski głos TTS i proste, czytelne napisy scenowe (nie są to napisy zsynchronizowane słowo po słowie).
- Format 9:16, 16:9, 1:1, MP4 z dźwiękiem, opcjonalna własna muzyka.
- `sources.json` z linkami do autorów, query i informacją o ilustracyjnym charakterze stocku.
- Długość docelowa 15/30/35/45/60/90 sekund. Gdy lektor mówi dłużej, film się wydłuża, żeby nie urwać narracji.

## Windows, start przez dwuklik

1. Zainstaluj [Python 3.10 lub nowszy](https://www.python.org/downloads/) i zaznacz **Add python.exe to PATH**.
2. Pobierz projekt, rozpakuj katalog `prompt-stock-studio`.
3. Uruchom `START_WINDOWS.bat`. Pierwszy start instaluje biblioteki i FFmpeg przez pakiet `imageio-ffmpeg`.
4. Uzyskaj własny darmowy klucz [Pexels API](https://www.pexels.com/api/). Wpisz go w panelu aplikacji.
5. Opcjonalnie dodaj klucz OpenAI API do tworzenia scenariusza przez AI. Klucze API OpenAI mogą generować koszty.
6. Wpisz prompt, kliknij **Przygotuj scenariusz**, popraw sceny i kliknij **Wygeneruj film MP4**.
7. Pobierz MP4 i listę źródeł; gotowe pliki zostają także w `exports/`.

Do działania potrzebne jest połączenie z internetem dla Pexels, OpenAI (jeśli włączone) i Edge TTS. Obrazy i filmy stock nie są generowane przez sztuczną inteligencję: są wyszukiwane z biblioteki Pexels.

## Przykładowy prompt

> Create a 35-second video about Iceland winter road trips for Babel Boost Iceland. Natural English male voice. Hook in the first 2 seconds. Explain three practical travel tips without inventing current forecasts or incidents. Use illustrative winter landscape and snowy road footage. End with: Follow Babel Boost at BabelBoost.com.

## Źródła i licencja

Pexels API: https://www.pexels.com/api/documentation/  
Licencja: https://www.pexels.com/license/

Nie przedstawiaj wideo stockowego jako autentycznej rejestracji konkretnego wydarzenia, osoby lub daty. W projektach politycznych i informacyjnych zweryfikuj fakty przed publikacją. Unikaj stockowych wizerunków, które mogłyby fałszywie przedstawiać rozpoznawalne osoby w negatywnym kontekście. Dla reklam nie sugeruj poparcia produktu przez osoby na zdjęciach.

Korzystanie z Pexels API wymaga własnego klucza i przestrzegania limitów oraz wytycznych. Narzędzie wyświetla link do Pexels i zapisuje dane autora. Dołącz plik `sources.json` do archiwum projektu, nie trzeba go publikować z filmem.

## Technologia

Python, Streamlit, Pexels REST API, optional OpenAI, edge-tts, Pillow, FFmpeg przez imageio-ffmpeg. Bez zewnętrznego serwera przetrzymującego przesłane pliki. Wynik MP4 zostaje lokalnie.

## Ograniczenia MVP

Nie ma automatycznej weryfikacji prawdziwości newsów, montażu do uderzeń muzyki, pełnych napisów karaoke ani automatycznego publikowania na TikTok i YouTube. Przy niedostępnej frazie Pexels trzeba zmienić słowa wyszukiwania. Automatyczny głos może być niedostępny w zależności od dostawcy i połączenia z internetem.
