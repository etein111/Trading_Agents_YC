"""Layer 3: Aggregator — applies thresholds and ranks all stocks."""

from dataclasses import dataclass, field
from typing import Optional
from .config import SCORE_THRESHOLDS


@dataclass
class AggregatedResult:
    strong_buy: list = field(default_factory=list)
    consider: list = field(default_factory=list)
    skip: list = field(default_factory=list)
    all_stocks: list = field(default_factory=list)


class Aggregator:
    """Applies scoring thresholds and categorizes stocks."""

    def __init__(self, thresholds: Optional[dict] = None):
        if thresholds is None:
            thresholds = SCORE_THRESHOLDS
        self.strong_buy_threshold = thresholds["strong_buy"]
        self.consider_threshold = thresholds["consider"]

    def aggregate(self, stock_scores: list[dict]) -> AggregatedResult:
        strong_buy, consider, skip = [], [], []

        for s in stock_scores:
            composite = s.get("composite", 0)
            if composite >= self.strong_buy_threshold:
                s["rating"] = "Strong Buy"
                strong_buy.append(s)
            elif composite >= self.consider_threshold:
                s["rating"] = "Consider"
                consider.append(s)
            else:
                s["rating"] = "Skip"
                skip.append(s)

        # Sort each bucket descending by composite
        strong_buy.sort(key=lambda x: x["composite"], reverse=True)
        consider.sort(key=lambda x: x["composite"], reverse=True)

        return AggregatedResult(
            strong_buy=strong_buy,
            consider=consider,
            skip=skip,
            all_stocks=stock_scores,
        )

    def top_per_sector(self, stock_scores: list[dict], top_n: int = 3) -> dict:
        """Per sector, return top N stocks across all ratings."""
        by_sector = {}
        for s in stock_scores:
            sector = s.get("sector", "Unknown")
            by_sector.setdefault(sector, []).append(s)

        result = {}
        for sector, stocks in by_sector.items():
            stocks.sort(key=lambda x: x["composite"], reverse=True)
            result[sector] = stocks[:top_n]
        return result