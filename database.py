from __future__ import annotations

from datetime import datetime

import psycopg2
from psycopg2.extras import Json

from config import DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT


def get_connection():
    # Tworzy połączenie z bazą PostgreSQL / Supabase.
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )


def create_tables():
    # Tworzy wszystkie potrzebne tabele i indeksy.
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS games (
            id BIGSERIAL PRIMARY KEY,
            white_bot TEXT NOT NULL,
            black_bot TEXT NOT NULL,
            result TEXT NOT NULL,
            move_count INT NOT NULL,
            matchup TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS moves (
            id BIGSERIAL PRIMARY KEY,
            game_id BIGINT REFERENCES games(id) ON DELETE CASCADE,
            move_number INT NOT NULL,
            player TEXT NOT NULL,
            move TEXT NOT NULL,
            fen TEXT,
            is_capture BOOLEAN DEFAULT FALSE,
            is_check BOOLEAN DEFAULT FALSE,
            is_castle BOOLEAN DEFAULT FALSE,
            eval FLOAT
        );
        """
    )

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
        CREATE TABLE IF NOT EXISTS style_profiles (
            id BIGSERIAL PRIMARY KEY,
            player_name TEXT UNIQUE NOT NULL,
            source_game_count INT NOT NULL,
            avg_halfmoves FLOAT,
            avg_fullmoves FLOAT,
            avg_captures FLOAT,
            avg_player_captures FLOAT,
            castle_rate FLOAT,
            kingside_castle_rate FLOAT,
            queenside_castle_rate FLOAT,
            check_rate FLOAT,
            player_check_rate FLOAT,
            avg_time_class_weight FLOAT,
            bullet_share FLOAT,
            blitz_share FLOAT,
            rapid_share FLOAT,
            win_rate FLOAT,
            draw_rate FLOAT,
            loss_rate FLOAT,
            profile_json JSONB,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        """
    )

    # Dodatkowe migracje dla starszych wersji bazy.
    cur.execute("ALTER TABLE games ADD COLUMN IF NOT EXISTS matchup TEXT;")
    cur.execute("ALTER TABLE moves ADD COLUMN IF NOT EXISTS is_capture BOOLEAN DEFAULT FALSE;")
    cur.execute("ALTER TABLE moves ADD COLUMN IF NOT EXISTS is_check BOOLEAN DEFAULT FALSE;")
    cur.execute("ALTER TABLE moves ADD COLUMN IF NOT EXISTS is_castle BOOLEAN DEFAULT FALSE;")

    # Indeksy przyspieszające sync i analizy.
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_source_games_username_played_at
        ON source_games (username, played_at);
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_games_matchup
        ON games (matchup);
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_moves_game_id
        ON moves (game_id);
        """
    )

    conn.commit()
    cur.close()
    conn.close()


def get_latest_source_game_date(username):
    # Zwraca datę ostatniej zapisanej partii źródłowej dla danego gracza.
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


def delete_old_source_games(cutoff_datetime: datetime) -> int:
    # Usuwa źródłowe partie starsze niż ustalony cutoff.
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        DELETE FROM source_games
        WHERE played_at IS NOT NULL
          AND played_at < %s;
        """,
        (cutoff_datetime,),
    )

    deleted = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return deleted


def strip_raw_json_from_source_games():
    # Czyści pełny JSON z rekordów źródłowych, żeby oszczędzić miejsce.
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


def get_games_count():
    # Zwraca łączną liczbę wygenerowanych partii.
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM games;")
    count = cur.fetchone()[0]

    cur.close()
    conn.close()
    return count


def insert_game(white: str, black: str, result: str, move_count: int, matchup: str | None = None) -> int:
    # Zapisuje jedną wygenerowaną partię i zwraca jej ID.
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO games (white_bot, black_bot, result, move_count, matchup)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id;
        """,
        (white, black, result, move_count, matchup),
    )

    game_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return game_id


def insert_move(
    game_id: int,
    move_number: int,
    player: str,
    move: str,
    fen: str,
    is_capture: bool = False,
    is_check: bool = False,
    is_castle: bool = False,
    eval_score: float | None = None,
):
    # Zapisuje pojedynczy ruch do tabeli moves.
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO moves (
            game_id, move_number, player, move, fen, is_capture, is_check, is_castle, eval
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        """,
        (game_id, move_number, player, move, fen, is_capture, is_check, is_castle, eval_score),
    )

    conn.commit()
    cur.close()
    conn.close()


def insert_source_game_with_cursor(cur, record):
    # Zapisuje jedną partię źródłową przy użyciu już otwartego kursora.
    # Dzięki ON CONFLICT nie tworzy duplikatów.
    cur.execute(
        """
        INSERT INTO source_games (
            source,
            username,
            game_url,
            played_at,
            white_username,
            black_username,
            player_color,
            player_result,
            time_class,
            time_control,
            rules,
            rated,
            pgn,
            raw_json
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


def upsert_style_profile(player_name: str, source_game_count: int, metrics: dict, profile_json: dict):
    # Zapisuje lub aktualizuje profil stylu danego gracza.
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO style_profiles (
            player_name,
            source_game_count,
            avg_halfmoves,
            avg_fullmoves,
            avg_captures,
            avg_player_captures,
            castle_rate,
            kingside_castle_rate,
            queenside_castle_rate,
            check_rate,
            player_check_rate,
            avg_time_class_weight,
            bullet_share,
            blitz_share,
            rapid_share,
            win_rate,
            draw_rate,
            loss_rate,
            profile_json,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (player_name) DO UPDATE SET
            source_game_count = EXCLUDED.source_game_count,
            avg_halfmoves = EXCLUDED.avg_halfmoves,
            avg_fullmoves = EXCLUDED.avg_fullmoves,
            avg_captures = EXCLUDED.avg_captures,
            avg_player_captures = EXCLUDED.avg_player_captures,
            castle_rate = EXCLUDED.castle_rate,
            kingside_castle_rate = EXCLUDED.kingside_castle_rate,
            queenside_castle_rate = EXCLUDED.queenside_castle_rate,
            check_rate = EXCLUDED.check_rate,
            player_check_rate = EXCLUDED.player_check_rate,
            avg_time_class_weight = EXCLUDED.avg_time_class_weight,
            bullet_share = EXCLUDED.bullet_share,
            blitz_share = EXCLUDED.blitz_share,
            rapid_share = EXCLUDED.rapid_share,
            win_rate = EXCLUDED.win_rate,
            draw_rate = EXCLUDED.draw_rate,
            loss_rate = EXCLUDED.loss_rate,
            profile_json = EXCLUDED.profile_json,
            updated_at = NOW();
        """,
        (
            player_name,
            source_game_count,
            metrics.get("avg_halfmoves"),
            metrics.get("avg_fullmoves"),
            metrics.get("avg_captures"),
            metrics.get("avg_player_captures"),
            metrics.get("castle_rate"),
            metrics.get("kingside_castle_rate"),
            metrics.get("queenside_castle_rate"),
            metrics.get("check_rate"),
            metrics.get("player_check_rate"),
            metrics.get("avg_time_class_weight"),
            metrics.get("bullet_share"),
            metrics.get("blitz_share"),
            metrics.get("rapid_share"),
            metrics.get("win_rate"),
            metrics.get("draw_rate"),
            metrics.get("loss_rate"),
            Json(profile_json),
        ),
    )

    conn.commit()
    cur.close()
    conn.close()
