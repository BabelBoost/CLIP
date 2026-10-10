# NieFiltrowanyPL Podcast Studio

Lokalna aplikacja na Windows do produkcji podcastów wideo bez pokazywania prowadzącego. Dla kanału https://www.youtube.com/@NieFiltrowanyPL.

## Funkcje
- Edytor scenariuszy po polsku oraz import TXT.
- Opcjonalny lokalny model AI Ollama do napisania roboczego scenariusza.
- Głos Windows (SAPI, zainstalowany w systemie) lub import własnego MP3/WAV/M4A.
- Grafiki JPG/PNG z własnego folderu lub plansze generowane automatycznie.
- Eksport: YouTube MP4 1280x720, audio WAV, napisy SRT, scenariusz TXT, opis filmu.
- Brak płatnych API. Bez chmury. Bez nagrywania twarzy.

## Instalacja Windows
1. Zainstaluj Python 3.11 lub 3.12, zaznacz **Add Python to PATH**.
2. Zainstaluj FFmpeg i dodaj programy ffmpeg oraz ffprobe do PATH.
3. Pobierz folder projektu, uruchom START_WINDOWS.bat.
4. Wpisz scenariusz albo wybierz **Wczytaj scenariusz TXT**.
5. Dla własnego głosu wskaż WAV/MP3. W przeciwnym razie program użyje syntezatora Windows. Do polskiej narracji zainstaluj polski głos w Windows.
6. Opcjonalnie wskaż folder z posiadanymi zdjęciami.
7. Kliknij **RENDERUJ PODCAST**. Pliki pojawią się w folderze output.

## Opcjonalne AI
Zainstaluj Ollama (https://ollama.com), a następnie w terminalu:
\`\`\`
ollama pull gemma3:1b
ollama serve
\`\`\`
Jeśli Ollama jest już uruchomiony, drugie polecenie nie jest potrzebne. Kliknij **AI: napisz scenariusz**. Model 1B jest wariantem oszczędnym dla 8 GB RAM, ale jakość polszczyzny i poprawność faktów wymagają ręcznej kontroli.

## Ograniczenia
- Napisy SRT są rozkładane proporcjonalnie do liczby słów, a nie rozpoznawane z nagrania. Przed publikacją skontroluj synchronizację.
- Brak automatycznego wyszukiwania źródeł. **Sprawdzaj cytaty, daty, liczby i materiały przed publikacją.**
- Przy braku polskiego głosu Windows TTS może czytać po polsku z obcym akcentem. Najlepszy efekt daje import własnego głosu.
- Materiały źródłowe i zdjęcia wykorzystuj zgodnie z licencją.
- Domyślnie 720p, aby render na 8 GB RAM był lżejszy.
- Projekt nie wysyła wideo automatycznie do YouTube. Publikację wykonuje użytkownik.

## Problemy
Jeśli program pokazuje "Brak FFmpeg" sprawdź w cmd: \`ffmpeg -version\` i \`ffprobe -version\`.
Jeśli SAPI nie ma właściwego głosu, użyj opcji importu MP3/WAV. Jeśli generowanie AI nie działa, uruchom Ollama i sprawdź model poleceniem \`ollama list\`.

## Bezpieczeństwo
Bez kluczy dostępu, bez zdalnych usług poza opcjonalnym lokalnym Ollama. AI tworzy szkic tekstu, a nie zweryfikowany reportaż.
