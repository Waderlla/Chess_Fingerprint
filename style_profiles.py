from __future__ import annotations


def clamp(value, low=0.0, high=1.0) :
    # Ogranicza wartość do przedziału 0..1.
    return max(low, min(high, value))


def build_profile(player_name, metrics):
    # Buduje profil stylu pojedynczego gracza na podstawie zagregowanych statystyk.
    avg_fullmoves = metrics.get("avg_fullmoves", 0.0) or 0.0
    avg_player_captures = metrics.get("avg_player_captures", 0.0) or 0.0
    castle_rate = metrics.get("castle_rate", 0.0) or 0.0
    player_check_rate = metrics.get("player_check_rate", 0.0) or 0.0
    blitz_share = metrics.get("blitz_share", 0.0) or 0.0
    rapid_share = metrics.get("rapid_share", 0.0) or 0.0
    win_rate = metrics.get("win_rate", 0.0) or 0.0

    long_game_bias = clamp(avg_fullmoves / 60.0) if avg_fullmoves else 0.5
    exchange_bias = clamp(avg_player_captures / 12.0) if avg_player_captures else 0.5
    tactical_bias = clamp((player_check_rate / 8.0) * 0.6 + blitz_share * 0.4)
    positional_bias = clamp(long_game_bias * 0.55 + castle_rate * 0.45)
    pacing_bias = clamp(rapid_share * 0.6 + long_game_bias * 0.4)

    # Dodatkowe cechy używane przy wyborze ruchu.
    precision_bias = clamp(
        positional_bias * 0.45
        + (1.0 - tactical_bias) * 0.30
        + win_rate * 0.25
    )

    aggression_bias = clamp(
        tactical_bias * 0.55
        + exchange_bias * 0.30
        + blitz_share * 0.15
    )

    return {
        "player_name": player_name,
        "long_game_bias": round(long_game_bias, 3),
        "exchange_bias": round(exchange_bias, 3),
        "tactical_bias": round(tactical_bias, 3),
        "positional_bias": round(positional_bias, 3),
        "pacing_bias": round(pacing_bias, 3),
        "precision_bias": round(precision_bias, 3),
        "aggression_bias": round(aggression_bias, 3),
        "derived_from_games": metrics.get("games_count", 0),
    }


def build_ecnalab_profile(profile_a, profile_b):
    # Buduje profil hybrydowy 50/50.
    numeric_keys = [
        "long_game_bias",
        "exchange_bias",
        "tactical_bias",
        "positional_bias",
        "pacing_bias",
        "precision_bias",
        "aggression_bias",
    ]

    profile = {"player_name": "Ecnalab"}
    for key in numeric_keys:
        profile[key] = round(
            (profile_a.get(key, 0.5) + profile_b.get(key, 0.5)) / 2,
            3,
        )

    profile["derived_from_games"] = min(
        profile_a.get("derived_from_games", 0),
        profile_b.get("derived_from_games", 0),
    )
    return profile
