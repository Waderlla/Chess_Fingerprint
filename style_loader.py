from __future__ import annotations

from database import get_connection


def _default_profile(player_name):
    # Profil awaryjny, gdy w bazie nie ma jeszcze policzonego profilu.
    return {
        "player_name": player_name,
        "long_game_bias": 0.5,
        "exchange_bias": 0.5,
        "tactical_bias": 0.5,
        "positional_bias": 0.5,
        "pacing_bias": 0.5,
        "precision_bias": 0.5,
        "aggression_bias": 0.5,
        "derived_from_games": 0,
    }


def load_profile(player_name):
    # Ładuje profil stylu z bazy.
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT profile_json
        FROM style_profiles
        WHERE player_name = %s;
        """,
        (player_name,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row or not row[0]:
        return _default_profile(player_name)

    profile = row[0]
    profile.setdefault("player_name", player_name)
    profile.setdefault("long_game_bias", 0.5)
    profile.setdefault("exchange_bias", 0.5)
    profile.setdefault("tactical_bias", 0.5)
    profile.setdefault("positional_bias", 0.5)
    profile.setdefault("pacing_bias", 0.5)
    profile.setdefault("precision_bias", 0.5)
    profile.setdefault("aggression_bias", 0.5)
    profile.setdefault("derived_from_games", 0)
    return profile


def load_all_profiles():
    # Ładuje komplet profili używanych przez symulator.
    return {
        "MagnusBot": load_profile("MagnusCarlsen"),
        "HikaruBot": load_profile("hikaru"),
        "EcnalabBot": load_profile("Ecnalab"),
    }
