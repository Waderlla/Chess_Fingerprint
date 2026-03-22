from __future__ import annotations

from datetime import datetime, timezone

import requests

from config import (
    PLAYERS,
    SOURCE_GAMES_RETENTION_YEARS,
    FETCH_LOOKBACK_MONTHS,
    DISABLE_RAW_JSON_STORAGE,
)
from database import (
    create_tables,
    get_connection,
    insert_source_game_with_cursor,
    get_latest_source_game_date,
    delete_old_source_games,
    strip_raw_json_from_source_games,
)


def month_range(start_year, start_month, end_year, end_month):
    # Generator kolejnych miesięcy pomiędzy datą start i end.
    year, month = start_year, start_month
    while (year < end_year) or (year == end_year and month <= end_month):
        yield year, month
        month += 1
        if month == 13:
            month = 1
            year += 1


def shift_months(year, month, delta_months):
    # Przesuwa rok/miesiąc o podaną liczbę miesięcy.
    absolute = year * 12 + (month - 1) + delta_months
    new_year = absolute // 12
    new_month = absolute % 12 + 1
    return new_year, new_month


def utc_now():
    # Zwraca aktualny czas UTC.
    return datetime.now(timezone.utc)


def parse_played_at(game):
    # Zamienia timestamp z Chess.com na datetime UTC.
    end_time = game.get("end_time")
    if end_time is None:
        return None
    return datetime.fromtimestamp(end_time, tz=timezone.utc)


def extract_record(username, game):
    # Wyciąga z odpowiedzi API tylko te pola, które są potrzebne w projekcie.
    white = game.get("white", {}) or {}
    black = game.get("black", {}) or {}

    white_name = white.get("username")
    black_name = black.get("username")

    username_lower = username.lower()
    white_lower = (white_name or "").lower()
    black_lower = (black_name or "").lower()

    if white_lower == username_lower:
        player_color = "white"
        player_result = white.get("result")
    elif black_lower == username_lower:
        player_color = "black"
        player_result = black.get("result")
    else:
        player_color = None
        player_result = None

    return {
        "source": "chess.com",
        "username": username,
        "game_url": game.get("url"),
        "played_at": parse_played_at(game),
        "white_username": white_name,
        "black_username": black_name,
        "player_color": player_color,
        "player_result": player_result,
        "time_class": game.get("time_class"),
        "time_control": game.get("time_control"),
        "rules": game.get("rules"),
        "rated": game.get("rated"),
        "pgn": game.get("pgn"),
        "raw_json": None if DISABLE_RAW_JSON_STORAGE else game,
    }


def fetch_month(username, year, month):
    # Pobiera archiwum partii jednego użytkownika dla danego miesiąca.
    url = f"https://api.chess.com/pub/player/{username}/games/{year}/{month:02d}"
    headers = {"User-Agent": "chess-style-project/1.0"}
    response = requests.get(url, headers=headers, timeout=30)

    if response.status_code == 404:
        return []

    response.raise_for_status()
    data = response.json()
    return data.get("games", [])


def get_sync_window(username):
    # Wyznacza zakres miesięcy do pobrania:
    # - przy pierwszym imporcie: ostatnie N lat
    # - przy kolejnych: od ostatniej zapisanej gry z małym overlapem
    now = utc_now()
    end_year, end_month = now.year, now.month

    latest = get_latest_source_game_date(username)

    if latest is None:
        start_year = now.year - SOURCE_GAMES_RETENTION_YEARS
        start_month = now.month
        return start_year, start_month, end_year, end_month

    start_year, start_month = latest.year, latest.month
    start_year, start_month = shift_months(start_year, start_month, -FETCH_LOOKBACK_MONTHS)
    return start_year, start_month, end_year, end_month


def fetch_and_store(username):
    # Główny sync partii dla jednego gracza.
    total_processed = 0

    start_year, start_month, end_year, end_month = get_sync_window(username)
    print(f"\n=== Sync {username}: {start_year}-{start_month:02d} -> {end_year}-{end_month:02d} ===")

    conn = get_connection()
    cur = conn.cursor()

    try:
        for year, month in month_range(start_year, start_month, end_year, end_month):
            print(f"Pobieram {username}: {year}-{month:02d}")
            games = fetch_month(username, year, month)
            print(f"  znaleziono gier: {len(games)}")

            for index, game in enumerate(games, start=1):
                record = extract_record(username, game)
                insert_source_game_with_cursor(cur, record)
                total_processed += 1

                if index % 50 == 0:
                    conn.commit()
                    print(f"  przetworzono {index}/{len(games)}")

            conn.commit()

        print(f"Zakończono {username}. Przetworzono rekordów: {total_processed}")
    finally:
        cur.close()
        conn.close()


def prune_source_games():
    # Czyści dane źródłowe starsze niż ustalona retencja.
    now = utc_now()
    cutoff_year = now.year - SOURCE_GAMES_RETENTION_YEARS
    cutoff = datetime(cutoff_year, now.month, 1, tzinfo=timezone.utc)

    deleted = delete_old_source_games(cutoff)
    print(f"Usunięto starych partii źródłowych: {deleted}")

    if DISABLE_RAW_JSON_STORAGE:
        stripped = strip_raw_json_from_source_games()
        print(f"Wyzerowano raw_json w rekordach: {stripped}")


def main():
    # Tworzy tabele, synchronizuje dane dla obu graczy
    # i na końcu czyści stare rekordy.
    create_tables()

    for username in PLAYERS:
        fetch_and_store(username)

    prune_source_games()


if __name__ == "__main__":
    main()
