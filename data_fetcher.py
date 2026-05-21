from __future__ import annotations

from datetime import datetime, timezone

import requests

from config import (
    PLAYERS,
    MAX_GAMES_PER_PLAYER,
    FETCH_LOOKBACK_MONTHS,
    DISABLE_RAW_JSON_STORAGE,
)
from database import (
    create_tables,
    get_connection,
    insert_source_game_with_cursor,
    get_latest_source_game_date,
    keep_latest_source_games,
    strip_raw_json_from_source_games,
)

HEADERS = {"User-Agent": "chess-fingerprint/1.0"}


def month_range(start_year, start_month, end_year, end_month):
    year, month = start_year, start_month
    while (year < end_year) or (year == end_year and month <= end_month):
        yield year, month
        month += 1
        if month == 13:
            month = 1
            year += 1


def shift_months(year, month, delta_months):
    absolute = year * 12 + (month - 1) + delta_months
    new_year = absolute // 12
    new_month = absolute % 12 + 1
    return new_year, new_month


def utc_now():
    return datetime.now(timezone.utc)


def parse_played_at(game):
    end_time = game.get("end_time")
    if end_time is None:
        return None
    return datetime.fromtimestamp(end_time, tz=timezone.utc)


def extract_record(username, game):
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
    url = f"https://api.chess.com/pub/player/{username}/games/{year}/{month:02d}"
    response = requests.get(url, headers=HEADERS, timeout=30)
    if response.status_code == 404:
        return []
    response.raise_for_status()
    return response.json().get("games", [])


def get_available_archives(username):
    url = f"https://api.chess.com/pub/player/{username}/games/archives"
    response = requests.get(url, headers=HEADERS, timeout=30)
    if response.status_code != 200:
        return []
    return response.json().get("archives", [])


def initial_fetch(username, conn, cur):
    # Pobiera od najnowszych partii i zatrzymuje się po osiągnięciu limitu.
    archives = get_available_archives(username)
    if not archives:
        print(f"Brak archiwów dla {username}.")
        return 0

    archives = list(reversed(archives))  # od najnowszego do najstarszego
    total_stored = 0

    for archive_url in archives:
        if total_stored >= MAX_GAMES_PER_PLAYER:
            break

        parts = archive_url.rstrip("/").split("/")
        year, month = int(parts[-2]), int(parts[-1])

        print(f"Pobieram {username}: {year}-{month:02d}")
        games = fetch_month(username, year, month)
        games = list(reversed(games))  # od najnowszej w miesiącu
        print(f"  znaleziono gier: {len(games)}")

        for game in games:
            if total_stored >= MAX_GAMES_PER_PLAYER:
                break
            record = extract_record(username, game)
            insert_source_game_with_cursor(cur, record)
            total_stored += 1

        conn.commit()
        print(f"  łącznie zapisano: {total_stored}/{MAX_GAMES_PER_PLAYER}")

    return total_stored


def incremental_fetch(username, latest, conn, cur):
    # Pobiera tylko nowe partie od ostatniego syncu.
    now = utc_now()
    start_year, start_month = shift_months(latest.year, latest.month, -FETCH_LOOKBACK_MONTHS)
    end_year, end_month = now.year, now.month

    print(f"\n=== Sync {username}: {start_year}-{start_month:02d} -> {end_year}-{end_month:02d} ===")
    total_stored = 0

    for year, month in month_range(start_year, start_month, end_year, end_month):
        print(f"Pobieram {username}: {year}-{month:02d}")
        games = fetch_month(username, year, month)
        print(f"  znaleziono gier: {len(games)}")

        for index, game in enumerate(games, start=1):
            record = extract_record(username, game)
            insert_source_game_with_cursor(cur, record)
            total_stored += 1
            if index % 50 == 0:
                conn.commit()

        conn.commit()

    return total_stored


def fetch_and_store(username):
    latest = get_latest_source_game_date(username)
    is_initial = latest is None

    conn = get_connection()
    cur = conn.cursor()

    try:
        if is_initial:
            print(f"\n=== Pierwszy import {username} (limit: {MAX_GAMES_PER_PLAYER} partii) ===")
            total = initial_fetch(username, conn, cur)
            print(f"Pierwszy import {username} zakończony: {total} partii.")
        else:
            total = incremental_fetch(username, latest, conn, cur)
            print(f"Zakończono {username}. Nowych rekordów: {total}")
    finally:
        cur.close()
        conn.close()


def prune_source_games():
    for username in PLAYERS:
        deleted = keep_latest_source_games(username, MAX_GAMES_PER_PLAYER)
        print(f"{username}: usunięto {deleted} nadmiarowych partii (limit: {MAX_GAMES_PER_PLAYER})")

    if DISABLE_RAW_JSON_STORAGE:
        stripped = strip_raw_json_from_source_games()
        print(f"Wyzerowano raw_json w rekordach: {stripped}")


def main():
    create_tables()

    for username in PLAYERS:
        fetch_and_store(username)

    prune_source_games()


if __name__ == "__main__":
    main()
