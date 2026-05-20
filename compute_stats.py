from __future__ import annotations

from collections import Counter
from statistics import mean

from database import create_tables, get_connection, save_player_stats, delete_orphaned_classifications
from pgn_parser import parse_game_features

PLAYERS = ["MagnusCarlsen", "hikaru"]

RESULT_WIN = {"win"}
RESULT_DRAW = {"agreed", "repetition", "stalemate", "timevsinsufficient", "insufficient", "50move"}
RESULT_LOSS = {"checkmated", "timeout", "resigned", "lose", "abandoned"}


def normalize_result(player_result: str) -> str:
    if player_result in RESULT_WIN:
        return "win"
    if player_result in RESULT_DRAW:
        return "draw"
    if player_result in RESULT_LOSS:
        return "loss"
    return "other"


def load_source_games(username: str) -> list[tuple]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT player_color, player_result, time_class, pgn
        FROM source_games
        WHERE username = %s
          AND pgn IS NOT NULL
          AND player_color IS NOT NULL;
        """,
        (username,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def compute_stats_for_player(username: str) -> dict | None:
    rows = load_source_games(username)
    if not rows:
        print(f"Brak partii dla {username}.")
        return None

    fullmoves_list = []
    captures_per_move_list = []
    checks_per_move_list = []
    castled_count = 0
    kingside_count = 0
    queenside_count = 0
    time_classes = []
    results = []

    skipped = 0
    for player_color, player_result, time_class, pgn in rows:
        parsed = parse_game_features(pgn, player_color)
        if parsed is None:
            skipped += 1
            continue

        fullmoves = max(parsed.get("fullmoves", 0) or 0, 1)
        captures = parsed.get("player_captures", 0) or 0
        checks = parsed.get("player_checks", 0) or 0
        castle_type = parsed.get("player_castle_type")

        fullmoves_list.append(fullmoves)
        captures_per_move_list.append(captures / fullmoves)
        checks_per_move_list.append(checks / fullmoves)

        if parsed.get("player_castled"):
            castled_count += 1
        if castle_type == "kingside":
            kingside_count += 1
        if castle_type == "queenside":
            queenside_count += 1

        if time_class:
            time_classes.append(time_class)

        results.append(normalize_result(player_result or ""))

    games_count = len(fullmoves_list)
    if games_count == 0:
        print(f"Żadna partia {username} nie mogła zostać sparsowana.")
        return None

    time_counter = Counter(time_classes)
    result_counter = Counter(results)

    return {
        "username": username,
        "games_count": games_count,
        "avg_fullmoves": round(mean(fullmoves_list), 2),
        "avg_captures_per_move": round(mean(captures_per_move_list), 4),
        "avg_checks_per_move": round(mean(checks_per_move_list), 4),
        "castle_rate": round(castled_count / games_count, 4),
        "kingside_castle_rate": round(kingside_count / games_count, 4),
        "queenside_castle_rate": round(queenside_count / games_count, 4),
        "win_rate": round(result_counter.get("win", 0) / games_count, 4),
        "draw_rate": round(result_counter.get("draw", 0) / games_count, 4),
        "loss_rate": round(result_counter.get("loss", 0) / games_count, 4),
        "bullet_share": round(time_counter.get("bullet", 0) / games_count, 4),
        "blitz_share": round(time_counter.get("blitz", 0) / games_count, 4),
        "rapid_share": round(time_counter.get("rapid", 0) / games_count, 4),
    }


def main():
    create_tables()

    for username in PLAYERS:
        print(f"\nObliczam statystyki: {username}...")
        stats = compute_stats_for_player(username)
        if stats is None:
            continue
        save_player_stats(stats)
        print(f"  Partii: {stats['games_count']}")
        print(f"  Śr. ruchów: {stats['avg_fullmoves']}")
        print(f"  Bicia/ruch: {stats['avg_captures_per_move']}")
        print(f"  Szachy/ruch: {stats['avg_checks_per_move']}")
        print(f"  Roszada: {stats['castle_rate']:.1%}")
        print(f"  Win rate: {stats['win_rate']:.1%}")
        print(f"  Zapisano.")

    print("\nSprzątam osierocone rekordy klasyfikacji...")
    deleted = delete_orphaned_classifications()
    print(f"Usunięto {deleted} rekordów.")

    print("\nGotowe.")


if __name__ == "__main__":
    main()
