"""Layer 1: Sector Scanner — ranks 6 sectors using weighted dimensions."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import yfinance as yf
import pandas as pd

from .config import SECTORS, WEIGHTS


@dataclass
class SectorScore:
    name: str
    score: float
    rank: int
    breakdown: dict = field(default_factory=dict)


def _score_momentum(etf_ticker: str, lookback: int = 20) -> float:
    """ETF price return over lookback days normalized to 0-1."""
    try:
        proxy = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}
        data = yf.download(etf_ticker, period=f"{lookback}d", proxy=proxy, progress=False)
        if len(data) < 5:
            return 0.5
        close = data["Close"]
        if isinstance(close, pd.DataFrame):
            first_price = close.iloc[0, 0]
            last_price = close.iloc[-1, 0]
        else:
            first_price = close.iloc[0]
            last_price = close.iloc[-1]
        ret = (last_price / first_price) - 1
        normalized = (ret + 0.20) / 0.40
        return max(0.0, min(1.0, normalized))
    except Exception:
        return 0.5


def _score_valuation(sector_stocks: list[str]) -> float:
    """Median PE of sector stocks, normalized vs historical range (0-1)."""
    try:
        pes = []
        proxy = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}
        for ticker in sector_stocks:
            info = yf.Ticker(ticker, proxy=proxy).info
            pe = info.get("trailingPE") or info.get("forwardPE")
            if pe and pe > 0:
                pes.append(pe)
        if not pes:
            return 0.5
        median_pe = sorted(pes)[len(pes) // 2]
        normalized = (50 - median_pe) / 45
        return max(0.0, min(1.0, normalized))
    except Exception:
        return 0.5


def _score_fundamentals(sector_stocks: list[str]) -> float:
    """Average revenue growth of sector stocks (0-1)."""
    try:
        proxy = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}
        growths = []
        for ticker in sector_stocks:
            info = yf.Ticker(ticker, proxy=proxy).info
            rev_growth = info.get("revenueGrowth") or 0
            growths.append(rev_growth)
        avg = sum(growths) / len(growths)
        normalized = (avg + 0.50) / 1.00
        return max(0.0, min(1.0, normalized))
    except Exception:
        return 0.5


class SectorScanner:
    """Ranks sectors using A×0.4 + B×0.3 + E×0.2 + C×0.1 weights."""

    def __init__(self, sectors: dict = SECTORS, weights: dict = WEIGHTS,
                 lookback: int = 20):
        self.sectors = sectors
        self.weights = weights
        self.lookback = lookback

    def scan(self) -> dict:
        sector_results = []
        for sector_name, cfg in self.sectors.items():
            etf_ticker = cfg["etf"]
            stocks = cfg["stocks"]

            momentum = _score_momentum(etf_ticker, self.lookback)
            valuation = _score_valuation(stocks)
            fundamentals = _score_fundamentals(stocks)
            # Macro score — placeholder using momentum + news (simplified)
            # TODO: macro scoring via News Analyst (alpha_vantage sentiment + policy events)
            macro = (momentum + valuation) / 2

            composite = (
                momentum * self.weights["momentum"]
                + valuation * self.weights["valuation"]
                + macro * self.weights["macro"]
                + fundamentals * self.weights["fundamentals"]
            )

            sector_results.append(SectorScore(
                name=sector_name,
                score=round(composite, 3),
                rank=0,
                breakdown={
                    "momentum": round(momentum, 3),
                    "valuation": round(valuation, 3),
                    "macro": round(macro, 3),
                    "fundamentals": round(fundamentals, 3),
                }
            ))

        # Sort descending by score, assign ranks
        sector_results.sort(key=lambda s: s.score, reverse=True)
        for i, s in enumerate(sector_results):
            s.rank = i + 1

        return {
            "sectors": [s.__dict__ for s in sector_results],
            "scan_date": datetime.now().strftime("%Y-%m-%d"),
            "methodology": "A×0.4 + B×0.3 + E×0.2 + C×0.1",
        }