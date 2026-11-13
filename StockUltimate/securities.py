"""Shared security universe for stockchoice.

Keep ticker symbols and display names in one place so Watchlist, Compare,
Growth, Value, Dividend, ETF, and Details pages can share the same choices.
"""
from __future__ import annotations

# Core stock universe
STOCKS: dict[str, str] = {
    "AAPL": "Apple",
    "ABBV": "AbbVie",
    "ABT": "Abbott Laboratories",
    "ADBE": "Adobe",
    "AMD": "Advanced Micro Devices",
    "AMGN": "Amgen",
    "AMZN": "Amazon",
    "AVGO": "Broadcom",
    "BAC": "Bank of America",
    "BF-B": "Brown Forman",
    "BMY": "Bristol Myers",
    "BRK-B": "Berkshire Hathaway",
    "CAT": "Caterpillar",
    "CMCSA": "Comcast",
    "COST": "Costco Wholesale",
    "CRM": "Salesforce",
    "CSCO": "Cisco Systems",
    "CVX": "Chevron",
    "DIS": "Walt Disney",
    "ESS": "Essex Property Trust",
    "F": "Ford Motor Co",
    "GOOG": "Alphabet",
    "HD": "Home Depot",
    "HON": "Honeywell",
    "IBM": "IBM",
    "JNJ": "Johnson & Johnson",
    "JPM": "JPMorgan Chase",
    "KMB": "Kimberly Clark",
    "KO": "Coca-Cola",
    "LLY": "Eli Lilly",
    "LOW": "Lowe's",
    "MA": "Mastercard",
    "MCD": "McDonald's",
    "MDLZ": "Mondelez",
    "META": "Meta Platforms",
    "MRK": "Merck",
    "MSFT": "Microsoft",
    "NEE": "NextEra Energy",
    "NFLX": "Netflix",
    "NKE": "Nike",
    "NVDA": "NVIDIA",
    "O": "Realty Investment Corp",
    "ORCL": "Oracle",
    "PEP": "PepsiCo",
    "PG": "Procter & Gamble",
    "PPG": "PPG Industries",
    "QCOM": "Qualcomm",
    "SBUX": "Starbucks",
    "T": "AT&T",
    "TMO": "Thermo Fisher Scientific",
    "TSLA": "Tesla",
    "TXN": "Texas Instruments",
    "UNH": "UnitedHealth Group",
    "UPS": "UPS",
    "V": "Visa",
    "VZ": "Verizon",
    "WMT": "Walmart",
    "XOM": "Exxon Mobil",
    "AFL": "Aflac",
    "ADP": "Automatic Data Processing",
    "APD": "Air Products and Chemicals",
    "BLK": "BlackRock",
    "C": "Citigroup",
    "CINF": "Cincinnati Financial",
    "CL": "Colgate-Palmolive",
    "COP": "ConocoPhillips",
    "CRWD": "CrowdStrike",
    "CVS": "CVS Health",
    "DDOG": "Datadog",
    "DHR": "Danaher",
    "ED": "Consolidated Edison",
    "EMR": "Emerson Electric",
    "GD": "General Dynamics",
    "GM": "General Motors",
    "GS": "Goldman Sachs",
    "MDT": "Medtronic",
    "MET": "MetLife",
    "NEM": "Newmont",
    "NOW": "ServiceNow",
    "PANW": "Palo Alto Networks",
    "PFE": "Pfizer",
    "PLTR": "Palantir Technologies",
    "SHOP": "Shopify",
    "SNOW": "Snowflake",
    "TROW": "T. Rowe Price",
    "UBER": "Uber Technologies",
}

# Core ETF universe
ETFS: dict[str, str] = {
    # Broad market / index
    "DIA": "SPDR Dow Jones Industrial Average ETF Trust",
    "IWM": "iShares Russell 2000 ETF",
    "QQQ": "Invesco QQQ Trust",
    "SPY": "SPDR S&P 500 ETF Trust",
    "VTI": "Vanguard Total Stock Market ETF",
    "VOO": "Vanguard S&P 500 ETF",

    # Style
    "IWF": "iShares Russell 1000 Growth ETF",
    "IWD": "iShares Russell 1000 Value ETF",
    "VUG": "Vanguard Growth ETF",
    "VTV": "Vanguard Value ETF",
    "QUAL": "iShares Quality Tilt",

    # Dividend / income
    "DGRO": "iShares Core Dividend Growth ETF",
    "HDV": "iShares Core High Dividend ETF",
    "SCHD": "Schwab U.S. Dividend Equity ETF",
    "VIG": "Vanguard Dividend Appreciation ETF",
    "VYM": "Vanguard High Dividend Yield ETF",

    # Sectors
    "XLB": "Materials Select Sector SPDR Fund",
    "XLC": "Communication Services Select Sector SPDR Fund",
    "XLE": "Energy Select Sector SPDR Fund",
    "XLF": "Financial Select Sector SPDR Fund",
    "XLI": "Industrial Select Sector SPDR Fund",
    "XLK": "Technology Select Sector SPDR Fund",
    "XLP": "Consumer Staples Select Sector SPDR Fund",
    "XLRE": "Real Estate Select Sector SPDR Fund",
    "XLU": "Utilities Select Sector SPDR Fund",
    "XLV": "Health Care Select Sector SPDR Fund",
    "XLY": "Consumer Discretionary Select Sector SPDR Fund",

    # Bonds
    "AGG": "iShares Core U.S. Aggregate Bond ETF",
    "BND": "Vanguard Total Bond Market ETF",
    "HYG": "iShares iBoxx $ High Yield Corporate Bond ETF",
    "IEF": "iShares 7-10 Year Treasury Bond ETF",
    "LQD": "iShares iBoxx $ Investment Grade Corporate Bond ETF",
    "SHY": "iShares 1-3 Year Treasury Bond ETF",
    "TLT": "iShares 20+ Year Treasury Bond ETF",
    "SGOV": "IShares Short Term Gov",

    # International
    "EFA": "iShares MSCI EAFE ETF",
    "EEM": "iShares MSCI Emerging Markets ETF",
    "VXUS": "Vanguard Total International Stock ETF",
    "GLD": "SPDR Gold Shares",
    "IVV": "iShares Core S&P 500 ETF",
    "IXUS": "iShares Core MSCI Total International Stock ETF",
    "QQQM": "Invesco NASDAQ 100 ETF",
    "SCHG": "Schwab U.S. Large-Cap Growth ETF",
    "SCHV": "Schwab U.S. Large-Cap Value ETF",
    "USO": "United States Oil Fund",
    "VCSH": "Vanguard Short-Term Corporate Bond ETF",
    "VEA": "Vanguard FTSE Developed Markets ETF",
    "VWO": "Vanguard FTSE Emerging Markets ETF",
}

ALL_SECURITIES: dict[str, str] = {**STOCKS, **ETFS}


def get_security_name(symbol: str) -> str:
    """Return the display name for a ticker, falling back to the ticker."""
    symbol = str(symbol).strip().upper()
    return ALL_SECURITIES.get(symbol, symbol)


def get_security_type(symbol: str) -> str:
    """Return 'Stock', 'ETF', or 'Unknown' for a ticker."""
    symbol = str(symbol).strip().upper()
    if symbol in STOCKS:
        return "Stock"
    if symbol in ETFS:
        return "ETF"
    return "Unknown"


def get_security_options(exclude: list[str] | tuple[str, ...] | set[str] | None = None) -> list[str]:
    """Return alphabetized ticker choices, optionally excluding symbols."""
    excluded = {str(s).strip().upper() for s in (exclude or [])}
    return [symbol for symbol in sorted(ALL_SECURITIES) if symbol not in excluded]


def format_security_option(symbol: str) -> str:
    """Format a selectbox option as 'TICKER — Name'."""
    symbol = str(symbol).strip().upper()
    return f"{symbol} — {get_security_name(symbol)}"
