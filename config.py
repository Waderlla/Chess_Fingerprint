from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Wczytanie zmiennych środowiskowych z pliku .env
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

# Ile lat danych źródłowych trzymamy do budowy stylu.
# Dzięki temu baza nie rośnie bez końca.
SOURCE_GAMES_RETENTION_YEARS = int(os.getenv("SOURCE_GAMES_RETENTION_YEARS", "5"))

# Przy syncu wracamy o 1 miesiąc, żeby bezpiecznie złapać ewentualne opóźnione dane.
FETCH_LOOKBACK_MONTHS = int(os.getenv("FETCH_LOOKBACK_MONTHS", "1"))

# Dla oszczędności miejsca można wyłączyć zapis pełnego raw_json.
DISABLE_RAW_JSON_STORAGE = os.getenv("DISABLE_RAW_JSON_STORAGE", "true").lower() == "true"

# ===== SILNIK STOCKFISH =====

ENGINE_TIME_LIMIT = float(os.getenv("ENGINE_TIME_LIMIT", "0.2"))
ENGINE_TOP_MOVES = int(os.getenv("ENGINE_TOP_MOVES", "3"))


def _autodetect_stockfish():
    """
    Szuka pliku silnika w folderze ./stockfish obok projektu.
    Obsługuje najczęstsze nazwy plików na Windows / Linux / macOS.
    """
    root = Path(__file__).resolve().parent / "stockfish"
    if not root.exists():
        return ""

    patterns = [
        "*stockfish*.exe",
        "*stockfish*",
    ]

    for pattern in patterns:
        for path in root.rglob(pattern):
            if path.is_file():
                return str(path)

    return ""


# Najpierw próbujemy wziąć ścieżkę z .env, a jeśli jej nie ma,
# próbujemy znaleźć silnik automatycznie w lokalnym folderze stockfish/.
STOCKFISH_PATH = os.getenv("STOCKFISH_PATH", "").strip() or _autodetect_stockfish()
