from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# ===== BAZA DANYCH (SUPABASE / POSTGRES) =====

DB_NAME = os.getenv("SUPABASE_DB_NAME", "postgres")
DB_USER = os.getenv("SUPABASE_DB_USER", "")
DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD", "")
DB_HOST = os.getenv("SUPABASE_DB_HOST", "")
DB_PORT = int(os.getenv("SUPABASE_DB_PORT", "5432"))

# ===== DANE ŹRÓDŁOWE =====

PLAYERS = [
    "hikaru",
    "MagnusCarlsen",
]

# Maksymalna liczba partii na gracza trzymana w bazie.
# Starsze partie są usuwane gdy przekroczymy ten limit.
MAX_GAMES_PER_PLAYER = int(os.getenv("MAX_GAMES_PER_PLAYER", "500"))

FETCH_LOOKBACK_MONTHS = int(os.getenv("FETCH_LOOKBACK_MONTHS", "1"))
DISABLE_RAW_JSON_STORAGE = os.getenv("DISABLE_RAW_JSON_STORAGE", "true").lower() == "true"
