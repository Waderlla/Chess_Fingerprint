# ♟ Chess Style Classifier — Magnus vs Hikaru

**Can a machine learning model recognize a chess grandmaster by their playing style?**

A Random Forest classifier trained on real Chess.com games, enriched with Stockfish engine analysis, that classifies whether a given game was played by Magnus Carlsen or Hikaru Nakamura — move by move.

🔗 **Live demo:** [waderlla.github.io/Chess_Fingerprint](https://waderlla.github.io/Chess_Fingerprint)

---

## How it works

1. **Data collection** — games are fetched automatically from the Chess.com public API each week via GitHub Actions
2. **Engine analysis** — Stockfish evaluates every player move (ACPL, best move rate, blunder/mistake/inaccuracy rates, sacrifice rate)
3. **Classification** — a Random Forest model (21 features) is trained and used to compute per-move probabilities for each game
4. **Frontend** — an interactive page displays player stats, a radar chart, a live chess board replay, and an animated probability bar that updates with each move

## Features

- Weekly automated data sync (GitHub Actions cron)
- Stockfish-powered feature engineering (incremental — only new games are analyzed each run)
- Move-by-move classification stored as JSONB (one row per game, not per move)
- Interactive chess board with autoplay and speed controls
- Radar chart comparing playing styles
- Player stat cards with win/draw rates, castling preferences, time control breakdown
- Separate WordPress-embeddable version (`embed.html`) with a warm light theme

## Tech stack

| Layer | Tools |
|---|---|
| Data fetching | Python, Chess.com API |
| Database | Supabase (PostgreSQL), JSONB |
| Engine analysis | Stockfish, python-chess |
| ML classifier | scikit-learn (Random Forest) |
| Automation | GitHub Actions |
| Frontend | HTML/CSS/JS, chessboard.js, chess.js, Chart.js |
| Hosting | GitHub Pages |

## Model accuracy

~70% on a held-out test set (20%). Features include game-level statistics (captures, checks, castling, ECO opening code, time control) and engine-derived metrics (ACPL, best move rate, blunder/inaccuracy/mistake/sacrifice rates).

The first version without engine features achieved ~52% (essentially random). Adding Stockfish analysis was the key decision.

## Project structure

```
├── run_fetch.py          # fetch games from Chess.com API
├── compute_stats.py      # aggregate player statistics
├── engine_analyzer.py    # Stockfish analysis (incremental)
├── classifier.py         # train Random Forest, save move-by-move probs
├── pgn_parser.py         # PGN parsing utilities
├── database.py           # Supabase/PostgreSQL interface
├── config.py             # env-based configuration
├── index.html            # GitHub Pages frontend (dark theme)
├── embed.html            # WordPress embed version (light theme)
├── requirements.txt
└── .github/workflows/
    └── monthly_sync.yml  # weekly cron: fetch → analyze → classify
```

## Security

- The Supabase `anon` key in the frontend is public by design — it is read-only
- Row Level Security (RLS) is enabled on all tables with SELECT-only policies for anonymous users
- Database credentials (host, password) are stored exclusively in GitHub Secrets
- The `service_role` key is never used in frontend code

---

---

# ♟ Chess Style Classifier — Magnus vs Hikaru

**Czy algorytm uczenia maszynowego rozpozna arcymistrza szachowego po stylu gry?**

Klasyfikator Random Forest wytrenowany na prawdziwych partiach z Chess.com, wzbogacony o analizę silnikiem Stockfish. Model klasyfikuje, czy dana partia została rozegrana przez Magnusa Carlsena czy Hikaru Nakamurę — ruch po ruchu.

🔗 **Demo na żywo:** [waderlla.github.io/Chess_Fingerprint](https://waderlla.github.io/Chess_Fingerprint)

---

## Jak to działa

1. **Pobieranie danych** — partie pobierane automatycznie z publicznego API Chess.com co tydzień przez GitHub Actions
2. **Analiza silnikiem** — Stockfish ocenia każdy ruch gracza (ACPL, odsetek najlepszych ruchów, wskaźniki błędów i ofiar)
3. **Klasyfikacja** — model Random Forest (21 cech) wyznacza prawdopodobieństwa dla każdego ruchu w partii
4. **Frontend** — interaktywna strona pokazuje statystyki graczy, wykres radarowy, odtwarzacz szachownicy i animowany pasek prawdopodobieństwa zmieniający się z każdym ruchem

## Funkcjonalności

- Automatyczna synchronizacja danych co tydzień (GitHub Actions cron)
- Analiza Stockfishem z przyrostowym przetwarzaniem (tylko nowe partie przy każdym uruchomieniu)
- Klasyfikacja ruch po ruchu zapisana jako JSONB (jeden wiersz na partię)
- Interaktywna szachownica z autoodtwarzaniem i regulacją prędkości
- Wykres radarowy porównujący style gry
- Karty statystyk z wynikami, preferencjami roszady i podziałem na kategorie czasowe
- Osobna wersja do osadzenia w WordPress (`embed.html`) z jasnym motywem

## Stos technologiczny

| Warstwa | Narzędzia |
|---|---|
| Pobieranie danych | Python, Chess.com API |
| Baza danych | Supabase (PostgreSQL), JSONB |
| Analiza silnikiem | Stockfish, python-chess |
| Klasyfikator ML | scikit-learn (Random Forest) |
| Automatyzacja | GitHub Actions |
| Frontend | HTML/CSS/JS, chessboard.js, chess.js, Chart.js |
| Hosting | GitHub Pages |

## Dokładność modelu

~70% na zbiorze testowym (20% danych). Cechy obejmują statystyki partii (bicia, szachy, roszada, kod otwarcia ECO, kategoria czasowa) oraz metryki z analizy silnikiem (ACPL, odsetek najlepszych ruchów, wskaźniki błędów, niedokładności i ofiar).

Pierwsza wersja bez analizy silnikiem osiągała ~52% (praktycznie losowo). Dodanie Stockfisha było kluczową decyzją projektową.

## Bezpieczeństwo

- Klucz `anon` Supabase w kodzie frontendowym jest publiczny z założenia — jest tylko do odczytu
- Row Level Security (RLS) jest włączone na wszystkich tabelach z politykami SELECT dla użytkowników anonimowych
- Poświadczenia bazy danych (host, hasło) przechowywane wyłącznie w GitHub Secrets
- Klucz `service_role` nie jest używany w kodzie frontendowym
