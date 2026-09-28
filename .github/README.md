# ♟ Chess Style Classifier - Magnus vs Hikaru

**Can a machine learning model recognize a chess grandmaster by their playing style?**

A Random Forest classifier trained on real Chess.com games, enriched with Stockfish engine analysis, that classifies whether a given game was played by Magnus Carlsen or Hikaru Nakamura - move by move.

🔗 **Live demo:** [olgamironczuk.pl - Chess Style Classifier](https://olgamironczuk.pl/projekty/chess-style-classifier-czy-algorytm-rozpozna-mistrza-po-stylu-gry#prezentacja-aplikacji)

This repository contains the full source code for reference. The project runs on my own VPS.

---

## How it works

1. **Data collection** - games are fetched every week from the Chess.com public API (systemd timer on the VPS)
2. **Engine analysis** - Stockfish evaluates every player move (ACPL, best move rate, blunder/mistake/inaccuracy rates, sacrifice rate)
3. **Classification** - a Random Forest model (21 features) is retrained and used to compute per-move probabilities for each game
4. **Export** - results are exported to static JSON files served by Caddy at `chess.olgamironczuk.pl`
5. **Frontend** - the widget on my website displays player stats, a radar chart, a live chess board replay, and an animated probability bar that updates with each move

## Features

- Weekly automated data sync (systemd timer)
- Stockfish-powered feature engineering (incremental - only new games are analyzed each run)
- Move-by-move classification stored as JSONB (one row per game, not per move)
- Atomic JSON export - the website never sees a half-written dataset, and a failed sync keeps the previous data
- Interactive chess board with autoplay and speed controls, Polish/English UI
- Radar chart comparing playing styles
- Player stat cards with win/draw rates, castling preferences, time control breakdown

## Tech stack

| Layer | Tools |
|---|---|
| Data fetching | Python, Chess.com API |
| Database | PostgreSQL (Docker), JSONB |
| Engine analysis | Stockfish, python-chess |
| ML classifier | scikit-learn (Random Forest) |
| Automation | systemd timer |
| Serving data | Caddy (static JSON, HTTPS) |
| Frontend | JavaScript, chessboard.js, chess.js, Chart.js |

## Model accuracy

~70% on a held-out test set (20%). Features include game-level statistics (captures, checks, castling, ECO opening code, time control) and engine-derived metrics (ACPL, best move rate, blunder/inaccuracy/mistake/sacrifice rates).

The first version without engine features achieved ~52% (essentially random). Adding Stockfish analysis was the key decision.

## Project structure

```
├── run_fetch.py          # fetch games from Chess.com API
├── data_fetcher.py       # initial + incremental fetch logic
├── compute_stats.py      # aggregate player statistics
├── engine_analyzer.py    # Stockfish analysis (incremental)
├── classifier.py         # train Random Forest, save move-by-move probs
├── export_json.py        # export stats + classified games to JSON for the website
├── pgn_parser.py         # PGN parsing utilities
├── database.py           # PostgreSQL interface
├── config.py             # env-based configuration
├── requirements.txt
├── web/                  # website widget (JS + CSS)
└── deploy/vps/
    ├── install.sh            # idempotent VPS setup (user, venv, Postgres, timer, Caddy)
    ├── chess-sync.service    # weekly pipeline: fetch → stats → Stockfish → classify → export
    ├── chess-sync.timer      # every Monday 02:00 Europe/Warsaw
    ├── chess.caddy           # chess.olgamironczuk.pl → static JSON
    ├── main.caddy            # main Caddy config importing per-site files
    └── caddy-main-config.conf
```

> History: earlier versions used Supabase, GitHub Actions and GitHub Pages. The project was moved to my own server in September 2026.

---

---

# ♟ Chess Style Classifier - Magnus vs Hikaru

**Czy algorytm uczenia maszynowego rozpozna arcymistrza szachowego po stylu gry?**

Klasyfikator Random Forest wytrenowany na prawdziwych partiach z Chess.com, wzbogacony o analizę silnikiem Stockfish. Model klasyfikuje, czy dana partia została rozegrana przez Magnusa Carlsena czy Hikaru Nakamurę - ruch po ruchu.

🔗 **Demo na żywo:** [olgamironczuk.pl - Chess Style Classifier](https://olgamironczuk.pl/projekty/chess-style-classifier-czy-algorytm-rozpozna-mistrza-po-stylu-gry#prezentacja-aplikacji)

Repozytorium zawiera pełny kod do wglądu. Projekt działa na moim własnym serwerze VPS.

---

## Jak to działa

1. **Pobieranie danych** - partie pobierane co tydzień z publicznego API Chess.com (timer systemd na VPS)
2. **Analiza silnikiem** - Stockfish ocenia każdy ruch gracza (ACPL, odsetek najlepszych ruchów, wskaźniki błędów i ofiar)
3. **Klasyfikacja** - model Random Forest (21 cech) jest trenowany od nowa i wyznacza prawdopodobieństwa dla każdego ruchu w partii
4. **Eksport** - wyniki trafiają do statycznych plików JSON, które Caddy udostępnia pod `chess.olgamironczuk.pl`
5. **Frontend** - widget na mojej stronie pokazuje statystyki graczy, wykres radarowy, odtwarzacz szachownicy i animowany pasek prawdopodobieństwa zmieniający się z każdym ruchem

## Funkcjonalności

- Automatyczna synchronizacja danych co tydzień (timer systemd)
- Analiza Stockfishem z przyrostowym przetwarzaniem (tylko nowe partie przy każdym uruchomieniu)
- Klasyfikacja ruch po ruchu zapisana jako JSONB (jeden wiersz na partię)
- Atomowy eksport JSON - strona nigdy nie trafi na niedokończone dane, a nieudany sync zostawia poprzednie
- Interaktywna szachownica z autoodtwarzaniem i regulacją prędkości, interfejs PL/EN
- Wykres radarowy porównujący style gry
- Karty statystyk z wynikami, preferencjami roszady i podziałem na kategorie czasowe

## Stos technologiczny

| Warstwa | Narzędzia |
|---|---|
| Pobieranie danych | Python, Chess.com API |
| Baza danych | PostgreSQL (Docker), JSONB |
| Analiza silnikiem | Stockfish, python-chess |
| Klasyfikator ML | scikit-learn (Random Forest) |
| Automatyzacja | timer systemd |
| Udostępnianie danych | Caddy (statyczne JSON, HTTPS) |
| Frontend | JavaScript, chessboard.js, chess.js, Chart.js |

## Dokładność modelu

~70% na zbiorze testowym (20% danych). Cechy obejmują statystyki partii (bicia, szachy, roszada, kod otwarcia ECO, kategoria czasowa) oraz metryki z analizy silnikiem (ACPL, odsetek najlepszych ruchów, wskaźniki błędów, niedokładności i ofiar).

Pierwsza wersja bez analizy silnikiem osiągała ~52% (praktycznie losowo). Dodanie Stockfisha było kluczową decyzją projektową.

> Historia: wcześniejsze wersje korzystały z Supabase, GitHub Actions i GitHub Pages. We wrześniu 2026 projekt został przeniesiony na mój własny serwer.
