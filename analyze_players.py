from database import create_tables, get_connection, upsert_style_profile
from pgn_parser import parse_game_features
from style_features import aggregate_style_features
from style_profiles import build_profile, build_ecnalab_profile


def fetch_source_games_for_player(username):
    # Pobiera z bazy wszystkie partie źródłowe danego gracza.
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            username,
            player_color,
            player_result,
            time_class,
            pgn,
            game_url
        FROM source_games
        WHERE username = %s
          AND pgn IS NOT NULL
        ORDER BY played_at ASC NULLS LAST;
        """,
        (username,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    result = []
    for row in rows:
        result.append(
            {
                "username": row[0],
                "player_color": row[1],
                "player_result": row[2],
                "time_class": row[3],
                "pgn": row[4],
                "game_url": row[5],
            }
        )
    return result


def analyze_player(username):
    # Analizuje wszystkie partie jednego gracza i zapisuje jego profil do bazy.
    source_rows = fetch_source_games_for_player(username)
    parsed_games = []

    for row in source_rows:
        parsed = parse_game_features(row["pgn"], row["player_color"])
        if parsed is not None:
            parsed_games.append(parsed)

    metrics = aggregate_style_features(parsed_games, source_rows)
    profile = build_profile(username, metrics)
    upsert_style_profile(username, metrics["games_count"], metrics, profile)

    print(f"\n=== {username} ===")
    print(f"Liczba gier: {metrics['games_count']}")
    print(f"Śr. pełnych ruchów: {metrics['avg_fullmoves']}")
    print(f"Śr. przechwytów gracza: {metrics['avg_player_captures']}")
    print(f"Castle rate: {metrics['castle_rate']}")
    print(f"Blitz share: {metrics['blitz_share']}")
    print(f"Rapid share: {metrics['rapid_share']}")
    print("Profil:", profile)

    return metrics, profile


def main():
    # Buduje profile Magnusa, Hikaru oraz hybrydy Ecnalab.
    create_tables()

    magnus_metrics, magnus_profile = analyze_player("MagnusCarlsen")
    hikaru_metrics, hikaru_profile = analyze_player("hikaru")

    ecnalab_profile = build_ecnalab_profile(magnus_profile, hikaru_profile)

    empty_metrics = {
        "avg_halfmoves": None,
        "avg_fullmoves": None,
        "avg_captures": None,
        "avg_player_captures": None,
        "castle_rate": None,
        "kingside_castle_rate": None,
        "queenside_castle_rate": None,
        "check_rate": None,
        "player_check_rate": None,
        "avg_time_class_weight": None,
        "bullet_share": None,
        "blitz_share": None,
        "rapid_share": None,
        "win_rate": None,
        "draw_rate": None,
        "loss_rate": None,
    }

    upsert_style_profile(
        "Ecnalab",
        min(magnus_metrics["games_count"], hikaru_metrics["games_count"]),
        empty_metrics,
        ecnalab_profile,
    )

    print("\n=== Ecnalab ===")
    print("Profil:", ecnalab_profile)


if __name__ == "__main__":
    main()
