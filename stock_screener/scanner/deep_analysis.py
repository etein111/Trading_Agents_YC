"""Layer 4: Deep agent analysis for top N stocks via TradingAgentsGraph."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env so LLM provider settings are available
load_dotenv(Path(__file__).parent.parent.parent / ".env")

# Set yfinance proxy globally before any TradingAgents imports
import yfinance as _yf
_http = os.getenv("HTTP_PROXY") or os.getenv("http_proxy") or "http://127.0.0.1:7890"
_https = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy") or "http://127.0.0.1:7890"
_yf.set_config(proxy={"http": _http, "https": _https})

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.agents.utils.rating import parse_rating


def _sector_for(ticker: str, sectors_map: dict) -> str:
    for sector, cfg in sectors_map.items():
        if ticker in cfg.get("stocks", []):
            return sector
    return "Unknown"


def _build_config():
    """Build config dict with .env LLM overrides, matching cli/main.py pattern."""
    cfg = DEFAULT_CONFIG.copy()
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    deep_model = os.getenv("LLM_DEEP_MODEL", "")
    quick_model = os.getenv("LLM_QUICK_MODEL", "")
    backend_url = os.getenv("BACKEND_URL") or None
    cfg["llm_provider"] = provider
    if deep_model:
        cfg["deep_think_llm"] = deep_model
    if quick_model:
        cfg["quick_think_llm"] = quick_model
    cfg["backend_url"] = backend_url
    cfg["checkpoint_enabled"] = False
    return cfg


@dataclass
class DeepStockAnalysis:
    ticker: str
    sector: str
    composite_score: float
    market_report: str = ""
    sentiment_report: str = ""
    news_report: str = ""
    fundamentals_report: str = ""
    investment_plan: str = ""
    trader_plan: str = ""
    final_decision: str = ""
    rating: str = "Hold"
    error: Optional[str] = None


def run_deep_analysis(
    tickers: list[str],
    trade_date: str,
    sectors_map: dict,
    top_n: int = 8,
) -> list[DeepStockAnalysis]:
    """Run TradingAgentsGraph.propagate() on each ticker and collect all agent reports."""
    results = []
    for ticker in tickers[:top_n]:
        analysis = _analyze_one(ticker, trade_date, sectors_map)
        results.append(analysis)
    return results


def _analyze_one(ticker: str, trade_date: str, sectors_map: dict) -> DeepStockAnalysis:
    sector = _sector_for(ticker, sectors_map)
    try:
        graph = TradingAgentsGraph(
            selected_analysts=["market", "social", "news", "fundamentals"],
            debug=False,
            config=_build_config(),
        )
        final_state, _ = graph.propagate(ticker, trade_date)

        # Extract rating from final_trade_decision text
        rating = parse_rating(final_state.get("final_trade_decision", ""))

        return DeepStockAnalysis(
            ticker=ticker,
            sector=sector,
            composite_score=0.0,  # filled by caller
            market_report=_trunc(final_state.get("market_report", "")),
            sentiment_report=_trunc(final_state.get("sentiment_report", "")),
            news_report=_trunc(final_state.get("news_report", "")),
            fundamentals_report=_trunc(final_state.get("fundamentals_report", "")),
            investment_plan=_trunc(final_state.get("investment_plan", "")),
            trader_plan=_trunc(final_state.get("trader_investment_plan", "")),
            final_decision=_trunc(final_state.get("final_trade_decision", "")),
            rating=rating,
        )
    except Exception as e:
        return DeepStockAnalysis(
            ticker=ticker,
            sector=sector,
            composite_score=0.0,
            error=str(e),
        )


def _trunc(text: str, max_chars: int = 3000) -> str:
    if not text:
        return ""
    return text[:max_chars] if len(text) > max_chars else text
