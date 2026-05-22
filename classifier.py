from __future__ import annotations

import chess
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

from database import create_tables, get_connection, save_game_classifications
from pgn_parser import load_pgn_game, parse_game_features

PLAYERS = {"MagnusCarlsen": 0, "hikaru": 1}
PLAYER_NAMES = ["MagnusCarlsen", "hikaru"]

FEATURE_NAMES = [
    "fullmoves_norm",
    "captures_per_move",
    "checks_per_move",
    "castled",
    "castle_kingside",
    "castle_queenside",
    "time_bullet",
    "time_blitz",
    "time_rapid",
]


def _feature_vector(fullmoves, captures, checks, castled, castle_ks, castle_qs, time_class):
    n = max(fullmoves, 1)
    return [
        min(fullmoves / 60.0, 2.0),
        captures / n,
        checks / n,
        castled,
        castle_ks,
        castle_qs,
        1 if time_class == "bullet" else 0,
        1 if time_class == "blitz" else 0,
        1 if time_class == "rapid" else 0,
    ]


def game_to_features(parsed: dict, time_class: str) -> list[float]:
    castle_type = parsed.get("player_castle_type")
    return _feature_vector(
        fullmoves=parsed.get("fullmoves", 0) or 0,
        captures=parsed.get("player_captures", 0) or 0,
        checks=parsed.get("player_checks", 0) or 0,
        castled=1 if parsed.get("player_castled") else 0,
        castle_ks=1 if castle_type == "kingside" else 0,
        castle_qs=1 if castle_type == "queenside" else 0,
        time_class=time_class,
    )


def collect_move_vectors(pgn: str, player_color: str, time_class: str) -> list[tuple[int, list[float]]]:
    """
    Przetwarza partię i zwraca listę (move_number, feature_vector) dla każdego ruchu.
    Wektory są potem przekazywane do predict_proba w jednej zbiorczej operacji.
    """
    game = load_pgn_game(pgn)
    if game is None:
        return []

    board = game.board()
    target_turn = chess.WHITE if player_color == "white" else chess.BLACK

    captures = checks = castled = castle_ks = castle_qs = 0
    results = []
    halfmove = 0

    for move in game.mainline_moves():
        mover = board.turn
        is_cap = board.is_capture(move)
        is_ks = board.is_kingside_castling(move)
        is_qs = board.is_queenside_castling(move)
        board.push(move)
        is_chk = board.is_check()
        halfmove += 1

        if mover == target_turn:
            if is_cap:
                captures += 1
            if is_chk:
                checks += 1
            if not castled and (is_ks or is_qs):
                castled = 1
                castle_ks = 1 if is_ks else 0
                castle_qs = 1 if is_qs else 0

        move_number = (halfmove + 1) // 2
        vec = _feature_vector(move_number, captures, checks, castled, castle_ks, castle_qs, time_class)
        results.append((move_number, vec))

    return results


def load_games() -> list[tuple]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT username, player_color, time_class, pgn, game_url
        FROM source_games
        WHERE pgn IS NOT NULL
          AND username IN ('MagnusCarlsen', 'hikaru')
          AND player_color IS NOT NULL;
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def main():
    create_tables()

    print("Ładowanie partii z bazy...")
    rows = load_games()
    print(f"Znaleziono {len(rows)} partii.")

    dataset = []
    skipped = 0
    for username, player_color, time_class, pgn, game_url in rows:
        if username not in PLAYERS:
            continue
        parsed = parse_game_features(pgn, player_color)
        if parsed is None:
            skipped += 1
            continue
        features = game_to_features(parsed, time_class or "")
        dataset.append((features, PLAYERS[username], username, player_color, time_class or "", pgn, game_url))

    if skipped:
        print(f"Pominięto {skipped} partii z błędnym PGN.")
    print(f"Załadowano {len(dataset)} poprawnych partii.")

    X = np.array([d[0] for d in dataset])
    y = np.array([d[1] for d in dataset])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"Trening: {len(X_train)} | Test: {len(X_test)}")
    print("Trenuję klasyfikator...")

    clf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    print(f"\nDokładność: {accuracy_score(y_test, y_pred):.1%}")
    print(classification_report(y_test, y_pred, target_names=PLAYER_NAMES))

    # Zbieramy wszystkie wektory naraz i klasyfikujemy jednym wywołaniem.
    # Potem zapisujemy jeden wiersz na partię (nie na ruch) — 1000 wierszy zamiast 70 000.
    print("Zbieram wektory ruchów...", flush=True)
    per_game_meta = []
    offsets = []
    all_vecs = []

    for _, _, username, player_color, time_class, pgn, game_url in dataset:
        if game_url is None:
            continue
        move_vecs = collect_move_vectors(pgn, player_color, time_class)
        if not move_vecs:
            continue
        start = len(all_vecs)
        move_numbers = [m for m, _ in move_vecs]
        all_vecs.extend(v for _, v in move_vecs)
        offsets.append((start, len(move_vecs)))
        per_game_meta.append((game_url, username, move_numbers))

    print(f"Łącznie wektorów: {len(all_vecs)}. Klasyfikuję jednym wywołaniem...", flush=True)
    all_probs = clf.predict_proba(np.array(all_vecs))

    magnus_idx = PLAYERS["MagnusCarlsen"]
    hikaru_idx = PLAYERS["hikaru"]

    classifications = []
    for (game_url, username, move_numbers), (start, length) in zip(per_game_meta, offsets):
        probs_slice = all_probs[start : start + length]
        move_probs = [
            {
                "move_number": mn,
                "magnus_prob": round(float(p[magnus_idx]), 4),
                "hikaru_prob": round(float(p[hikaru_idx]), 4),
            }
            for mn, p in zip(move_numbers, probs_slice)
        ]
        classifications.append({
            "game_url": game_url,
            "username": username,
            "move_probs": move_probs,
        })

    print(f"Zapisuję {len(classifications)} partii (jeden wiersz na partię)...", flush=True)
    save_game_classifications(classifications)
    print("Gotowe.", flush=True)


if __name__ == "__main__":
    main()
