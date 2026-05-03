"""Entry point: runs the full stock screener pipeline."""

import os
from pathlib import Path

# Load .env file so Gmail credentials are available
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from stock_screener.scanner import (
    AnomalyDetector, SectorScanner, StockScorer,
    Aggregator, ReportBuilder, SECTORS,
)

# Optional import - PortfolioManager from tradingagents.agents.portfolio.manager
# This module may not exist or may require additional dependencies
_portfolio_manager_class = None
try:
    from tradingagents.agents.portfolio.manager import PortfolioManager
    _has_portfolio_manager = True
except ImportError:
    # PortfolioManager not available - use fallback
    _has_portfolio_manager = False
    PortfolioManager = None

try:
    from scheduler.gmail_pusher import GmailPusher
    _has_gmail_pusher = True
except ImportError:
    _has_gmail_pusher = False
    GmailPusher = None


def run_daily_scan() -> dict:
    """Run full pipeline: anomaly → sector → stock → aggregate → report."""
    # Layer 0: Anomaly detection (simplified — real impl fetches data)
    detector = AnomalyDetector()
    anomalies = detector.detect()

    # Layer 1: Sector ranking
    scanner = SectorScanner()
    sector_result = scanner.scan()

    # Layer 2: Score all stocks per sector
    scorer = StockScorer()
    all_scores = []
    for sector in SECTORS:
        scored = scorer.score_sector_stocks(sector)
        all_scores.extend([{**s.__dict__, "ticker": s.stock} for s in scored])

    # Layer 3: Aggregate
    agg = Aggregator()
    aggregated = agg.aggregate(all_scores)
    top_by_sector = agg.top_per_sector(all_scores, top_n=3)

    # Layer 4: Portfolio adjustments (if PortfolioManager available)
    if _has_portfolio_manager:
        pm = PortfolioManager("data/portfolio.json")
        positions = pm.get_positions()
        cash = pm.get_cash_balance()

        builder = ReportBuilder()
        adjustments_result = builder.build_adjustments(
            [{"ticker": p["ticker"], "shares": p["shares"], "entry_price": p["entry_price"]}
             for p in positions],
            all_scores,
            cash,
        )
    else:
        # Fallback when PortfolioManager not available
        builder = ReportBuilder()
        adjustments_result = builder.build_adjustments([], all_scores, 0)

    return {
        "sectors": sector_result["sectors"],
        "all_stocks": all_scores,
        "top_by_sector": top_by_sector,
        "adjustments": adjustments_result["adjustments"],
        "unchanged": adjustments_result["unchanged"],
        "anomalies": [a.__dict__ for a in anomalies],
        "scan_date": sector_result["scan_date"],
    }


def send_daily_report():
    """Run scan and send Gmail report."""
    if not _has_gmail_pusher:
        raise ImportError("GmailPusher not available - check scheduler package installation")
    result = run_daily_scan()

    # Deep agent analysis for top 8 stocks
    all_stocks = result["all_stocks"]
    top_tickers = [s["ticker"] for s in all_stocks[:8]]
    from stock_screener.scanner.deep_analysis import run_deep_analysis
    deep_results = run_deep_analysis(top_tickers, result["scan_date"], SECTORS, top_n=8)
    # Fill composite scores from pre-computed all_stocks
    score_map = {s["ticker"]: s["composite"] for s in all_stocks}
    for d in deep_results:
        d.composite_score = score_map.get(d.ticker, 0.0)

    # Load portfolio for positions display
    portfolio_positions = []
    if _has_portfolio_manager:
        pm = PortfolioManager("data/portfolio.json")
        portfolio_positions = pm.get_positions()

    pusher = GmailPusher("yechuan958@gmail.com", "yechuan958@gmail.com")
    report = {
        "scan_date": result["scan_date"],
        "sector_rankings": result["sectors"],
        "all_stocks": result["all_stocks"],
        "top_by_sector": result["top_by_sector"],
        "adjustments": result["adjustments"],
        "unchanged": result["unchanged"],
        "anomalies": result["anomalies"],
        "portfolio_positions": portfolio_positions,
        "deep_stocks": [d.__dict__ for d in deep_results],
    }
    msg = pusher.format_deep_screener_report(report)
    pusher.send_with_retry(msg)