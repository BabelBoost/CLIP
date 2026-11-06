# Babel Boost Outro Studio

Uniwersalne outro reklamowe 1080 × 1920. Otwórz `index.html` dwuklikiem w Chrome lub Edge. Nie wymaga instalacji ani połączenia z internetem.

1. Wybierz język PL lub EN.
2. Wpisz nagłówek, dopisek, CTA i adres sklepu.
3. Opcjonalnie wczytaj okładkę JPG, PNG lub WebP. Okładka mieści się w całości, bez przycinania.
4. Pobierz PNG lub animację WebM o długości 6 sekund. Podczas eksportu pozostaw kartę aktywną.
5. Dodaj wynik na końcu klipu. Podkład muzyczny z filmu wycisz w ostatniej sekundzie.

Wersja domyślna reklamuje sklep BabelBoost.com. Grafika książki jest elementem marki, nie okładką istniejącej publikacji. Podmień ją przy reklamie konkretnego tytułu.

Eksport jest bez dźwięku. Animacja ma łagodne wejście książki, a CTA i adres pozostają widoczne. Główne treści mieszczą się z dala od krawędzi. Nakładki interfejsu platform mogą się różnić.

Konwersja WebM do MP4 przy użyciu FFmpeg:

```bash
ffmpeg -i BabelBoost_Outro_6s.webm -c:v libx264 -pix_fmt yuv420p -r 30 -movflags +faststart BabelBoost_Outro_6s.mp4
```

Projekt korzysta z Canvas i systemowej czcionki Arial. Bez zewnętrznych zasobów i bez przesyłania okładek na serwer.
