from __future__ import annotations

from collections import Counter
from statistics import mean

# Wagi pomocnicze dla różnych temp gry.
TIME_CLASS_WEIGHTS = {
    "bullet": 0.6,
    "blitz": 1.0,
    "rapid": 1.2,
    "daily": 1.5,
}


def normalize_result(player_result):
    # Ujednolica różne nazwy wyników z Chess.com do win/draw/loss.
    if player_result == "win":
        return "win"

    if player_result in {"agreed", "repetition", "stalemate", "timevsinsufficient", "insufficient", "50move"}:
        return "draw"

    if player_result in {"checkmated", "timeout", "resigned", "lose", "abandoned"}:
        return "loss"

    return "other"


def aggregate_style_features(parsed_games, source_rows):
    # Agreguje cechy z wielu partii do jednego profilu statystycznego.
    if not parsed_games:
        return {
            "games_count": 0,
            "avg_halfmoves": 0.0,
            "avg_fullmoves": 0.0,
            "avg_captures": 0.0,
            "avg_player_captures": 0.0,
            "castle_rate": 0.0,
            "kingside_castle_rate": 0.0,
            "queenside_castle_rate": 0.0,
            "check_rate": 0.0,
            "player_check_rate": 0.0,
            "avg_time_class_weight": 0.0,
            "bullet_share": 0.0,
            "blitz_share": 0.0,
            "rapid_share": 0.0,
            "win_rate": 0.0,
            "draw_rate": 0.0,
            "loss_rate": 0.0,
        }

    halfmoves = [g["halfmoves"] for g in parsed_games]
    fullmoves = [g["fullmoves"] for g in parsed_games]
    captures = [g["total_captures"] for g in parsed_games]
    player_captures = [g.get("player_captures", 0) for g in parsed_games]
    total_checks = [g["total_checks"] for g in parsed_games]
    player_checks = [g.get("player_checks", 0) for g in parsed_games]

    castle_count = sum(1 for g in parsed_games if g.get("player_castled"))
    kingside_count = sum(1 for g in parsed_games if g.get("player_castle_type") == "kingside")
    queenside_count = sum(1 for g in parsed_games if g.get("player_castle_type") == "queenside")

    time_classes = [row.get("time_class") for row in source_rows]
    time_counter = Counter(time_classes)
    total_rows = len(source_rows)

    weighted = [TIME_CLASS_WEIGHTS.get(row.get("time_class"), 1.0) for row in source_rows]

    results = [normalize_result(row.get("player_result")) for row in source_rows]
    result_counter = Counter(results)

    return {
        "games_count": len(parsed_games),
        "avg_halfmoves": round(mean(halfmoves), 2),
        "avg_fullmoves": round(mean(fullmoves), 2),
        "avg_captures": round(mean(captures), 2),
        "avg_player_captures": round(mean(player_captures), 2),
        "castle_rate": round(castle_count / len(parsed_games), 4),
        "kingside_castle_rate": round(kingside_count / len(parsed_games), 4),
        "queenside_castle_rate": round(queenside_count / len(parsed_games), 4),
        "check_rate": round(mean(total_checks), 2),
        "player_check_rate": round(mean(player_checks), 2),
        "avg_time_class_weight": round(mean(weighted), 3) if weighted else 0.0,
        "bullet_share": round(time_counter.get("bullet", 0) / total_rows, 4) if total_rows else 0.0,
        "blitz_share": round(time_counter.get("blitz", 0) / total_rows, 4) if total_rows else 0.0,
        "rapid_share": round(time_counter.get("rapid", 0) / total_rows, 4) if total_rows else 0.0,
        "win_rate": round(result_counter.get("win", 0) / total_rows, 4) if total_rows else 0.0,
        "draw_rate": round(result_counter.get("draw", 0) / total_rows, 4) if total_rows else 0.0,
        "loss_rate": round(result_counter.get("loss", 0) / total_rows, 4) if total_rows else 0.0,
    }
