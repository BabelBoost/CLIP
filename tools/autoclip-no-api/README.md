# Babel Boost AutoClip Studio | BEZ API

Działający lokalnie generator pionowych klipów MP4 na Windows.

**Nie wymaga żadnego klucza API** ani płatnych kont OpenAI, Pexels czy Pixabay. Podstawowy tryb montażu działa bez internetu po jednorazowym zainstalowaniu bibliotek.

## Co działa

- Wpisujesz prompt i jednym przyciskiem dostajesz pionowe MP4.
- Bez modelu AI generowany jest prosty, edytowalny scenariusz na podstawie promptu. Nie udaje analizowanych newsów ani nie wymyśla faktów.
- Opcjonalna **Ollama** z pobranym modelem może lokalnie tworzyć lepszy scenariusz. Nie potrzebuje klucza API. Uruchamiamy polecenie CLI, a nie zewnętrzną usługę.
- Wyszukiwanie dopasowanych plików z folderu `stock/` po nazwach i słowach powiązanych. Rozpoznawane JPG/PNG/WEBP/MP4/MOV/M4V.
- Jeśli nie ma żadnych zdjęć, aplikacja generuje własne oryginalne grafiki i nadal tworzy film.
- Opcjonalne pobieranie zdjęć z **Wikimedia Commons** przez publiczne strony HTML, bez API ani logowania. Automatycznie używa tylko zdjęć z wykrytym linkiem CC0 na stronie pliku. Zależy od obecnego układu witryny i dostępu do internetu, może nie działać lub nie znaleźć materiałów.
- Lokalny lektor na bazie zainstalowanych głosów Windows przez pyttsx3. Dla języka polskiego może być potrzebny zainstalowany polski głos Windows.
- Napisy scenowe, logo, muzyka użytkownika, MP4 do 1080 × 1920, raport sources.json oraz credits.txt.
- Bez automatycznej publikacji, bez weryfikacji prawdziwości informacji, bez napisów zsynchronizowanych słowo po słowie.

## Jak uruchomić na Windows

1. Zainstaluj Python 3.10 lub nowszy z https://www.python.org/downloads/ i zaznacz Add Python to PATH.
2. Rozpakuj paczkę do folderu na pulpicie.
3. Kliknij **START_WINDOWS.bat**. To zainstaluje darmowe biblioteki. Pierwszy start wymaga dostępu do internetu, ale **nie wymaga żadnego API**.
4. Program otworzy się w przeglądarce. Wklej prompt i kliknij **Stwórz klip z promptu**.
5. Gotowy MP4 pojawi się w panelu i w katalogu `exports`.
6. Przy następnych uruchomieniach bez internetu użyj **START_OFFLINE.bat**.

## Jak korzystać z prawdziwych stocków bez API

1. Otwórz https://www.pexels.com/ lub https://pixabay.com/
2. Pobierz zdjęcia lub filmy zgodnie z ich licencjami i umieść je w `stock/`.
3. Nadaj plikom nazwy opisujące obraz, np. `iceland_snow_mountain_01.mp4`.
4. Program sam wybierze materiały pasujące do promptu, bez wskazywania ich scenami.

Tryb Wikimedia Commons może znaleźć zdjęcia z sieci bez żadnego klucza, lecz nie daje gwarancji dostępności. Pixabay i Pexels nie są skrobane automatycznie. Na darmowe API nie ma potrzeby zakładać konta, bo program z nich nie korzysta.

## Opcjonalny lepszy scenariusz bez API

Zainstaluj lokalną aplikację **Ollama**: https://ollama.com/ , następnie pobierz model poleceniem `ollama pull llama3.2:3b`. W AutoClip zaznacz „AI lokalne przez Ollama”. Sam model zużywa miejsce na dysku i pamięć RAM. Ollama działa lokalnie, a program rozmawia z nim przez CLI.

## Licencje

Wikimedia Commons nie daje jednej licencji wszystkim plikom. Sprawdzaj prawa i informacje o autorach w `credits.txt`. Materiały wrażliwe, polityczne i reporterskie powinny być opisywane jako ilustracyjne. Nie przedstawiaj stocku jako autentycznego nagrania zdarzenia. Treści reklamowe muszą respektować prawa osób i znaków.

Baza: https://github.com/BabelBoost/CLIP
