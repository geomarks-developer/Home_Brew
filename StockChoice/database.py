"""SQLite persistence for stockchoice watchlists."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

DB_PATH = Path(__file__).resolve().with_name("stockchoice.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS watchlist (
                symbol TEXT PRIMARY KEY,
                added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def normalize_symbol(symbol: str) -> str:
    return str(symbol).strip().upper()


def load_watchlist() -> list[str]:
    init_database()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT symbol FROM watchlist ORDER BY added_at, rowid"
        ).fetchall()
    return [row["symbol"] for row in rows]


def add_to_watchlist(symbol: str) -> bool:
    symbol = normalize_symbol(symbol)
    if not symbol:
        return False
    init_database()
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO watchlist (symbol) VALUES (?)", (symbol,)
        )
        conn.commit()
        return cursor.rowcount > 0


def add_many_to_watchlist(symbols: Iterable[str]) -> int:
    normalized = list(dict.fromkeys(normalize_symbol(s) for s in symbols if normalize_symbol(s)))
    if not normalized:
        return 0
    init_database()
    added = 0
    with get_connection() as conn:
        for symbol in normalized:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO watchlist (symbol) VALUES (?)", (symbol,)
            )
            added += max(cursor.rowcount, 0)
        conn.commit()
    return added


def remove_from_watchlist(symbol: str) -> bool:
    symbol = normalize_symbol(symbol)
    init_database()
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol,))
        conn.commit()
        return cursor.rowcount > 0


def clear_watchlist() -> None:
    init_database()
    with get_connection() as conn:
        conn.execute("DELETE FROM watchlist")
        conn.commit()
