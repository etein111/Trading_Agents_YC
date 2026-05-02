"""Layer 2: Stock Scorer — runs analyst-style scoring on individual stocks."""

from dataclasses import dataclass
from typing import Optional
import yfinance as yf

from .config import SECTORS


@dataclass
class StockScore:
    stock: str
    sector: str
    scores: dict  # momentum, valuation, macro, fundamentals
    composite: float
    peer_avg: dict
    above_peer: bool


class StockScorer:
    """Scores individual stocks across 4 dimensions."""

    def score_stock(self, ticker: str) -> StockScore:
        sector = self._find_sector(ticker)
        stocks_in_sector = SECTORS.get(sector, {}).get("stocks", [])

        momentum = self._score_momentum(ticker)
        valuation = self._score_valuation(ticker)
        macro = self._score_macro(ticker)
        fundamentals = self._score_fundamentals(ticker)

        composite = (
            momentum * 0.4
            + valuation * 0.3
            + macro * 0.2
            + fundamentals * 0.1
        )

        peer_avgs = {
            "momentum": momentum,
            "valuation": valuation,
            "macro": macro,
            "fundamentals": fundamentals,
        }
        above_peer = composite > sum(peer_avgs.values()) / len(peer_avgs)

        return StockScore(
            stock=ticker,
            sector=sector,
            scores={
                "momentum": round(momentum, 3),
                "valuation": round(valuation, 3),
                "macro": round(macro, 3),
                "fundamentals": round(fundamentals, 3),
            },
            composite=round(composite, 3),
            peer_avg=peer_avgs,
            above_peer=above_peer,
        )

    def score_sector_stocks(self, sector: str) -> list[StockScore]:
        stocks = SECTORS.get(sector, {}).get("stocks", [])
        return [self.score_stock(s) for s in stocks]

    def _find_sector(self, ticker: str) -> str:
        for sector, cfg in SECTORS.items():
            if ticker in cfg["stocks"]:
                return sector
        return "Unknown"

    def _score_momentum(self, ticker: str) -> float:
        try:
            proxy = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}
            data = yf.Ticker(ticker, proxy=proxy).history(period="1mo")
            if len(data) < 10:
                return 0.5
            ret = (data["Close"].iloc[-1] / data["Close"].iloc[0]) - 1
            normalized = (ret + 0.20) / 0.40
            return max(0.0, min(1.0, normalized))
        except Exception:
            return 0.5

    def _score_valuation(self, ticker: str) -> float:
        try:
            proxy = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}
            info = yf.Ticker(ticker, proxy=proxy).info
            pe = info.get("trailingPE") or info.get("forwardPE")
            if not pe or pe <= 0:
                return 0.5
            normalized = (50 - pe) / 45
            return max(0.0, min(1.0, normalized))
        except Exception:
            return 0.5

    def _score_macro(self, ticker: str) -> float:
        # Simplified: news sentiment as macro proxy
        # TODO: macro scoring via News Analyst (alpha_vantage sentiment + policy events)
        try:
            proxy = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}
            news = yf.Ticker(ticker, proxy=proxy).news
            if not news:
                return 0.5
            return 0.5
        except Exception:
            return 0.5

    def _score_fundamentals(self, ticker: str) -> float:
        try:
            proxy = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}
            info = yf.Ticker(ticker, proxy=proxy).info
            roe = info.get("returnOnEquity") or 0
            debt_to_equity = info.get("debtToEquity") or 100
            rev_growth = info.get("revenueGrowth") or 0
            roe_score = max(0.0, min(1.0, roe)) if roe else 0.3
            debt_score = max(0.0, 1.0 - debt_to_equity / 200) if debt_to_equity else 0.5
            growth_score = max(0.0, min(1.0, (rev_growth + 0.5) / 1.0))
            return (roe_score * 0.4 + debt_score * 0.3 + growth_score * 0.3)
        except Exception:
            return 0.5