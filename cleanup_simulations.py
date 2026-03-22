from database import get_connection


def delete_all_simulations():
    # Usuwa wszystkie wygenerowane partie i ruchy.
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM moves;")
    cur.execute("DELETE FROM games;")

    conn.commit()
    cur.close()
    conn.close()

    print("Usunięto wszystkie symulowane partie i ruchy.")


if __name__ == "__main__":
    delete_all_simulations()
