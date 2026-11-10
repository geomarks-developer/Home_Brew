"""
TickerTrends Database Layer
===========================

Handles all SQLite database operations for TickerTrends.

Database:
    data/tickertrends.db

Tables:
    tickers
    watchlist
    ticker_state
    state_history
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "tickertrends.db"


# ============================================================
# TIME
# ============================================================

def timestamp() -> str:
    """Return a consistent timestamp for database records."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection() -> sqlite3.Connection:
    """
    Open a connection to the TickerTrends SQLite database.

    sqlite3.Row allows query results to be accessed by
    column name rather than only by numeric index.
    """

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    # Foreign-key enforcement is enabled per connection.
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def initialize_database() -> None:
    """
    Create the TickerTrends database and tables if they
    do not already exist.
    """

    with get_connection() as conn:

        # ----------------------------------------------------
        # TICKERS
        # ----------------------------------------------------

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tickers (
                ticker              TEXT PRIMARY KEY,
                company_name        TEXT,
                sector              TEXT,
                industry            TEXT,

                in_nasdaq100        INTEGER NOT NULL DEFAULT 0,
                in_sp100            INTEGER NOT NULL DEFAULT 0,
                in_aristocrats      INTEGER NOT NULL DEFAULT 0,

                active              INTEGER NOT NULL DEFAULT 1,

                updated_at          TEXT
            )
            """
        )

        # ----------------------------------------------------
        # WATCHLIST
        # ----------------------------------------------------

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS watchlist (
                ticker              TEXT PRIMARY KEY,
                date_added          TEXT NOT NULL,
                notes               TEXT,

                FOREIGN KEY (ticker)
                    REFERENCES tickers(ticker)
                    ON DELETE CASCADE
            )
            """
        )

        # ----------------------------------------------------
        # CURRENT TICKER STATE
        # ----------------------------------------------------

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ticker_state (
                ticker                  TEXT PRIMARY KEY,

                price                   REAL,

                sma_50                  REAL,
                sma_200                 REAL,
                sma_200_slope           REAL,

                pct_from_sma50          REAL,
                pct_from_sma200         REAL,

                rsi_14                  REAL,

                pe_ratio                REAL,
                peg_ratio               REAL,

                free_cash_flow          REAL,
                fcf_metric              REAL,

                relative_performance    REAL,

                technical_score         REAL,
                fundamental_score       REAL,
                total_score             REAL,

                trend_state             TEXT,

                calculated_at           TEXT NOT NULL,

                FOREIGN KEY (ticker)
                    REFERENCES tickers(ticker)
                    ON DELETE CASCADE
            )
            """
        )

        # ----------------------------------------------------
        # STATE HISTORY
        # ----------------------------------------------------

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS state_history (
                id                      INTEGER PRIMARY KEY AUTOINCREMENT,

                ticker                  TEXT NOT NULL,

                old_state               TEXT,
                new_state               TEXT NOT NULL,

                old_score               REAL,
                new_score               REAL,

                changed_at              TEXT NOT NULL,

                acknowledged            INTEGER NOT NULL DEFAULT 0,
                acknowledged_at         TEXT,

                FOREIGN KEY (ticker)
                    REFERENCES tickers(ticker)
                    ON DELETE CASCADE
            )
            """
        )

        # ----------------------------------------------------
        # INDEXES
        # ----------------------------------------------------

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_state_total_score
            ON ticker_state(total_score DESC)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_state_trend
            ON ticker_state(trend_state)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_history_ticker
            ON state_history(ticker)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_history_unacknowledged
            ON state_history(acknowledged, changed_at DESC)
            """
        )


# ============================================================
# TICKERS
# ============================================================

def upsert_ticker(
    ticker: str,
    company_name: Optional[str] = None,
    sector: Optional[str] = None,
    industry: Optional[str] = None,
    in_nasdaq100: bool = False,
    in_sp100: bool = False,
    in_aristocrats: bool = False,
    active: bool = True,
) -> None:
    """
    Insert a ticker or update its existing master record.
    """

    ticker = ticker.upper().strip()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO tickers (
                ticker,
                company_name,
                sector,
                industry,
                in_nasdaq100,
                in_sp100,
                in_aristocrats,
                active,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(ticker) DO UPDATE SET
                company_name = excluded.company_name,
                sector = excluded.sector,
                industry = excluded.industry,
                in_nasdaq100 = excluded.in_nasdaq100,
                in_sp100 = excluded.in_sp100,
                in_aristocrats = excluded.in_aristocrats,
                active = excluded.active,
                updated_at = excluded.updated_at
            """,
            (
                ticker,
                company_name,
                sector,
                industry,
                int(in_nasdaq100),
                int(in_sp100),
                int(in_aristocrats),
                int(active),
                timestamp(),
            ),
        )


def get_ticker(ticker: str) -> Optional[dict[str, Any]]:
    """Return one ticker's master record."""

    ticker = ticker.upper().strip()

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM tickers
            WHERE ticker = ?
            """,
            (ticker,),
        ).fetchone()

    return dict(row) if row else None


def get_all_tickers(
    active_only: bool = True,
) -> list[dict[str, Any]]:
    """Return the TickerTrends universe."""

    with get_connection() as conn:

        if active_only:
            rows = conn.execute(
                """
                SELECT *
                FROM tickers
                WHERE active = 1
                ORDER BY ticker
                """
            ).fetchall()

        else:
            rows = conn.execute(
                """
                SELECT *
                FROM tickers
                ORDER BY ticker
                """
            ).fetchall()

    return [dict(row) for row in rows]


# ============================================================
# WATCHLIST
# ============================================================

def add_to_watchlist(
    ticker: str,
    notes: Optional[str] = None,
) -> None:
    """Add a ticker to the watchlist."""

    ticker = ticker.upper().strip()

    # Make sure a master ticker exists first.
    if get_ticker(ticker) is None:
        upsert_ticker(ticker=ticker)

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO watchlist (
                ticker,
                date_added,
                notes
            )
            VALUES (?, ?, ?)

            ON CONFLICT(ticker) DO UPDATE SET
                notes = COALESCE(excluded.notes, watchlist.notes)
            """,
            (
                ticker,
                timestamp(),
                notes,
            ),
        )


def remove_from_watchlist(ticker: str) -> None:
    """Remove a ticker from the watchlist."""

    ticker = ticker.upper().strip()

    with get_connection() as conn:
        conn.execute(
            """
            DELETE FROM watchlist
            WHERE ticker = ?
            """,
            (ticker,),
        )


def is_in_watchlist(ticker: str) -> bool:
    """Return True if ticker is currently on the watchlist."""

    ticker = ticker.upper().strip()

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM watchlist
            WHERE ticker = ?
            """,
            (ticker,),
        ).fetchone()

    return row is not None


def get_watchlist() -> list[dict[str, Any]]:
    """
    Return watchlist records with current state information.
    """

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                w.ticker,
                w.date_added,
                w.notes,

                t.company_name,
                t.sector,

                s.price,
                s.rsi_14,
                s.sma_50,
                s.sma_200,

                s.technical_score,
                s.fundamental_score,
                s.total_score,

                s.trend_state,
                s.calculated_at

            FROM watchlist w

            LEFT JOIN tickers t
                ON t.ticker = w.ticker

            LEFT JOIN ticker_state s
                ON s.ticker = w.ticker

            ORDER BY
                s.total_score DESC,
                w.ticker ASC
            """
        ).fetchall()

    return [dict(row) for row in rows]


# ============================================================
# CURRENT TICKER STATE
# ============================================================

def get_ticker_state(
    ticker: str,
) -> Optional[dict[str, Any]]:
    """Return the latest calculated state for a ticker."""

    ticker = ticker.upper().strip()

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM ticker_state
            WHERE ticker = ?
            """,
            (ticker,),
        ).fetchone()

    return dict(row) if row else None


def save_ticker_state(
    ticker: str,
    *,
    price: Optional[float] = None,
    sma_50: Optional[float] = None,
    sma_200: Optional[float] = None,
    sma_200_slope: Optional[float] = None,
    pct_from_sma50: Optional[float] = None,
    pct_from_sma200: Optional[float] = None,
    rsi_14: Optional[float] = None,
    pe_ratio: Optional[float] = None,
    peg_ratio: Optional[float] = None,
    free_cash_flow: Optional[float] = None,
    fcf_metric: Optional[float] = None,
    relative_performance: Optional[float] = None,
    technical_score: Optional[float] = None,
    fundamental_score: Optional[float] = None,
    total_score: Optional[float] = None,
    trend_state: Optional[str] = None,
) -> None:
    """
    Save the latest calculated state for a ticker.

    If the trend category changed, a state_history record
    is automatically created.
    """

    ticker = ticker.upper().strip()

    if get_ticker(ticker) is None:
        upsert_ticker(ticker=ticker)

    previous = get_ticker_state(ticker)

    previous_state = (
        previous["trend_state"]
        if previous
        else None
    )

    previous_score = (
        previous["total_score"]
        if previous
        else None
    )

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO ticker_state (
                ticker,
                price,
                sma_50,
                sma_200,
                sma_200_slope,
                pct_from_sma50,
                pct_from_sma200,
                rsi_14,
                pe_ratio,
                peg_ratio,
                free_cash_flow,
                fcf_metric,
                relative_performance,
                technical_score,
                fundamental_score,
                total_score,
                trend_state,
                calculated_at
            )

            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?
        )

            ON CONFLICT(ticker) DO UPDATE SET
                price = excluded.price,
                sma_50 = excluded.sma_50,
                sma_200 = excluded.sma_200,
                sma_200_slope = excluded.sma_200_slope,
                pct_from_sma50 = excluded.pct_from_sma50,
                pct_from_sma200 = excluded.pct_from_sma200,
                rsi_14 = excluded.rsi_14,
                pe_ratio = excluded.pe_ratio,
                peg_ratio = excluded.peg_ratio,
                free_cash_flow = excluded.free_cash_flow,
                fcf_metric = excluded.fcf_metric,
                relative_performance =
                    excluded.relative_performance,
                technical_score =
                    excluded.technical_score,
                fundamental_score =
                    excluded.fundamental_score,
                total_score =
                    excluded.total_score,
                trend_state =
                    excluded.trend_state,
                calculated_at =
                    excluded.calculated_at
            """,
            (
                ticker,
                price,
                sma_50,
                sma_200,
                sma_200_slope,
                pct_from_sma50,
                pct_from_sma200,
                rsi_14,
                pe_ratio,
                peg_ratio,
                free_cash_flow,
                fcf_metric,
                relative_performance,
                technical_score,
                fundamental_score,
                total_score,
                trend_state,
                timestamp(),
            ),
        )

    # Record only actual category changes.
    # Initial population is not considered a state change.
    if (
        previous_state is not None
        and trend_state is not None
        and previous_state != trend_state
    ):
        record_state_change(
            ticker=ticker,
            old_state=previous_state,
            new_state=trend_state,
            old_score=previous_score,
            new_score=total_score,
        )


def get_all_ticker_states() -> list[dict[str, Any]]:
    """
    Return all calculated ticker states ranked by score.
    """

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                s.*,
                t.company_name,
                t.sector,
                t.industry,
                t.in_nasdaq100,
                t.in_sp100,
                t.in_aristocrats

            FROM ticker_state s

            LEFT JOIN tickers t
                ON t.ticker = s.ticker

            ORDER BY
                s.total_score DESC,
                s.ticker ASC
            """
        ).fetchall()

    return [dict(row) for row in rows]


# ============================================================
# STATE HISTORY
# ============================================================

def record_state_change(
    ticker: str,
    old_state: Optional[str],
    new_state: str,
    old_score: Optional[float] = None,
    new_score: Optional[float] = None,
) -> int:
    """
    Record a ticker moving from one trend category to another.

    Returns the new history record ID.
    """

    ticker = ticker.upper().strip()

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO state_history (
                ticker,
                old_state,
                new_state,
                old_score,
                new_score,
                changed_at,
                acknowledged
            )
            VALUES (?, ?, ?, ?, ?, ?, 0)
            """,
            (
                ticker,
                old_state,
                new_state,
                old_score,
                new_score,
                timestamp(),
            ),
        )

        return int(cursor.lastrowid)


def get_state_history(
    ticker: Optional[str] = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return state-change history."""

    with get_connection() as conn:

        if ticker:

            ticker = ticker.upper().strip()

            rows = conn.execute(
                """
                SELECT *
                FROM state_history
                WHERE ticker = ?
                ORDER BY changed_at DESC
                LIMIT ?
                """,
                (
                    ticker,
                    limit,
                ),
            ).fetchall()

        else:

            rows = conn.execute(
                """
                SELECT *
                FROM state_history
                ORDER BY changed_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    return [dict(row) for row in rows]


def get_unacknowledged_changes(
    watchlist_only: bool = True,
) -> list[dict[str, Any]]:
    """
    Return state changes the user has not yet acknowledged.

    By default, only changes for watchlist stocks are returned.
    """

    with get_connection() as conn:

        if watchlist_only:

            rows = conn.execute(
                """
                SELECT
                    h.*,
                    t.company_name,
                    s.total_score,
                    s.trend_state

                FROM state_history h

                INNER JOIN watchlist w
                    ON w.ticker = h.ticker

                LEFT JOIN tickers t
                    ON t.ticker = h.ticker

                LEFT JOIN ticker_state s
                    ON s.ticker = h.ticker

                WHERE h.acknowledged = 0

                ORDER BY h.changed_at DESC
                """
            ).fetchall()

        else:

            rows = conn.execute(
                """
                SELECT *
                FROM state_history
                WHERE acknowledged = 0
                ORDER BY changed_at DESC
                """
            ).fetchall()

    return [dict(row) for row in rows]


def acknowledge_change(change_id: int) -> None:
    """Mark one state-change alert as acknowledged."""

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE state_history

            SET
                acknowledged = 1,
                acknowledged_at = ?

            WHERE id = ?
            """,
            (
                timestamp(),
                change_id,
            ),
        )


def acknowledge_all_changes(
    ticker: Optional[str] = None,
) -> None:
    """
    Acknowledge all alerts.

    If ticker is provided, only alerts for that ticker
    are acknowledged.
    """

    with get_connection() as conn:

        if ticker:

            ticker = ticker.upper().strip()

            conn.execute(
                """
                UPDATE state_history

                SET
                    acknowledged = 1,
                    acknowledged_at = ?

                WHERE
                    ticker = ?
                    AND acknowledged = 0
                """,
                (
                    timestamp(),
                    ticker,
                ),
            )

        else:

            conn.execute(
                """
                UPDATE state_history

                SET
                    acknowledged = 1,
                    acknowledged_at = ?

                WHERE acknowledged = 0
                """,
                (timestamp(),),
            )

def ensure_scan_runs_table() -> None:
    """
    Create the scan_runs table and index when missing.

    Safe to call repeatedly.
    """

    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scan_runs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_type       TEXT NOT NULL DEFAULT 'full',
                started_at      TEXT NOT NULL,
                completed_at    TEXT,
                requested       INTEGER NOT NULL DEFAULT 0,
                successful      INTEGER NOT NULL DEFAULT 0,
                failed          INTEGER NOT NULL DEFAULT 0,
                state_changes   INTEGER NOT NULL DEFAULT 0,
                status          TEXT NOT NULL DEFAULT 'running'
            )
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_scan_runs_completed
            ON scan_runs(completed_at DESC)
            """
        )


# ============================================================
# SCAN FRESHNESS
# ============================================================

def start_scan_run(
    requested: int,
    scan_type: str = "full",
) -> int:
    """
    Record the beginning of a scanner run.

    Returns the new scan ID.
    """
    ensure_scan_runs_table()

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO scan_runs (
                scan_type,
                started_at,
                requested,
                status
            )
            VALUES (?, ?, ?, 'running')
            """,
            (
                scan_type,
                timestamp(),
                requested,
            ),
        )

        return int(cursor.lastrowid)


def complete_scan_run(
    scan_id: int,
    successful: int,
    failed: int,
    state_changes: int,
) -> None:
    """
    Mark a scanner run successfully completed.
    """

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE scan_runs
            SET
                completed_at = ?,
                successful = ?,
                failed = ?,
                state_changes = ?,
                status = 'completed'
            WHERE id = ?
            """,
            (
                timestamp(),
                successful,
                failed,
                state_changes,
                scan_id,
            ),
        )


def fail_scan_run(
    scan_id: int,
    successful: int = 0,
    failed: int = 0,
    state_changes: int = 0,
) -> None:
    """
    Mark a scanner run as interrupted or failed.
    """

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE scan_runs
            SET
                completed_at = ?,
                successful = ?,
                failed = ?,
                state_changes = ?,
                status = 'failed'
            WHERE id = ?
            """,
            (
                timestamp(),
                successful,
                failed,
                state_changes,
                scan_id,
            ),
        )


def get_last_completed_scan(
    scan_type: str = "full",
) -> dict[str, Any] | None:
    """
    Return the latest successfully completed scan.
    """
    ensure_scan_runs_table()

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM scan_runs
            WHERE
                scan_type = ?
                AND status = 'completed'
            ORDER BY completed_at DESC
            LIMIT 1
            """,
            (scan_type,),
        ).fetchone()

    return dict(row) if row else None


def get_scan_history(
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Return recent scanner runs.
    """
    ensure_scan_runs_table()

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM scan_runs
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


def get_latest_data_timestamp() -> str | None:
    """
    Return the most recent ticker-state calculation time.
    """

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT MAX(calculated_at) AS latest
            FROM ticker_state
            """
        ).fetchone()

    if row is None:
        return None

    return row["latest"]


def get_oldest_data_timestamp() -> str | None:
    """
    Return the oldest current ticker-state calculation time.

    This is useful for detecting a partially refreshed universe.
    """

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT MIN(calculated_at) AS oldest
            FROM ticker_state
            """
        ).fetchone()

    if row is None:
        return None

    return row["oldest"]

# ============================================================
# DATABASE INFORMATION / TESTING
# ============================================================

def database_exists() -> bool:
    """Return True if the SQLite database file exists."""
    return DB_PATH.exists()


def get_database_path() -> str:
    """Return the full database path."""
    return str(DB_PATH)


def get_table_names() -> list[str]:
    """Return application table names in the database."""

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE
                type = 'table'
                AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()

    return [row["name"] for row in rows]

        # ----------------------------------------------------
        # SCAN RUNS
        # ----------------------------------------------------

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS scan_runs (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,

            scan_type           TEXT NOT NULL DEFAULT 'full',

            started_at          TEXT NOT NULL,
            completed_at        TEXT,

            requested           INTEGER NOT NULL DEFAULT 0,
            successful          INTEGER NOT NULL DEFAULT 0,
            failed              INTEGER NOT NULL DEFAULT 0,
            state_changes       INTEGER NOT NULL DEFAULT 0,

            status              TEXT NOT NULL DEFAULT 'running'
        )
        """
        )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_scan_runs_completed
        ON scan_runs(completed_at DESC)
        """
    )


# ============================================================
# INITIALIZE WHEN RUN DIRECTLY
# ============================================================

if __name__ == "__main__":

    initialize_database()

    print("TickerTrends database initialized.")
    print(f"Database: {get_database_path()}")
    print(f"Tables: {', '.join(get_table_names())}")