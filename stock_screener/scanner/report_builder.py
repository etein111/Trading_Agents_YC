"""Layer 4: Report Builder — generates portfolio adjustment recommendations."""

from dataclasses import dataclass, field
from typing import Optional
from .config import MAX_POSITION_WEIGHT, SCORE_THRESHOLDS


@dataclass
class Adjustment:
    action: str  # "REDUCE" | "ADD" | "NEW" | "HOLD"
    ticker: str
    current_shares: int
    recommended_shares: int
    reason: str
    source: dict = field(default_factory=dict)


@dataclass
class Report:
    adjustments: list = field(default_factory=list)
    unchanged: list = field(default_factory=list)
    anomalies: list = field(default_factory=list)
    sector_rankings: list = field(default_factory=list)


class ReportBuilder:
    """Builds portfolio adjustment recommendations from stock scores."""

    def __init__(self, portfolio_file: str = "data/portfolio.json",
                 max_position_weight: float = MAX_POSITION_WEIGHT,
                 strong_buy_threshold: float = SCORE_THRESHOLDS["strong_buy"],
                 consider_threshold: float = SCORE_THRESHOLDS["consider"]):
        self.portfolio_file = portfolio_file
        self.max_position_weight = max_position_weight
        self.strong_buy_threshold = strong_buy_threshold
        self.consider_threshold = consider_threshold

    def build_adjustments(self, positions: list[dict], stock_scores: list[dict],
                          cash: float) -> dict:
        """
        Args:
            positions: [{"ticker": str, "shares": int, "entry_price": float}, ...]
            stock_scores: [{"ticker": str, "composite": float, "sector": str, ...}, ...]
            cash: float — available cash
        """
        portfolio_value = sum(p["shares"] * p["entry_price"] for p in positions) + cash
        adj, unchanged = [], []

        score_by_ticker = {s["ticker"]: s for s in stock_scores}
        position_by_ticker = {p["ticker"]: p for p in positions}

        # Process existing positions
        for pos in positions:
            ticker = pos["ticker"]
            score = score_by_ticker.get(ticker, {})
            composite = score.get("composite", 0)
            current_shares = pos["shares"]
            current_value = current_shares * pos["entry_price"]
            position_weight = current_value / portfolio_value if portfolio_value else 0

            if composite < self.consider_threshold:
                recommended = max(0, current_shares - 1)
                if recommended < current_shares:
                    adj.append(Adjustment(
                        action="REDUCE",
                        ticker=ticker,
                        current_shares=current_shares,
                        recommended_shares=recommended,
                        reason=f"综合得分{composite:.2f}偏低(<{self.consider_threshold:.2f})，建议减仓释放资金",
                        source={"composite_score": composite, "position_weight": round(position_weight, 3)},
                    ))
                else:
                    unchanged.append({"ticker": ticker, "reason": "已是最低持仓"})
            else:
                unchanged.append({
                    "ticker": ticker,
                    "reason": f"综合得分{composite:.2f}尚可，持仓比例{round(position_weight*100,1)}%"
                })

        # Process new opportunities
        held_tickers = set(position_by_ticker.keys())
        for score in stock_scores:
            ticker = score["ticker"]
            if ticker in held_tickers:
                continue
            composite = score["composite"]
            if composite >= self.strong_buy_threshold:
                adj.append(Adjustment(
                    action="NEW",
                    ticker=ticker,
                    current_shares=0,
                    recommended_shares=1,
                    reason=f"综合得分{composite:.2f}高(≥{self.strong_buy_threshold:.2f})，{score.get('sector', '')}板块强势，建议新建仓1股试探",
                    source=score,
                ))

        return {
            "adjustments": [a.__dict__ for a in adj],
            "unchanged": unchanged,
        }

    def build_full_report(self, sector_results: list, stock_scores: list,
                          anomalies: list, positions: list, cash: float) -> Report:
        adjustments_result = self.build_adjustments(positions, stock_scores, cash)
        return Report(
            adjustments=adjustments_result["adjustments"],
            unchanged=adjustments_result["unchanged"],
            anomalies=anomalies,
            sector_rankings=sector_results,
        )
