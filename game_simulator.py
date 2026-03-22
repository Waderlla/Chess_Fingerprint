import chess

from database import create_tables, insert_game, insert_move
from engine_wrapper import EngineWrapper
from move_selector import choose_move_by_style
from style_loader import load_all_profiles


def move_to_player(board_before):
    # Zamienia turę silnika na nazwę gracza white/black.
    return "white" if board_before.turn == chess.WHITE else "black"


def simulate_game(white_bot_name, black_bot_name, profiles):
    # Rozgrywa jedną partię pomiędzy dwoma botami i zapisuje ją do bazy.
    board = chess.Board()
    engine = EngineWrapper()

    moves_data = []
    fullmove_number = 1

    try:
        while not board.is_game_over():
            board_before = board.copy()
            candidates = engine.get_top_moves(board)

            if board.turn == chess.WHITE:
                profile = profiles[white_bot_name]
            else:
                profile = profiles[black_bot_name]

            move = choose_move_by_style(candidates, profile)

            if move is None:
                break

            player = move_to_player(board_before)
            san = board_before.san(move)

            is_capture = board_before.is_capture(move)
            is_check = board_before.gives_check(move)
            is_castle = board_before.is_castling(move)

            board.push(move)

            moves_data.append(
                {
                    "move_number": fullmove_number,
                    "player": player,
                    "move": san,
                    "fen": board.fen(),
                    "is_capture": is_capture,
                    "is_check": is_check,
                    "is_castle": is_castle,
                    "eval": 0,
                }
            )

            if player == "black":
                fullmove_number += 1

        result = board.result()
        matchup = f"{white_bot_name} vs {black_bot_name}"

        game_id = insert_game(
            white=white_bot_name,
            black=black_bot_name,
            result=result,
            move_count=len(moves_data),
            matchup=matchup,
        )

        for m in moves_data:
            insert_move(
                game_id=game_id,
                move_number=m["move_number"],
                player=m["player"],
                move=m["move"],
                fen=m["fen"],
                is_capture=m["is_capture"],
                is_check=m["is_check"],
                is_castle=m["is_castle"],
                eval_score=m["eval"],
            )

        print(f"Zapisano grę: {game_id}, {matchup}, wynik: {result}")

    finally:
        engine.close()


def run_match_series():
    # Rozgrywa jedną rundę czterech dozwolonych matchupów.
    create_tables()
    profiles = load_all_profiles()

    pairings = [
        ("MagnusBot", "EcnalabBot"),
        ("EcnalabBot", "MagnusBot"),
        ("HikaruBot", "EcnalabBot"),
        ("EcnalabBot", "HikaruBot"),
    ]

    for white_bot, black_bot in pairings:
        simulate_game(white_bot, black_bot, profiles)


if __name__ == "__main__":
    run_match_series()
