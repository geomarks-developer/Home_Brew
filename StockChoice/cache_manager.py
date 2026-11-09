"""
StockChoice Cache Manager

SQLite cache layer for:

    - Fundamentals
    - Historical Prices
    - Strategy Scores

Future:

    - Watchlists
    - Portfolios
    - Saved Screens
"""

from __future__ import annotations

import json
import sqlite3

from datetime import datetime
from pathlib import Path

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

ROOT_DIR = Path(__file__).resolve().parent

DB_FILE = ROOT_DIR / "stockchoice.db"

FUNDAMENTAL_TTL_DAYS = 30

HISTORY_TTL_DAYS = 1

SCORE_TTL_DAYS = 1


# ============================================================
# CONNECTION
# ============================================================

def get_connection():

    return sqlite3.connect(
        DB_FILE
    )


# ============================================================
# DATE HELPERS
# ============================================================

def now_string():

    return datetime.utcnow().isoformat()


def age_in_days(
    timestamp: str
):

    updated = datetime.fromisoformat(
        timestamp
    )

    age = (
        datetime.utcnow()
        - updated
    )

    return (
        age.total_seconds()
        / 86400
    )


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def initialize_cache():

    conn = get_connection()

    #
    # Fundamentals
    #
    conn.execute("""
        CREATE TABLE IF NOT EXISTS
        stock_fundamentals (

            ticker TEXT PRIMARY KEY,

            data TEXT NOT NULL,

            updated_at TEXT NOT NULL
        )
    """)

    #
    # Price History
    #
    conn.execute("""
        CREATE TABLE IF NOT EXISTS
        stock_history (

            ticker TEXT PRIMARY KEY,

            data TEXT NOT NULL,

            updated_at TEXT NOT NULL
        )
    """)

    #
    # Scores
    #
    conn.execute("""
        CREATE TABLE IF NOT EXISTS
        stock_scores (

            ticker TEXT NOT NULL,

            strategy TEXT NOT NULL,

            score_data TEXT NOT NULL,

            updated_at TEXT NOT NULL,

            PRIMARY KEY (
                ticker,
                strategy
            )

        )
    """)

    conn.commit()

    conn.close()


# ============================================================
# FUNDAMENTALS
# ============================================================

def get_cached_fundamentals(
    ticker: str
) -> dict | None:

    conn = get_connection()

    cur = conn.cursor()

    cur.execute(
        """
        SELECT data, updated_at

        FROM stock_fundamentals

        WHERE ticker = ?
        """,
        (
            ticker.upper(),
        )
    )

    row = cur.fetchone()

    conn.close()

    if row is None:
        return None

    data, updated_at = row

    if (
        age_in_days(updated_at)
        > FUNDAMENTAL_TTL_DAYS
    ):
        return None

    return json.loads(data)


def save_fundamentals(
    ticker: str,
    data: dict,
):

    conn = get_connection()

    conn.execute(
        """
        INSERT OR REPLACE INTO
        stock_fundamentals (

            ticker,
            data,
            updated_at

        )

        VALUES (?, ?, ?)
        """,
        (
            ticker.upper(),

            json.dumps(
                data,
                default=str
            ),

            now_string(),
        )
    )

    conn.commit()

    conn.close()


# ============================================================
# HISTORY
# ============================================================

def get_cached_history(
    ticker: str
):

    conn = get_connection()

    cur = conn.cursor()

    cur.execute(
        """
        SELECT data, updated_at

        FROM stock_history

        WHERE ticker = ?
        """,
        (
            ticker.upper(),
        )
    )

    row = cur.fetchone()

    conn.close()

    if row is None:
        return None

    data, updated_at = row

    if (
        age_in_days(updated_at)
        > HISTORY_TTL_DAYS
    ):
        return None

    try:

        return pd.read_json(
            data,
            orient="split"
        )

    except Exception:

        return None


def save_history(
    ticker: str,
    history_df: pd.DataFrame,
):

    conn = get_connection()

    conn.execute(
        """
        INSERT OR REPLACE INTO
        stock_history (

            ticker,
            data,
            updated_at

        )

        VALUES (?, ?, ?)
        """,
        (
            ticker.upper(),

            history_df.to_json(
                orient="split",
                date_format="iso"
            ),

            now_string(),
        )
    )

    conn.commit()

    conn.close()


# ============================================================
# SCORES
# ============================================================

def get_cached_score(
    ticker: str,
    strategy: str,
):

    conn = get_connection()

    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            score_data,
            updated_at

        FROM stock_scores

        WHERE ticker = ?
          AND strategy = ?
        """,
        (
            ticker.upper(),
            strategy.lower(),
        )
    )

    row = cur.fetchone()

    conn.close()

    if row is None:
        return None

    data, updated_at = row

    if (
        age_in_days(updated_at)
        > SCORE_TTL_DAYS
    ):
        return None

    return json.loads(data)


def save_score(
    ticker: str,
    strategy: str,
    stock_score,
    details: dict,
):

    payload = {

        "ticker":
            stock_score.ticker,

        "strategy":
            stock_score.strategy,

        "strategy_score":
            stock_score.strategy_score,

        "rating":
            stock_score.rating,

        "trend_status":
            stock_score.trend_status,

        "factor_scores": {

            "growth":
                stock_score.factor_scores.growth,

            "quality":
                stock_score.factor_scores.quality,

            "value":
                stock_score.factor_scores.value,

            "dividend":
                stock_score.factor_scores.dividend,

            "momentum":
                stock_score.factor_scores.momentum,

            "risk":
                stock_score.factor_scores.risk,
        },

        "details":
            details,
    }

    conn = get_connection()

    conn.execute(
        """
        INSERT OR REPLACE INTO
        stock_scores (

            ticker,
            strategy,
            score_data,
            updated_at

        )

        VALUES (?, ?, ?, ?)
        """,
        (
            ticker.upper(),

            strategy.lower(),

            json.dumps(
                payload,
                default=str
            ),

            now_string(),
        )
    )

    conn.commit()

    conn.close()


# ============================================================
# CACHE MAINTENANCE
# ============================================================

def clear_fundamentals():

    conn = get_connection()

    conn.execute(
        "DELETE FROM stock_fundamentals"
    )

    conn.commit()

    conn.close()


def clear_history():

    conn = get_connection()

    conn.execute(
        "DELETE FROM stock_history"
    )

    conn.commit()

    conn.close()


def clear_scores():

    conn = get_connection()

    conn.execute(
        "DELETE FROM stock_scores"
    )

    conn.commit()

    conn.close()


def clear_all_cache():

    conn = get_connection()

    conn.execute(
        "DELETE FROM stock_fundamentals"
    )

    conn.execute(
        "DELETE FROM stock_history"
    )

    conn.execute(
        "DELETE FROM stock_scores"
    )

    conn.commit()

    conn.close()


# ============================================================
# CACHE STATS
# ============================================================

def cache_stats():

    conn = get_connection()

    cur = conn.cursor()

    cur.execute(
        """
        SELECT COUNT(*)
        FROM stock_fundamentals
        """
    )

    fundamentals = (
        cur.fetchone()[0]
    )

    cur.execute(
        """
        SELECT COUNT(*)
        FROM stock_history
        """
    )

    history = (
        cur.fetchone()[0]
    )

    cur.execute(
        """
        SELECT COUNT(*)
        FROM stock_scores
        """
    )

    scores = (
        cur.fetchone()[0]
    )

    conn.close()

    return {

        "fundamentals":
            fundamentals,

        "history":
            history,

        "scores":
            scores,
    }


# ============================================================
# INITIALIZE
# ============================================================

initialize_cache()


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print()

    print(
        "Database:"
    )

    print(DB_FILE)

    print()

    print(
        cache_stats()
    )

    print()