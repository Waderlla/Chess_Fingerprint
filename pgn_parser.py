from __future__ import annotations

import io

import chess
import chess.pgn


def load_pgn_game(pgn_text):
    # Wczytuje pojedynczą partię PGN z tekstu.
    if not pgn_text or not pgn_text.strip():
        return None
    stream = io.StringIO(pgn_text)
    return chess.pgn.read_game(stream)


def safe_read_headers(game):
    # Bezpiecznie odczytuje nagłówki PGN.
    headers = game.headers if game else {}
    return {
        "event": headers.get("Event", ""),
        "site": headers.get("Site", ""),
        "date": headers.get("Date", ""),
        "white": headers.get("White", ""),
        "black": headers.get("Black", ""),
        "result": headers.get("Result", ""),
        "opening": headers.get("Opening", ""),
        "eco": headers.get("ECO", ""),
        "termination": headers.get("Termination", ""),
        "white_elo": headers.get("WhiteElo", ""),
        "black_elo": headers.get("BlackElo", ""),
    }


def classify_result(result: str):
    # Uproszczona klasyfikacja wyniku partii.
    if result == "1-0":
        return "white_win"
    if result == "0-1":
        return "black_win"
    if result == "1/2-1/2":
        return "draw"
    return "unknown"


def count_piece_captures(game):
    # Liczy wszystkie bicia w partii.
    board = game.board()
    captures = 0
    for move in game.mainline_moves():
        if board.is_capture(move):
            captures += 1
        board.push(move)
    return captures


def count_player_captures(game, player_color):
    # Liczy bicia wykonane tylko przez badanego gracza.
    board = game.board()
    captures = 0
    target_turn = chess.WHITE if player_color == "white" else chess.BLACK

    for move in game.mainline_moves():
        mover = board.turn
        if mover == target_turn and board.is_capture(move):
            captures += 1
        board.push(move)

    return captures


def count_checks(game):
    # Liczy wszystkie szachy w partii.
    board = game.board()
    checks = 0

    for move in game.mainline_moves():
        board.push(move)
        if board.is_check():
            checks += 1

    return checks


def count_player_checks(game, player_color):
    # Liczy szachy dane przez badanego gracza.
    board = game.board()
    checks = 0
    target_turn = chess.WHITE if player_color == "white" else chess.BLACK

    for move in game.mainline_moves():
        mover = board.turn
        board.push(move)
        if mover == target_turn and board.is_check():
            checks += 1

    return checks


def detect_castle_type(san_moves, player_color):
    # Wykrywa rodzaj roszady badanego gracza.
    player_moves = san_moves[0::2] if player_color == "white" else san_moves[1::2]
    if "O-O-O" in player_moves:
        return "queenside"
    if "O-O" in player_moves:
        return "kingside"
    return None


def extract_san_moves(game):
    # Zwraca listę ruchów w notacji SAN.
    board = game.board()
    san_moves = []

    for move in game.mainline_moves():
        san = board.san(move)
        san_moves.append(san)
        board.push(move)

    return san_moves


def parse_game_features(pgn_text, player_color=None):
    # Zamienia PGN na zestaw cech używany później do budowy profilu stylu.
    game = load_pgn_game(pgn_text)
    if game is None:
        return None

    headers = safe_read_headers(game)
    san_moves = extract_san_moves(game)
    halfmoves = len(san_moves)
    fullmoves = (halfmoves + 1) // 2
    total_captures = count_piece_captures(game)
    total_checks = count_checks(game)

    features = {
        "headers": headers,
        "result_class": classify_result(headers["result"]),
        "halfmoves": halfmoves,
        "fullmoves": fullmoves,
        "total_captures": total_captures,
        "total_checks": total_checks,
        "san_moves": san_moves,
        "opening": headers["opening"],
        "eco": headers["eco"],
        "termination": headers["termination"],
    }

    if player_color in {"white", "black"}:
        castle_type = detect_castle_type(san_moves, player_color)
        features.update(
            {
                "player_color": player_color,
                "player_captures": count_player_captures(game, player_color),
                "player_checks": count_player_checks(game, player_color),
                "player_castled": castle_type is not None,
                "player_castle_type": castle_type,
            }
        )

    return features
