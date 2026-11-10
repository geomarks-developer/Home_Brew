"""
TickerTrends Universe Scanner
=============================

Runs the complete TickerTrends model across the active
stock universe.

Processing pipeline:

    Universe
        -> Technicals
        -> Trend State
        -> Fundamentals
        -> 100-Point Score
        -> SQLite

Each successful ticker is saved immediately.

This provides:

    - Restart-safe processing
    - Per-ticker error handling
    - Trend-state history tracking
    - Watchlist category-change alerts
    - Scanner summary statistics

Run from the TickerTrends project root:

    python -m core.scanner

Optional examples:

    python -m core.scanner --limit 10
    python -m core.scanner --ticker MSFT
    python -m core.scanner --tickers MSFT AAPL NVDA
    python -m core.scanner --delay 1.0
"""

from __future__ import annotations

import argparse
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from core.database import (
    complete_scan_run,
    fail_scan_run,
    get_all_ticker_states,
    get_database_path,
    get_ticker_state,
    initialize_database,
    save_ticker_state,
    start_scan_run,
)

from core.fundamentals import get_fundamentals
from core.scoring import (
    ScoreSummary,
    calculate_score,
)
from core.technicals import get_technicals
from core.universe import (
    get_universe,
    normalize_ticker,
    sync_universe,
)
import numpy as np

# ============================================================
# DEFAULT SETTINGS
# ============================================================

DEFAULT_DELAY_SECONDS = 0.50
DEFAULT_RETRY_DELAY_SECONDS = 3.0
DEFAULT_RETRIES = 1


# ============================================================
# SCAN RESULT MODELS
# ============================================================

@dataclass
class TickerScanResult:
    """
    Result for one scanned ticker.
    """

    ticker: str
    success: bool

    trend_state: str | None = None
    technical_score: float | None = None
    fundamental_score: float | None = None
    total_score: float | None = None

    previous_state: str | None = None
    state_changed: bool = False

    elapsed_seconds: float = 0.0
    error: str | None = None


@dataclass
class UniverseScanResult:
    """
    Complete result for one universe scan.
    """

    started_at: datetime
    finished_at: datetime | None = None

    requested: int = 0
    successful: int = 0
    failed: int = 0
    state_changes: int = 0

    ticker_results: list[TickerScanResult] = field(
        default_factory=list
    )

    @property
    def elapsed_seconds(self) -> float:
        """
        Return total scan duration.
        """

        ending = (
            self.finished_at
            if self.finished_at is not None
            else datetime.now()
        )

        return (
            ending - self.started_at
        ).total_seconds()

    @property
    def trend_counts(self) -> Counter:
        """
        Count successful results by trend state.
        """

        return Counter(
            result.trend_state
            for result in self.ticker_results
            if (
                result.success
                and result.trend_state is not None
            )
        )


# ============================================================
# DISPLAY HELPERS
# ============================================================

def format_score(
    value: float | None,
) -> str:
    """
    Format a score for console output.
    """

    if value is None:
        return "N/A"

    return f"{value:.1f}"


def format_duration(
    seconds: float,
) -> str:
    """
    Format elapsed time.
    """

    seconds = max(
        0,
        int(round(seconds)),
    )

    minutes, remaining_seconds = divmod(
        seconds,
        60,
    )

    hours, minutes = divmod(
        minutes,
        60,
    )

    if hours:
        return (
            f"{hours}h "
            f"{minutes}m "
            f"{remaining_seconds}s"
        )

    if minutes:
        return (
            f"{minutes}m "
            f"{remaining_seconds}s"
        )

    return f"{remaining_seconds}s"


# ============================================================
# DATABASE SAVE
# ============================================================

def save_scan_result(
    ticker: str,
    technicals: dict[str, Any],
    fundamentals: dict[str, Any],
    score: ScoreSummary,
) -> None:
    """
    Save one completed ticker result to SQLite.

    save_ticker_state() automatically inserts a state_history
    record when the trend category changes.
    """

    company_name = fundamentals.get(
        "company_name"
    )

    sector = fundamentals.get(
        "sector"
    )

    industry = fundamentals.get(
        "industry"
    )

    # Preserve existing universe membership flags by omitting
    # membership updates here. The tickers table is updated
    # directly for descriptive company fields.
    upsert_company_details(
        ticker=ticker,
        company_name=company_name,
        sector=sector,
        industry=industry,
    )

    save_ticker_state(
        ticker=ticker,

        price=technicals.get(
            "price"
        ),

        sma_50=technicals.get(
            "sma_50"
        ),

        sma_200=technicals.get(
            "sma_200"
        ),

        sma_200_slope=technicals.get(
            "sma_200_slope"
        ),

        pct_from_sma50=technicals.get(
            "pct_from_sma50"
        ),

        pct_from_sma200=technicals.get(
            "pct_from_sma200"
        ),

        rsi_14=technicals.get(
            "rsi_14"
        ),

        pe_ratio=fundamentals.get(
            "pe_ratio"
        ),

        peg_ratio=fundamentals.get(
            "peg_ratio"
        ),

        free_cash_flow=fundamentals.get(
            "free_cash_flow"
        ),

        # The database uses fcf_metric as the general
        # comparable cash-flow measure. For TickerTrends,
        # that measure is FCF margin.
        fcf_metric=fundamentals.get(
            "fcf_margin"
        ),

        relative_performance=fundamentals.get(
            "relative_performance"
        ),

        technical_score=score.technical_score,

        fundamental_score=score.fundamental_score,

        total_score=score.total_score,

        trend_state=score.trend_state,
    )


def upsert_company_details(
    ticker: str,
    company_name: str | None,
    sector: str | None,
    industry: str | None,
) -> None:
    """
    Update company details without overwriting the ticker's
    universe membership flags.

    Using upsert_ticker() directly here would reset membership
    flags because its default membership arguments are False.
    """

    from core.database import (
        get_connection,
        timestamp,
    )

    ticker = normalize_ticker(
        ticker
    )

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE tickers

            SET
                company_name = COALESCE(?, company_name),
                sector = COALESCE(?, sector),
                industry = COALESCE(?, industry),
                updated_at = ?

            WHERE ticker = ?
            """,
            (
                company_name,
                sector,
                industry,
                timestamp(),
                ticker,
            ),
        )


# ============================================================
# SINGLE-TICKER SCAN
# ============================================================

def scan_ticker(
    ticker: str,
) -> TickerScanResult:
    """
    Run the complete TickerTrends model for one ticker.
    """

    started = time.perf_counter()

    ticker = normalize_ticker(
        ticker
    )

    previous = get_ticker_state(
        ticker
    )

    previous_state = (
        previous.get("trend_state")
        if previous
        else None
    )

    try:
        # ----------------------------------------------------
        # TECHNICALS
        # ----------------------------------------------------

        technicals = get_technicals(
            ticker
        )

        if technicals is None:
            raise RuntimeError(
                "Technical data was unavailable."
            )

        # ----------------------------------------------------
        # FUNDAMENTALS
        # ----------------------------------------------------

        fundamentals = get_fundamentals(
            ticker
        )

        # ----------------------------------------------------
        # SCORE + TREND STATE
        # ----------------------------------------------------

        score = calculate_score(
            ticker=ticker,
            technicals=technicals,
            fundamentals=fundamentals,
        )

        if score.trend_state is None:
            raise RuntimeError(
                "Trend state could not be determined."
            )

        # ----------------------------------------------------
        # SAVE
        # ----------------------------------------------------

        save_scan_result(
            ticker=ticker,
            technicals=technicals,
            fundamentals=fundamentals,
            score=score,
        )

        changed = (
            previous_state is not None
            and previous_state
            != score.trend_state
        )

        elapsed = (
            time.perf_counter()
            - started
        )

        return TickerScanResult(
            ticker=ticker,
            success=True,
            trend_state=score.trend_state,
            technical_score=score.technical_score,
            fundamental_score=score.fundamental_score,
            total_score=score.total_score,
            previous_state=previous_state,
            state_changed=changed,
            elapsed_seconds=elapsed,
        )

    except Exception as exc:
        elapsed = (
            time.perf_counter()
            - started
        )

        return TickerScanResult(
            ticker=ticker,
            success=False,
            previous_state=previous_state,
            elapsed_seconds=elapsed,
            error=f"{type(exc).__name__}: {exc}",
        )


def scan_ticker_with_retry(
    ticker: str,
    retries: int = DEFAULT_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY_SECONDS,
) -> TickerScanResult:
    """
    Scan one ticker and retry transient failures.
    """

    attempts = retries + 1
    last_result: TickerScanResult | None = None

    for attempt in range(
        1,
        attempts + 1,
    ):
        result = scan_ticker(
            ticker
        )

        if result.success:
            return result

        last_result = result

        if attempt < attempts:
            print(
                f"    Retrying {ticker} after "
                f"{retry_delay:.1f}s..."
            )

            time.sleep(
                retry_delay
            )

    if last_result is None:
        return TickerScanResult(
            ticker=ticker,
            success=False,
            error="Unknown scanner error.",
        )

    return last_result


# ============================================================
# TICKER SELECTION
# ============================================================

def get_scan_tickers(
    requested_tickers: list[str] | None = None,
    limit: int | None = None,
) -> list:
    """
    Return the tickers that should be scanned.

    If requested_tickers is provided, only those symbols are
    scanned. Otherwise the complete active universe is used.
    """

    if requested_tickers:
        tickers = sorted(
            {
                normalize_ticker(ticker)
                for ticker in requested_tickers
                if ticker.strip()
            }
        )

    else:
        universe = get_universe()

        tickers = [
            row["ticker"]
            for row in universe
        ]

    if (
        limit is not None
        and limit > 0
    ):
        tickers = tickers[:limit]

    return tickers


# ============================================================
# UNIVERSE SCAN
# ============================================================

def scan_universe(
    requested_tickers: list[str] | None = None,
    limit: int | None = None,
    delay: float = DEFAULT_DELAY_SECONDS,
    retries: int = DEFAULT_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY_SECONDS,
    sync_before_scan: bool = True,
) -> UniverseScanResult:
    """
    Run TickerTrends across the selected universe.

    Results are saved after every successful ticker.
    """

    initialize_database()

    if sync_before_scan:
        print(
            "Synchronizing the TickerTrends universe..."
        )

        sync_universe()

    tickers = get_scan_tickers(
        requested_tickers=requested_tickers,
        limit=limit,
    )

    scan_result = UniverseScanResult(
        started_at=datetime.now(),
        requested=len(tickers),
    )

    scan_type = (
        "full"
        if requested_tickers is None
        and limit is None
        else "partial"
    )

    scan_id = start_scan_run(
        requested=len(tickers),
        scan_type=scan_type,
    )

    if not tickers:
        scan_result.finished_at = datetime.now()

        print(
            "No active tickers were found."
        )

        return scan_result

    print()
    print("TickerTrends Universe Scanner")
    print("=============================")
    print(f"Tickers:  {len(tickers)}")
    print(f"Database: {get_database_path()}")
    print()

    for position, ticker in enumerate(
        tickers,
        start=1,
    ):
        print(
            f"[{position:03}/{len(tickers):03}] "
            f"{ticker:<7}",
            end=" ",
            flush=True,
        )

        result = scan_ticker_with_retry(
            ticker=ticker,
            retries=retries,
            retry_delay=retry_delay,
        )

        scan_result.ticker_results.append(
            result
        )

        if result.success:
            scan_result.successful += 1

            if result.state_changed:
                scan_result.state_changes += 1

            fundamental_text = (
                format_score(
                    result.fundamental_score
                )
            )

            total_text = format_score(
                result.total_score
            )

            print(
                f"{result.trend_state:<16} "
                f"T:{format_score(result.technical_score):>4} "
                f"F:{fundamental_text:>4} "
                f"Total:{total_text:>5} "
                f"({result.elapsed_seconds:.1f}s)"
            )

            if result.state_changed:
                print(
                    f"    CHANGE: "
                    f"{result.previous_state} "
                    f"-> {result.trend_state}"
                )

        else:
            scan_result.failed += 1

            print(
                f"FAILED "
                f"({result.elapsed_seconds:.1f}s)"
            )

            print(
                f"    {result.error}"
            )

        # No delay is needed after the final ticker.
        if (
            delay > 0
            and position < len(tickers)
        ):
            time.sleep(
                delay
            )

    scan_result.finished_at = datetime.now()

    complete_scan_run(
        scan_id=scan_id,
        successful=scan_result.successful,
        failed=scan_result.failed,
        state_changes=scan_result.state_changes,
    )

    return scan_result


# ============================================================
# SUMMARY
# ============================================================

def print_scan_summary(
    result: UniverseScanResult,
) -> None:
    """
    Print final scan statistics.
    """

    print()
    print("TickerTrends Scan Summary")
    print("=========================")

    print(
        f"Requested:       "
        f"{result.requested}"
    )

    print(
        f"Successful:      "
        f"{result.successful}"
    )

    print(
        f"Failed:          "
        f"{result.failed}"
    )

    print(
        f"State changes:   "
        f"{result.state_changes}"
    )

    print(
        f"Elapsed time:    "
        f"{format_duration(result.elapsed_seconds)}"
    )

    print()
    print("Trend Distribution")
    print("------------------")

    trend_order = [
        "Strong Bullish",
        "Bullish",
        "Accumulation",
        "Extended",
        "Weakening",
        "Bearish",
    ]

    counts = result.trend_counts

    for state in trend_order:
        print(
            f"{state:16} "
            f"{counts.get(state, 0):>4}"
        )

    failed_results = [
        ticker_result
        for ticker_result in result.ticker_results
        if not ticker_result.success
    ]

    if failed_results:
        print()
        print("Failed Tickers")
        print("--------------")

        for failed in failed_results:
            print(
                f"{failed.ticker:<7} "
                f"{failed.error}"
            )

    print()

    print(
        "Each successful ticker was saved "
        "to SQLite."
    )

    print(
        f"Database: {get_database_path()}"
    )

    print()


# ============================================================
# DATABASE VERIFICATION
# ============================================================

def print_database_summary() -> None:
    """
    Print a short summary of saved ticker states.
    """

    states = get_all_ticker_states()

    scored = [
        row
        for row in states
        if row.get("total_score") is not None
    ]

    print(
        f"SQLite currently contains "
        f"{len(states)} ticker states."
    )

    print(
        f"Complete 100-point scores: "
        f"{len(scored)}"
    )


# ============================================================
# COMMAND-LINE ARGUMENTS
# ============================================================

def parse_arguments() -> argparse.Namespace:
    """
    Parse scanner command-line options.
    """

    parser = argparse.ArgumentParser(
        description=(
            "Run the TickerTrends model across "
            "the active stock universe."
        )
    )

    parser.add_argument(
        "--ticker",
        type=str,
        help=(
            "Scan one ticker, such as MSFT."
        ),
    )

    parser.add_argument(
        "--tickers",
        nargs="+",
        help=(
            "Scan a list of tickers, such as "
            "MSFT AAPL NVDA."
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Limit the number of universe tickers."
        ),
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY_SECONDS,
        help=(
            "Seconds to pause between tickers. "
            f"Default: {DEFAULT_DELAY_SECONDS}"
        ),
    )

    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help=(
            "Number of retries after a ticker failure. "
            f"Default: {DEFAULT_RETRIES}"
        ),
    )

    parser.add_argument(
        "--retry-delay",
        type=float,
        default=DEFAULT_RETRY_DELAY_SECONDS,
        help=(
            "Seconds to wait before retrying. "
            f"Default: {DEFAULT_RETRY_DELAY_SECONDS}"
        ),
    )

    parser.add_argument(
        "--no-sync",
        action="store_true",
        help=(
            "Do not synchronize the universe CSV files "
            "before scanning."
        ),
    )

    return parser.parse_args()


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    """
    Run the scanner from the command line.
    """

    args = parse_arguments()

    requested_tickers: list[str] | None = None

    if args.ticker:
        requested_tickers = [
            args.ticker
        ]

    elif args.tickers:
        requested_tickers = (
            args.tickers
        )

    result = scan_universe(
        requested_tickers=requested_tickers,
        limit=args.limit,
        delay=max(args.delay, 0),
        retries=max(args.retries, 0),
        retry_delay=max(
            args.retry_delay,
            0,
        ),
        sync_before_scan=not args.no_sync,
    )

    print_scan_summary(
        result
    )

    print_database_summary()


if __name__ == "__main__":
    main()