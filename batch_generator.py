from database import create_tables, get_games_count
from game_simulator import simulate_game
from style_loader import load_all_profiles

# Bezpieczny limit liczby symulowanych partii w bazie.
MAX_GAMES = 500


def generate_batch(rounds=25):
    # Generuje większą serię partii i zatrzymuje się po osiągnięciu limitu.
    create_tables()
    profiles = load_all_profiles()

    pairings = [
        ("MagnusBot", "EcnalabBot"),
        ("EcnalabBot", "MagnusBot"),
        ("HikaruBot", "EcnalabBot"),
        ("EcnalabBot", "HikaruBot"),
    ]

    total = get_games_count()
    print(f"Start: masz już {total} gier w bazie")

    for round_no in range(1, rounds + 1):
        print(f"\n=== Runda {round_no}/{rounds} ===")

        for white_bot, black_bot in pairings:
            if total >= MAX_GAMES:
                print(f"\n⛔ STOP — osiągnięto limit {MAX_GAMES} gier")
                return

            print(f"Gram: {white_bot} vs {black_bot}")
            simulate_game(white_bot, black_bot, profiles)
            total += 1
            print(f"Łącznie gier: {total}/{MAX_GAMES}")

    print(f"\nGotowe. Wygenerowano {total} gier.")


if __name__ == "__main__":
    generate_batch(rounds=25)
