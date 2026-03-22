import os

import chess
import chess.engine

from config import STOCKFISH_PATH, ENGINE_TIME_LIMIT, ENGINE_TOP_MOVES


class EngineWrapper:
    def __init__(self):
        # Sprawdza, czy plik silnika istnieje, zanim spróbuje go uruchomić.
        if not STOCKFISH_PATH:
            raise FileNotFoundError(
                "Nie ustawiono STOCKFISH_PATH i nie wykryto silnika w folderze ./stockfish"
            )
        if not os.path.exists(STOCKFISH_PATH):
            raise FileNotFoundError(f"Nie znaleziono pliku Stockfish: {STOCKFISH_PATH}")

        self.engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)

    def get_top_moves(self, board):
        # Pobiera TOP-N ruchów z silnika wraz z ich oceną.
        info = self.engine.analyse(
            board,
            chess.engine.Limit(time=ENGINE_TIME_LIMIT),
            multipv=ENGINE_TOP_MOVES,
        )

        moves = []
        for entry in info:
            pv = entry.get("pv")
            score = entry.get("score")

            if not pv:
                continue

            move = pv[0]

            cp = 0
            if score:
                pov = score.pov(board.turn)
                if pov.is_mate():
                    mate = pov.mate()
                    cp = 100000 if mate and mate > 0 else -100000
                else:
                    cp = pov.score() or 0

            moves.append({
                "move": move,
                "score": cp,
            })

        return moves

    def close(self):
        # Kończy proces silnika.
        self.engine.quit()
