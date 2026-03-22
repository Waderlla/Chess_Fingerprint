from database import get_connection


VALID_MATCHUPS = [
    "MagnusBot vs EcnalabBot",
    "EcnalabBot vs MagnusBot",
    "HikaruBot vs EcnalabBot",
    "EcnalabBot vs HikaruBot",
]


def print_matchup_stats():
    # Raportuje statystyki tylko dla docelowych matchupów.
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            matchup,
            COUNT(*) AS games,
            SUM(CASE WHEN result = '1-0' THEN 1 ELSE 0 END) AS white_wins,
            SUM(CASE WHEN result = '0-1' THEN 1 ELSE 0 END) AS black_wins,
            SUM(CASE WHEN result = '1/2-1/2' THEN 1 ELSE 0 END) AS draws,
            AVG(move_count) AS avg_moves
        FROM games
        WHERE matchup = ANY(%s)
        GROUP BY matchup
        ORDER BY matchup;
        """,
        (VALID_MATCHUPS,),
    )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    print("\n=== STATYSTYKI MATCHUPÓW ===")
    for row in rows:
        matchup, games, white_wins, black_wins, draws, avg_moves = row
        print(f"\n{matchup}")
        print(f"  gier: {games}")
        print(f"  wygrane białych: {white_wins}")
        print(f"  wygrane czarnych: {black_wins}")
        print(f"  remisy: {draws}")
        print(f"  średnia liczba ruchów: {round(avg_moves or 0, 2)}")


if __name__ == "__main__":
    print_matchup_stats()
