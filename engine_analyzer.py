from __future__ import annotations

import shutil

import chess
import chess.engine

from config import ENGINE_TIME_MS
from database import get_unanalyzed_games, save_engine_features
from pgn_parser import load_pgn_game

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}


def _material(board: chess.Board, color: chess.Color) -> int:
    return sum(PIECE_VALUES[pt] * len(board.pieces(pt, color)) for pt in PIECE_VALUES)


def analyze_game(
    pgn_text: str,
    player_color: str,
    engine: chess.engine.SimpleEngine,
    time_sec: float,
) -> dict | None:
    game = load_pgn_game(pgn_text)
    if game is None:
        return None

    board = game.board()
    target = chess.WHITE if player_color == "white" else chess.BLACK
    limit = chess.engine.Limit(time=time_sec)

    cpls: list[float] = []
    best_move_matches = 0
    sacrifices = 0

    for move in game.mainline_moves():
        if board.turn != target:
            board.push(move)
            continue

        try:
            info_before = engine.analyse(board, limit)
        except Exception:
            board.push(move)
            continue

        score_before = info_before["score"].white().score(mate_score=1000)
        best_move = info_before["pv"][0] if info_before.get("pv") else None
        mat_before = _material(board, target)

        board.push(move)

        try:
            info_after = engine.analyse(board, limit)
        except Exception:
            continue

        score_after = info_after["score"].white().score(mate_score=1000)
        mat_after = _material(board, target)

        if player_color == "white":
            cpl = score_before - score_after
        else:
            cpl = score_after - score_before
        cpl = max(0.0, min(float(cpl), 500.0))

        cpls.append(cpl)

        if best_move == move:
            best_move_matches += 1

        # Ofiara: gracz oddał materiał (>= pion), ale silnik to akceptuje (CPL <= 30)
        if (mat_after - mat_before) <= -100 and cpl <= 30:
            sacrifices += 1

    n = len(cpls)
    if n == 0:
        return None

    return {
        "acpl": round(sum(cpls) / n, 1),
        "best_move_rate": round(best_move_matches / n, 3),
        "inaccuracy_rate": round(sum(1 for c in cpls if 10 <= c < 50) / n, 3),
        "mistake_rate": round(sum(1 for c in cpls if 50 <= c < 100) / n, 3),
        "blunder_rate": round(sum(1 for c in cpls if c >= 100) / n, 3),
        "sacrifice_rate": round(sacrifices / n, 3),
        "moves_analyzed": n,
    }


def main():
    stockfish_path = shutil.which("stockfish")
    if not stockfish_path:
        print("BŁĄD: Stockfish nie znaleziony w PATH.")
        print("Zainstaluj: sudo apt-get install -y stockfish  (Linux)")
        print("lub pobierz z https://stockfishchess.org i dodaj do PATH.")
        return

    time_sec = ENGINE_TIME_MS / 1000.0
    rows = get_unanalyzed_games()
    total = len(rows)
    print(f"Partii do analizy silnikiem: {total}")

    if total == 0:
        print("Wszystkie partie są już zanalizowane.")
        return

    done = errors = 0
    with chess.engine.SimpleEngine.popen_uci(stockfish_path) as engine:
        for game_url, pgn, player_color in rows:
            features = analyze_game(pgn, player_color, engine, time_sec)
            if features:
                save_engine_features(game_url, features)
                done += 1
            else:
                errors += 1

            if (done + errors) % 50 == 0:
                print(f"  {done + errors}/{total} przetworzonych...", flush=True)

    print(f"Gotowe. Zanalizowano: {done}, błędy: {errors}.")


if __name__ == "__main__":
    main()
