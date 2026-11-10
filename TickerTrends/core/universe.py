"""
TickerTrends Universe Manager
=============================

Builds the TickerTrends stock universe from:

    - NASDAQ-100
    - S&P 100
    - Dividend Aristocrats

The three source lists are stored in:

    data/nasdaq100.csv
    data/sp100.csv
    data/aristocrats.csv

Membership is merged and written to the SQLite
tickers table defined in core.database.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from core.database import (
    get_all_tickers,
    get_connection,
    initialize_database,
    timestamp,
    upsert_ticker,
)


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

NASDAQ100_FILE = DATA_DIR / "nasdaq100.csv"
SP100_FILE = DATA_DIR / "sp100.csv"
ARISTOCRATS_FILE = DATA_DIR / "aristocrats.csv"


# ============================================================
# DATA MODEL
# ============================================================

@dataclass
class UniverseMember:
    """
    Represents one security in the combined TickerTrends
    universe.
    """

    ticker: str
    company_name: str | None = None

    in_nasdaq100: bool = False
    in_sp100: bool = False
    in_aristocrats: bool = False


# ============================================================
# SYMBOL NORMALIZATION
# ============================================================

def normalize_ticker(ticker: str) -> str:
    """
    Normalize a ticker symbol for use throughout TickerTrends.

    Examples:
        msft  -> MSFT
        brk.b -> BRK-B
        bf.b  -> BF-B
    """

    ticker = ticker.strip().upper()

    # yfinance generally expects hyphen-form ticker symbols
    # for class shares such as BRK-B and BF-B.
    ticker = ticker.replace(".", "-")

    return ticker


# ============================================================
# CSV CREATION
# ============================================================

def create_csv_if_missing(path: Path) -> None:
    """
    Create an empty universe CSV with standard column headers.

    Existing files are never overwritten.
    """

    if path.exists():
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.writer(file)

        writer.writerow(
            [
                "ticker",
                "company_name",
            ]
        )


def create_universe_files() -> None:
    """
    Ensure that all three universe source files exist.
    """

    create_csv_if_missing(NASDAQ100_FILE)
    create_csv_if_missing(SP100_FILE)
    create_csv_if_missing(ARISTOCRATS_FILE)


# ============================================================
# CSV READER
# ============================================================

def read_universe_csv(
    path: Path,
) -> list[tuple[str, str | None]]:
    """
    Read one universe CSV.

    Expected columns:

        ticker
        company_name

    company_name is optional.
    """

    if not path.exists():
        return []

    members: list[tuple[str, str | None]] = []

    with path.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            return []

        # Normalize CSV header names.
        field_map = {
            field.strip().lower(): field
            for field in reader.fieldnames
            if field
        }

        if "ticker" not in field_map:
            raise ValueError(
                f"{path.name} must contain a 'ticker' column."
            )

        ticker_column = field_map["ticker"]
        company_column = field_map.get("company_name")

        for row in reader:
            raw_ticker = row.get(ticker_column)

            if raw_ticker is None:
                continue

            ticker = normalize_ticker(raw_ticker)

            if not ticker:
                continue

            company_name: str | None = None

            if company_column:
                raw_company = row.get(company_column)

                if raw_company:
                    cleaned_company = raw_company.strip()

                    if cleaned_company:
                        company_name = cleaned_company

            members.append(
                (
                    ticker,
                    company_name,
                )
            )

    return members


# ============================================================
# UNIVERSE BUILD
# ============================================================

def merge_universe(
    members: dict[str, UniverseMember],
    source_members: Iterable[tuple[str, str | None]],
    *,
    nasdaq100: bool = False,
    sp100: bool = False,
    aristocrats: bool = False,
) -> None:
    """
    Merge one source list into the combined universe.
    """

    for ticker, company_name in source_members:

        if ticker not in members:
            members[ticker] = UniverseMember(
                ticker=ticker,
                company_name=company_name,
            )

        member = members[ticker]

        # Preserve an existing company name unless one is missing.
        if (
            member.company_name is None
            and company_name is not None
        ):
            member.company_name = company_name

        if nasdaq100:
            member.in_nasdaq100 = True

        if sp100:
            member.in_sp100 = True

        if aristocrats:
            member.in_aristocrats = True


def build_universe() -> dict[str, UniverseMember]:
    """
    Read all three source lists and return one deduplicated
    universe keyed by ticker.
    """

    create_universe_files()

    members: dict[str, UniverseMember] = {}

    # NASDAQ-100
    merge_universe(
        members,
        read_universe_csv(NASDAQ100_FILE),
        nasdaq100=True,
    )

    # S&P 100
    merge_universe(
        members,
        read_universe_csv(SP100_FILE),
        sp100=True,
    )

    # Dividend Aristocrats
    merge_universe(
        members,
        read_universe_csv(ARISTOCRATS_FILE),
        aristocrats=True,
    )

    return members


# ============================================================
# SQLITE SYNCHRONIZATION
# ============================================================

def mark_all_tickers_inactive() -> None:
    """
    Mark existing universe securities inactive before loading
    the latest source lists.

    Securities found during synchronization are immediately
    reactivated.

    This preserves historical records if a security is later
    removed from one of the source universes.
    """

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE tickers
            SET
                active = 0,
                in_nasdaq100 = 0,
                in_sp100 = 0,
                in_aristocrats = 0,
                updated_at = ?
            """,
            (timestamp(),),
        )


def sync_universe() -> dict[str, int]:
    """
    Synchronize the CSV universe files with SQLite.

    Returns statistics describing the resulting universe.
    """

    initialize_database()

    universe = build_universe()

    mark_all_tickers_inactive()

    for member in universe.values():
        upsert_ticker(
            ticker=member.ticker,
            company_name=member.company_name,
            in_nasdaq100=member.in_nasdaq100,
            in_sp100=member.in_sp100,
            in_aristocrats=member.in_aristocrats,
            active=True,
        )

    return get_universe_stats()


# ============================================================
# QUERY HELPERS
# ============================================================

def get_universe() -> list[dict[str, Any]]:
    """
    Return the active combined TickerTrends universe.
    """

    return get_all_tickers(active_only=True)


def get_universe_tickers() -> list[str]:
    """
    Return only the active ticker symbols.
    """

    return [
        row["ticker"]
        for row in get_universe()
    ]


def get_nasdaq100() -> list[dict[str, Any]]:
    """
    Return active NASDAQ-100 members.
    """

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM tickers
            WHERE
                active = 1
                AND in_nasdaq100 = 1
            ORDER BY ticker
            """
        ).fetchall()

    return [dict(row) for row in rows]


def get_sp100() -> list[dict[str, Any]]:
    """
    Return active S&P 100 members.
    """

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM tickers
            WHERE
                active = 1
                AND in_sp100 = 1
            ORDER BY ticker
            """
        ).fetchall()

    return [dict(row) for row in rows]


def get_aristocrats() -> list[dict[str, Any]]:
    """
    Return active Dividend Aristocrat members.
    """

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM tickers
            WHERE
                active = 1
                AND in_aristocrats = 1
            ORDER BY ticker
            """
        ).fetchall()

    return [dict(row) for row in rows]


# ============================================================
# MEMBERSHIP
# ============================================================

def get_memberships(
    ticker: str,
) -> list[str]:
    """
    Return the universe memberships for a ticker.

    Example:

        MSFT -> ["NASDAQ-100", "S&P 100"]
    """

    ticker = normalize_ticker(ticker)

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                in_nasdaq100,
                in_sp100,
                in_aristocrats
            FROM tickers
            WHERE ticker = ?
            """,
            (ticker,),
        ).fetchone()

    if row is None:
        return []

    memberships: list[str] = []

    if row["in_nasdaq100"]:
        memberships.append("NASDAQ-100")

    if row["in_sp100"]:
        memberships.append("S&P 100")

    if row["in_aristocrats"]:
        memberships.append("Dividend Aristocrat")

    return memberships


# ============================================================
# STATISTICS
# ============================================================

def get_universe_stats() -> dict[str, int]:
    """
    Return counts for each universe and the combined set.
    """

    with get_connection() as conn:
        total = conn.execute(
            """
            SELECT COUNT(*)
            FROM tickers
            WHERE active = 1
            """
        ).fetchone()[0]

        nasdaq100 = conn.execute(
            """
            SELECT COUNT(*)
            FROM tickers
            WHERE
                active = 1
                AND in_nasdaq100 = 1
            """
        ).fetchone()[0]

        sp100 = conn.execute(
            """
            SELECT COUNT(*)
            FROM tickers
            WHERE
                active = 1
                AND in_sp100 = 1
            """
        ).fetchone()[0]

        aristocrats = conn.execute(
            """
            SELECT COUNT(*)
            FROM tickers
            WHERE
                active = 1
                AND in_aristocrats = 1
            """
        ).fetchone()[0]

    return {
        "total": total,
        "nasdaq100": nasdaq100,
        "sp100": sp100,
        "aristocrats": aristocrats,
    }


# ============================================================
# VALIDATION
# ============================================================

def validate_universe() -> list[str]:
    """
    Look for obvious universe problems.

    Returns human-readable warning strings.
    """

    warnings: list[str] = []

    universe = get_universe()

    if not universe:
        warnings.append(
            "TickerTrends universe is empty."
        )

        return warnings

    for member in universe:
        ticker = member["ticker"]

        if " " in ticker:
            warnings.append(
                f"{ticker}: ticker contains whitespace."
            )

        if not (
            member["in_nasdaq100"]
            or member["in_sp100"]
            or member["in_aristocrats"]
        ):
            warnings.append(
                f"{ticker}: has no universe membership."
            )

    return warnings


# ============================================================
# COMMAND-LINE SUMMARY
# ============================================================

def print_summary() -> None:
    """
    Print a quick universe summary.
    """

    stats = get_universe_stats()

    print()
    print("TickerTrends Universe")
    print("=====================")
    print(f"NASDAQ-100:           {stats['nasdaq100']}")
    print(f"S&P 100:              {stats['sp100']}")
    print(f"Dividend Aristocrats: {stats['aristocrats']}")
    print("----------------------")
    print(f"Unique securities:    {stats['total']}")
    print()

    warnings = validate_universe()

    if warnings:
        print("Warnings:")

        for warning in warnings:
            print(f"  - {warning}")

    else:
        print("Universe validation passed.")


# ============================================================
# RUN DIRECTLY
# ============================================================

if __name__ == "__main__":
    sync_universe()
    print_summary()