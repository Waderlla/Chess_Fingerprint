from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from database import get_connection

# Katalog, z którego serwer WWW (Caddy) podaje dane stronie.
# Na VPS ustawiany w usłudze systemd (EXPORT_DIR=/srv/chess/data).
EXPORT_DIR = Path(os.getenv("EXPORT_DIR", "public"))

PLAYERS = ["MagnusCarlsen", "hikaru"]

STAT_FIELDS = [
    "games_count",
    "avg_fullmoves",
    "avg_captures_per_move",
    "avg_checks_per_move",
    "castle_rate",
    "kingside_castle_rate",
    "queenside_castle_rate",
    "win_rate",
    "draw_rate",
    "loss_rate",
    "bullet_share",
    "blitz_share",
    "rapid_share",
]


def load_player_stats() -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT username, {", ".join(STAT_FIELDS)}
        FROM player_stats
        WHERE username = ANY(%s);
        """,
        (PLAYERS,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {row[0]: dict(zip(STAT_FIELDS, row[1:])) for row in rows}


def load_classified_games() -> list[dict]:
    """Partie z klasyfikacją ruch po ruchu + dane potrzebne do odtworzenia na szachownicy."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT gc.game_url, gc.username, gc.move_probs,
               sg.pgn, sg.white_username, sg.black_username,
               sg.played_at, sg.time_class, sg.player_result
        FROM game_classifications gc
        JOIN source_games sg ON sg.game_url = gc.game_url
        WHERE sg.pgn IS NOT NULL
        ORDER BY sg.played_at DESC NULLS LAST;
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    games = []
    for game_url, username, move_probs, pgn, white, black, played_at, time_class, result in rows:
        games.append({
            "game_url": game_url,
            "username": username,
            "pgn": pgn,
            "white_username": white,
            "black_username": black,
            "played_at": played_at.isoformat() if played_at else None,
            "time_class": time_class,
            "player_result": result,
            # Tylko prawdopodobieństwo Magnusa - Hikaru to zawsze 1 - p.
            "magnus_probs": [m["magnus_prob"] for m in move_probs],
        })
    return games


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main():
    stats = load_player_stats()
    games = load_classified_games()

    # Pusta baza (np. nieudany sync) nie może skasować danych, które strona już pokazuje.
    if len(stats) < len(PLAYERS) or not games:
        print(f"Za mało danych do eksportu (gracze: {len(stats)}, partie: {len(games)}). Zostawiam poprzedni eksport.")
        return

    # Budujemy nowy eksport obok i podmieniamy katalog na końcu,
    # żeby strona nigdy nie trafiła na pół-zapisane pliki.
    tmp_dir = EXPORT_DIR.with_name(EXPORT_DIR.name + ".new")
    old_dir = EXPORT_DIR.with_name(EXPORT_DIR.name + ".old")
    shutil.rmtree(tmp_dir, ignore_errors=True)
    (tmp_dir / "games").mkdir(parents=True)

    updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    write_json(tmp_dir / "stats.json", {"updated_at": updated_at, "players": stats})
    write_json(tmp_dir / "games" / "index.json", {"updated_at": updated_at, "count": len(games)})
    for i, game in enumerate(games):
        write_json(tmp_dir / "games" / f"{i}.json", game)

    shutil.rmtree(old_dir, ignore_errors=True)
    if EXPORT_DIR.exists():
        EXPORT_DIR.rename(old_dir)
    tmp_dir.rename(EXPORT_DIR)
    shutil.rmtree(old_dir, ignore_errors=True)

    print(f"Wyeksportowano statystyki {len(stats)} graczy i {len(games)} partii do {EXPORT_DIR}.")


if __name__ == "__main__":
    main()
