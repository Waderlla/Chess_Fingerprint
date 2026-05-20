from __future__ import annotations

import chess
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

from database import create_tables, get_connection, save_game_classifications
from pgn_parser import load_pgn_game, parse_game_features

# Magnus = 0, Hikaru = 1
PLAYERS = {"MagnusCarlsen": 0, "hikaru": 1}
PLAYER_NAMES = ["MagnusCarlsen", "hikaru"]

# Cechy używane przez klasyfikator (jedna partia = jeden wektor)
FEATURE_NAMES = [
    "fullmoves_norm",       # długość gry znormalizowana przez 60
    "captures_per_move",    # bicia gracza / liczba ruchów
    "checks_per_move",      # szachy gracza / liczba ruchów
    "castled",              # czy wykonał roszadę (0/1)
    "castle_kingside",      # roszada królewska (0/1)
    "castle_queenside",     # roszada hetmańska (0/1)
    "time_bullet",          # tryb gry bullet (0/1)
    "time_blitz",           # tryb gry blitz (0/1)
    "time_rapid",           # tryb gry rapid (0/1)
]


def _to_feature_vector(fullmoves, captures, checks, castled, castle_ks, castle_qs, time_class):
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
    return _to_feature_vector(
        fullmoves=parsed.get("fullmoves", 0) or 0,
        captures=parsed.get("player_captures", 0) or 0,
        checks=parsed.get("player_checks", 0) or 0,
        castled=1 if parsed.get("player_castled") else 0,
        castle_ks=1 if castle_type == "kingside" else 0,
        castle_qs=1 if castle_type == "queenside" else 0,
        time_class=time_class,
    )


def classify_game_by_move(pgn: str, player_color: str, time_class: str, clf: RandomForestClassifier) -> list[dict]:
    """
    Przetwarza partię ruch po ruchu i zwraca prawdopodobieństwo klasyfikacji
    po każdym ruchu. Pozwala animować pasek pewności na stronie.
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
        features = [_to_feature_vector(move_number, captures, checks, castled, castle_ks, castle_qs, time_class)]
        probs = clf.predict_proba(features)[0]

        results.append({
            "move_number": move_number,
            "magnus_prob": round(float(probs[PLAYERS["MagnusCarlsen"]]), 4),
            "hikaru_prob": round(float(probs[PLAYERS["hikaru"]]), 4),
        })

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

    print(f"Trening: {len(X_train)} partii | Test: {len(X_test)} partii")
    print("Trenuję klasyfikator (Random Forest)...")

    clf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\nDokładność na zbiorze testowym: {acc:.1%}")
    print(classification_report(y_test, y_pred, target_names=PLAYER_NAMES))

    print("Obliczam prawdopodobieństwa ruch po ruchu dla wszystkich partii...")
    classifications = []
    for i, (_, _, username, player_color, time_class, pgn, game_url) in enumerate(dataset):
        if game_url is None:
            continue
        if (i + 1) % 200 == 0:
            print(f"  {i + 1}/{len(dataset)}")
        move_probs = classify_game_by_move(pgn, player_color, time_class, clf)
        for mp in move_probs:
            classifications.append({
                "game_url": game_url,
                "username": username,
                "move_number": mp["move_number"],
                "magnus_prob": mp["magnus_prob"],
                "hikaru_prob": mp["hikaru_prob"],
            })

    print(f"\nZapisuję {len(classifications)} rekordów do bazy...")
    save_game_classifications(classifications)
    print("Gotowe.")


if __name__ == "__main__":
    main()
