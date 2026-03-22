from database import get_connection


MAX_GAMES = 500  # ile partii chcesz trzymać


def cleanup_games():
    conn = get_connection()
    cur = conn.cursor()

    # pobierz ID najnowszych gier
    cur.execute("""
        SELECT id
        FROM games
        ORDER BY id DESC
        LIMIT %s;
    """, (MAX_GAMES,))

    keep_ids = [row[0] for row in cur.fetchall()]

    if not keep_ids:
        print("Brak gier do utrzymania.")
        cur.close()
        conn.close()
        return

    # zamieniamy listę ID na string SQL (bezpiecznie)
    ids_tuple = tuple(keep_ids)

    # usuwamy stare ruchy
    cur.execute(f"""
        DELETE FROM moves
        WHERE game_id NOT IN {ids_tuple};
    """)

    # usuwamy stare gry
    cur.execute(f"""
        DELETE FROM games
        WHERE id NOT IN {ids_tuple};
    """)

    conn.commit()
    cur.close()
    conn.close()

    print(f"Zostawiono {len(keep_ids)} najnowszych gier.")
    print("Stare symulacje usunięte.")


if __name__ == "__main__":
    cleanup_games()
