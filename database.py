from __future__ import annotations

from datetime import datetime

import psycopg2
from psycopg2.extras import Json

from config import DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT


def get_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )


def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS source_games (
            id BIGSERIAL PRIMARY KEY,
            source TEXT NOT NULL,
            username TEXT NOT NULL,
            game_url TEXT UNIQUE,
            played_at TIMESTAMP,
            white_username TEXT,
            black_username TEXT,
            player_color TEXT,
            player_result TEXT,
            time_class TEXT,
            time_control TEXT,
            rules TEXT,
            rated BOOLEAN,
            pgn TEXT,
            raw_json JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS player_stats (
            id BIGSERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            games_count INT,
            avg_fullmoves FLOAT,
            avg_captures_per_move FLOAT,
            avg_checks_per_move FLOAT,
            castle_rate FLOAT,
            kingside_castle_rate FLOAT,
            queenside_castle_rate FLOAT,
            win_rate FLOAT,
            draw_rate FLOAT,
            loss_rate FLOAT,
            bullet_share FLOAT,
            blitz_share FLOAT,
            rapid_share FLOAT,
            updated_at TIMESTAMP DEFAULT NOW()
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS game_classifications (
            id BIGSERIAL PRIMARY KEY,
            game_url TEXT UNIQUE NOT NULL,
            username TEXT NOT NULL,
            move_probs JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """
    )

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_source_games_username_played_at
        ON source_games (username, played_at);
        """
    )


    conn.commit()
    cur.close()
    conn.close()


def get_latest_source_game_date(username):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT MAX(played_at)
        FROM source_games
        WHERE username = %s;
        """,
        (username,),
    )
    latest = cur.fetchone()[0]

    cur.close()
    conn.close()
    return latest


def keep_latest_source_games(username: str, max_games: int) -> int:
    """Zostawia tylko ostatnie max_games partii gracza, usuwa starsze."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        DELETE FROM source_games
        WHERE username = %s
          AND id NOT IN (
              SELECT id FROM source_games
              WHERE username = %s
              ORDER BY played_at DESC NULLS LAST
              LIMIT %s
          );
        """,
        (username, username, max_games),
    )

    deleted = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return deleted


def strip_raw_json_from_source_games():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE source_games
        SET raw_json = NULL
        WHERE raw_json IS NOT NULL;
        """
    )

    updated = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return updated


def insert_source_game_with_cursor(cur, record):
    cur.execute(
        """
        INSERT INTO source_games (
            source, username, game_url, played_at,
            white_username, black_username, player_color, player_result,
            time_class, time_control, rules, rated, pgn, raw_json
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (game_url) DO NOTHING;
        """,
        (
            record["source"],
            record["username"],
            record["game_url"],
            record["played_at"],
            record["white_username"],
            record["black_username"],
            record["player_color"],
            record["player_result"],
            record["time_class"],
            record["time_control"],
            record["rules"],
            record["rated"],
            record["pgn"],
            Json(record["raw_json"]) if record["raw_json"] is not None else None,
        ),
    )


def save_player_stats(stats: dict):
    """Zapisuje lub aktualizuje statystyki gracza używane do kart i wykresu radar."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO player_stats (
            username, games_count,
            avg_fullmoves, avg_captures_per_move, avg_checks_per_move,
            castle_rate, kingside_castle_rate, queenside_castle_rate,
            win_rate, draw_rate, loss_rate,
            bullet_share, blitz_share, rapid_share,
            updated_at
        )
        VALUES (
            %(username)s, %(games_count)s,
            %(avg_fullmoves)s, %(avg_captures_per_move)s, %(avg_checks_per_move)s,
            %(castle_rate)s, %(kingside_castle_rate)s, %(queenside_castle_rate)s,
            %(win_rate)s, %(draw_rate)s, %(loss_rate)s,
            %(bullet_share)s, %(blitz_share)s, %(rapid_share)s,
            NOW()
        )
        ON CONFLICT (username) DO UPDATE SET
            games_count = EXCLUDED.games_count,
            avg_fullmoves = EXCLUDED.avg_fullmoves,
            avg_captures_per_move = EXCLUDED.avg_captures_per_move,
            avg_checks_per_move = EXCLUDED.avg_checks_per_move,
            castle_rate = EXCLUDED.castle_rate,
            kingside_castle_rate = EXCLUDED.kingside_castle_rate,
            queenside_castle_rate = EXCLUDED.queenside_castle_rate,
            win_rate = EXCLUDED.win_rate,
            draw_rate = EXCLUDED.draw_rate,
            loss_rate = EXCLUDED.loss_rate,
            bullet_share = EXCLUDED.bullet_share,
            blitz_share = EXCLUDED.blitz_share,
            rapid_share = EXCLUDED.rapid_share,
            updated_at = NOW();
        """,
        stats,
    )

    conn.commit()
    cur.close()
    conn.close()


def delete_orphaned_classifications():
    """Usuwa oceny partii które nie istnieją już w source_games."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        DELETE FROM game_classifications
        WHERE game_url NOT IN (
            SELECT game_url FROM source_games WHERE game_url IS NOT NULL
        );
        """
    )

    deleted = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return deleted


def save_game_classifications(classifications: list[dict]):
    """Zapisuje klasyfikacje jako jeden wiersz na partię (move_probs jako JSON)."""
    if not classifications:
        return

    conn = get_connection()
    cur = conn.cursor()

    chunk_size = 200
    for i in range(0, len(classifications), chunk_size):
        chunk = classifications[i : i + chunk_size]
        cur.executemany(
            """
            INSERT INTO game_classifications (game_url, username, move_probs)
            VALUES (%(game_url)s, %(username)s, %(move_probs)s)
            ON CONFLICT (game_url) DO UPDATE SET
                move_probs = EXCLUDED.move_probs;
            """,
            [({"game_url": r["game_url"], "username": r["username"], "move_probs": Json(r["move_probs"])}) for r in chunk],
        )
        conn.commit()

    cur.close()
    conn.close()
