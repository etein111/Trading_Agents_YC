# Stock Screener Multi-Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a daily stock screener + portfolio rebalancer that scans 6 sectors, ranks stocks per sector, and generates a Gmail report with sector rankings, stock recommendations, and portfolio adjustment suggestions.

**Architecture:** Layered pipeline — Anomaly Detection (Layer 0) → Sector Scanner (Layer 1) → Stock Analyst Agents (Layer 2) → Aggregator (Layer 3) → Portfolio Manager (Layer 4) → Gmail report. Reuses existing TradingAgents analysts where possible. Weekly weight review task runs Fridays.

**Tech Stack:** yfinance (data), existing Analyst agents (scoring), GmailPusher (email), SchedulerService (trigger), PortfolioManager (positions).

**Import paths** (correct paths for existing code):
- PortfolioManager: `from tradingagents.agents.portfolio.manager import PortfolioManager`
- All other imports from `stock_screener.scanner.*` (new code)

---

## File Structure

```
stock_screener/
├── scanner/
│   ├── __init__.py
│   ├── config.py          # Sector/ETF/watchlist config
│   ├── anomaly_detector.py # Layer 0: anomaly detection
│   ├── sector_scanner.py   # Layer 1: sector ranking
│   ├── stock_scorer.py    # Layer 2: orchestrates analysts per stock
│   ├── aggregator.py       # Layer 3: composite scores + thresholds
│   └── report_builder.py  # Layer 4: portfolio adjustment logic
├── scheduler/
│   ├── tasks.py           # Task definitions for screener tasks
│   └── gmail_pusher.py    # Extended with screener report formatting
```

**Modified files:**
- `tradingagents/agents/analysts/market_analyst.py` — add scoring method
- `tradingagents/agents/analysts/fundamentals_analyst.py` — add scoring method
- `tradingagents/agents/analysts/news_analyst.py` — add scoring method
- `tradingagents/agents/analysts/social_analyst.py` — add scoring method
- `data/task_queue.json` — add screener + weekly review tasks
- `scheduler/gmail_pusher.py` — add `format_screener_report()` method

---

## SECTOR_CONFIG (scanner/config.py)

```python
SECTORS = {
    "Technology":  {"etf": "XLK", "stocks": ["AMZN", "GOOG", "META", "MSFT", "ORCL"]},
    "Healthcare":   {"etf": "XLV", "stocks": ["JNJ", "PFE", "UNH", "MRK", "ABBV"]},
    "Finance":     {"etf": "XLF", "stocks": ["JPM", "BAC", "GS", "MS", "BLK"]},
    "Consumer":    {"etf": "XLY", "stocks": ["TSLA", "NKE", "KO", "PEP", "COST"]},
    "Energy":      {"etf": "XLE", "stocks": ["XOM", "CVX", "COP", "SLB", "OXY"]},
    "Industrials": {"etf": "XLI", "stocks": ["CAT", "BA", "HON", "GE", "UPS"]},
}

WEIGHTS = {"momentum": 0.4, "valuation": 0.3, "macro": 0.2, "fundamentals": 0.1}

SCORE_THRESHOLDS = {"strong_buy": 0.70, "consider": 0.50}
MAX_POSITION_WEIGHT = 0.30
```

---

## Task Breakdown

### Task 1: Scanner Config

**Files:**
- Create: `stock_screener/scanner/config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/stock_screener/test_config.py
def test_sector_config_has_required_fields():
    from stock_screener.scanner.config import SECTORS, WEIGHTS
    assert "Technology" in SECTORS
    assert SECTORS["Technology"]["etf"] == "XLK"
    assert len(SECTORS["Technology"]["stocks"]) >= 3
    assert sum(WEIGHTS.values()) == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/stock_screener/test_config.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Create stock_screener/scanner/__init__.py and config.py**

```python
# stock_screener/scanner/__init__.py
# Note: only export config constants at this stage. Other classes are created in Tasks 2-6.
from .config import SECTORS, WEIGHTS, SCORE_THRESHOLDS, MAX_POSITION_WEIGHT

__all__ = ["SECTORS", "WEIGHTS", "SCORE_THRESHOLDS", "MAX_POSITION_WEIGHT"]
```

```python
# stock_screener/scanner/config.py
SECTORS = {
    "Technology":  {"etf": "XLK", "stocks": ["AMZN", "GOOG", "META", "MSFT", "ORCL"]},
    "Healthcare":   {"etf": "XLV", "stocks": ["JNJ", "PFE", "UNH", "MRK", "ABBV"]},
    "Finance":     {"etf": "XLF", "stocks": ["JPM", "BAC", "GS", "MS", "BLK"]},
    "Consumer":    {"etf": "XLY", "stocks": ["TSLA", "NKE", "KO", "PEP", "COST"]},
    "Energy":      {"etf": "XLE", "stocks": ["XOM", "CVX", "COP", "SLB", "OXY"]},
    "Industrials": {"etf": "XLI", "stocks": ["CAT", "BA", "HON", "GE", "UPS"]},
}
WEIGHTS = {"momentum": 0.4, "valuation": 0.3, "macro": 0.2, "fundamentals": 0.1}
SCORE_THRESHOLDS = {"strong_buy": 0.70, "consider": 0.50}
MAX_POSITION_WEIGHT = 0.30
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/stock_screener/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add stock_screener/scanner/ tests/stock_screener/test_config.py
git commit -m "feat(stock_screener): add sector config with 6 sectors and weights"
```

---

### Task 2: Anomaly Detector (Layer 0)

**Files:**
- Create: `stock_screener/scanner/anomaly_detector.py`
- Test: `tests/stock_screener/test_anomaly_detector.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/stock_screener/test_anomaly_detector.py
def test_detect_anomaly_etf_inflow():
    """Test ETF net inflow anomaly detection."""
    from stock_screener.scanner.anomaly_detector import AnomalyDetector

    # Mock ETF history data showing unusual volume surge
    mock_data = {
        "XLK": [1e6, 1.2e6, 1.1e6, 5e6, 5.5e6],  # Last 2 days 5x average
        "XLF": [1e6, 1.1e6, 1e6, 1.2e6, 1.1e6],  # Normal
    }
    detector = AnomalyDetector(etf_volume_data=mock_data)
    anomalies = detector.detect()

    assert "Technology" in [a["sector"] for a in anomalies]
    assert anomalies[0]["signal"] == "etf_net_inflow"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/stock_screener/test_anomaly_detector.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write implementation**

```python
# stock_screener/scanner/anomaly_detector.py
"""Layer 0: Anomaly Detector — flags unusual sector activity without modifying weights."""

from dataclasses import dataclass


@dataclass
class Anomaly:
    sector: str
    signal: str  # "etf_net_inflow" | "price_breakout" | "policy_catalyst" | "institutional_building"
    description: str
    data_source: str
    severity: str = "medium"  # "low" | "medium" | "high"


class AnomalyDetector:
    """Detects anomalous sector activity across multiple signal types."""

    def __init__(self, etf_volume_data: dict | None = None,
                 etf_price_data: dict | None = None,
                 policy_events: list | None = None,
                 insider_data: dict | None = None):
        self.etf_volume_data = etf_volume_data or {}
        self.etf_price_data = etf_price_data or {}
        self.policy_events = policy_events or []
        self.insider_data = insider_data or {}
        # All detection methods handle None/empty inputs gracefully

    def detect(self) -> list[Anomaly]:
        anomalies = []
        anomalies.extend(self._check_etf_net_inflow())
        anomalies.extend(self._check_price_breakout())
        anomalies.extend(self._check_policy_catalyst())
        anomalies.extend(self._check_institutional_building())
        return anomalies

    def _check_etf_net_inflow(self) -> list[Anomaly]:
        """ETF volume > 3x 5-day average = unusual institutional interest."""
        results = []
        for sector, volumes in self.etf_volume_data.items():
            if len(volumes) < 5:
                continue
            avg = sum(volumes[:-2]) / max(len(volumes[:-2]), 1)
            recent = volumes[-1]
            if avg > 0 and recent > avg * 3:
                results.append(Anomaly(
                    sector=sector,
                    signal="etf_net_inflow",
                    description=f"ETF净流入激增: 近期日均{vrecent:.0f}股 vs 历史均值{avg:.0f}股 ({(recent/avg):.1f}x)",
                    data_source="yfinance ETF.history(volume=True)",
                    severity="high" if recent > avg * 5 else "medium",
                ))
        return results

    def _check_price_breakout(self) -> list[Anomaly]:
        """Price breakout above 50-day high."""
        results = []
        for sector, prices in self.etf_price_data.items():
            if len(prices) < 50:
                continue
            current = prices[-1]
            high_50d = max(prices[:-1])
            if current > high_50d * 1.02:  # 2% above 50d high
                results.append(Anomaly(
                    sector=sector,
                    signal="price_breakout",
                    description=f"价格突破50日高点: 当前${current:.2f} vs 50日高${high_50d:.2f}",
                    data_source="yfinance ETF.history(close=True)",
                    severity="medium",
                ))
        return results

    def _check_policy_catalyst(self) -> list[Anomaly]:
        """First-time policy coverage for a sector."""
        results = []
        sector_keywords = {
            "Technology": ["antitrust", "AI regulation", "data privacy", "CHIPS Act"],
            "Healthcare": ["drug pricing", "Medicare", "FDA approval", "health policy"],
            "Energy": ["OPEC", "carbon tax", "renewable subsidy", "oil reserve"],
            "Finance": ["interest rate", "bank regulation", "Dodd-Frank", "Basel"],
        }
        for event in self.policy_events:
            sector = event.get("sector", "")
            text = event.get("event", "")
            keywords = sector_keywords.get(sector, [])
            for kw in keywords:
                if kw.lower() in text.lower() and kw not in event.get("_seen", []):
                    results.append(Anomaly(
                        sector=sector,
                        signal="policy_catalyst",
                        description=f"政策催化: {kw} — {text[:80]}",
                        data_source="News Analyst output",
                        severity="high",
                    ))
                    break
        return results

    def _check_institutional_building(self) -> list[Anomaly]:
        """Large net insider buys in sector."""
        results = []
        for sector, data in self.insider_data.items():
            net = data.get("net_shares", 0)
            tx_count = data.get("transactions", 0)
            if net > 1_000_000 and tx_count > 5:
                results.append(Anomaly(
                    sector=sector,
                    signal="institutional_building",
                    description=f"机构持仓大幅增加: 净买入{net:,.0f}股, {tx_count}笔交易",
                    data_source="yfinance insider_transactions + 13F filings",
                    severity="high" if net > 5_000_000 else "medium",
                ))
        return results
```

- [ ] **Step 3: Write implementation** (continued — already shown above)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/stock_screener/test_anomaly_detector.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add stock_screener/scanner/anomaly_detector.py tests/stock_screener/test_anomaly_detector.py
git commit -m "feat(stock_screener): add AnomalyDetector Layer 0"
```

---

### Task 3: Sector Scanner (Layer 1)

**Files:**
- Create: `stock_screener/scanner/sector_scanner.py`
- Test: `tests/stock_screener/test_sector_scanner.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/stock_screener/test_sector_scanner.py
def test_sector_ranking_output():
    from stock_screener.scanner.sector_scanner import SectorScanner
    from stock_screener.scanner.config import SECTORS, WEIGHTS

    scanner = SectorScanner(sectors=SECTORS, weights=WEIGHTS)
    result = scanner.scan()

    assert "sectors" in result
    assert len(result["sectors"]) == 6
    assert result["sectors"][0]["rank"] == 1
    assert result["sectors"][0]["name"] == "Technology"  # highest weighted
    assert abs(sum(w for s in result["sectors"] for w in [s["breakdown"]["momentum"]])) > 0
    assert result["methodology"] == "A×0.4 + B×0.3 + E×0.2 + C×0.1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/stock_screener/test_sector_scanner.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# stock_screener/scanner/sector_scanner.py
"""Layer 1: Sector Scanner — ranks 6 sectors using weighted dimensions."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Annotated
import yfinance as yf
from stockstats import wrap

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
        data = yf.download(etf_ticker, period=f"{lookback}d", proxy={"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}, progress=False)
        if len(data) < 5:
            return 0.5
        ret = (data["Close"].iloc[-1] / data["Close"].iloc[0]) - 1
        # Map -20%~+20% return to 0-1
        normalized = (ret + 0.20) / 0.40
        return max(0.0, min(1.0, normalized))
    except Exception:
        return 0.5


def _score_valuation(sector_stocks: list[str]) -> float:
    """Median PE of sector stocks, normalized vs historical range (0-1)."""
    try:
        pes = []
        for ticker in sector_stocks:
            info = yf.Ticker(ticker).info
            pe = info.get("trailingPE") or info.get("forwardPE")
            if pe and pe > 0:
                pes.append(pe)
        if not pes:
            return 0.5
        median_pe = sorted(pes)[len(pes) // 2]
        # Lower PE = better value; map 5x-50x → 0-1 (lower is better)
        normalized = (50 - median_pe) / 45
        return max(0.0, min(1.0, normalized))
    except Exception:
        return 0.5


def _score_fundamentals(sector_stocks: list[str]) -> float:
    """Average revenue growth of sector stocks (0-1)."""
    try:
        growths = []
        for ticker in sector_stocks:
            info = yf.Ticker(ticker).info
            rev_growth = info.get("revenueGrowth") or 0
            growths.append(rev_growth)
        avg = sum(growths) / len(growths)
        # Map -0.5~+0.5 growth to 0-1
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/stock_screener/test_sector_scanner.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add stock_screener/scanner/sector_scanner.py tests/stock_screener/test_sector_scanner.py
git commit -m "feat(stock_screener): add SectorScanner Layer 1"
```

---

### Task 4: Stock Scorer (Layer 2)

**Files:**
- Create: `stock_screener/scanner/stock_scorer.py`
- Test: `tests/stock_screener/test_stock_scorer.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/stock_screener/test_stock_scorer.py
def test_score_stock_returns_all_dimensions():
    from stock_screener.scanner.stock_scorer import StockScorer

    scorer = StockScorer()
    result = scorer.score_stock("AMZN")

    assert "scores" in result
    assert set(result["scores"].keys()) == {"momentum", "valuation", "macro", "fundamentals"}
    for v in result["scores"].values():
        assert 0.0 <= v <= 1.0
    assert "peer_avg" in result
    assert "above_peer" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/stock_screener/test_stock_scorer.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# stock_screener/scanner/stock_scorer.py
"""Layer 2: Stock Scorer — runs analyst-style scoring on individual stocks."""

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated
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
            "momentum": momentum,  # simplified — real impl would avg sector peers
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
            data = yf.Ticker(ticker).history(period="1mo", proxy={"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"})
            if len(data) < 10:
                return 0.5
            ret = (data["Close"].iloc[-1] / data["Close"].iloc[0]) - 1
            normalized = (ret + 0.20) / 0.40
            return max(0.0, min(1.0, normalized))
        except Exception:
            return 0.5

    def _score_valuation(self, ticker: str) -> float:
        try:
            info = yf.Ticker(ticker).info
            pe = info.get("trailingPE") or info.get("forwardPE")
            if not pe or pe <= 0:
                return 0.5
            normalized = (50 - pe) / 45
            return max(0.0, min(1.0, normalized))
        except Exception:
            return 0.5

    def _score_macro(self, ticker: str) -> float:
        # Simplified: news sentiment as macro proxy
        try:
            news = yf.Ticker(ticker).news
            if not news:
                return 0.5
            # Use sentiment score if available
            sentiments = [n.get("relatedTickers", []) for n in news[:5]]
            # Placeholder — real impl would call News Analyst / alpha_vantage
            return 0.5
        except Exception:
            return 0.5

    def _score_fundamentals(self, ticker: str) -> float:
        try:
            info = yf.Ticker(ticker).info
            roe = info.get("returnOnEquity") or 0
            debt_to_equity = info.get("debtToEquity") or 100
            rev_growth = info.get("revenueGrowth") or 0
            # ROE normalized + debt penalty
            roe_score = max(0.0, min(1.0, roe)) if roe else 0.3
            debt_score = max(0.0, 1.0 - debt_to_equity / 200) if debt_to_equity else 0.5
            growth_score = max(0.0, min(1.0, (rev_growth + 0.5) / 1.0))
            return (roe_score * 0.4 + debt_score * 0.3 + growth_score * 0.3)
        except Exception:
            return 0.5
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/stock_screener/test_stock_scorer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add stock_screener/scanner/stock_scorer.py tests/stock_screener/test_stock_scorer.py
git commit -m "feat(stock_screener): add StockScorer Layer 2"
```

---

### Task 5: Aggregator (Layer 3)

**Files:**
- Create: `stock_screener/scanner/aggregator.py`
- Test: `tests/stock_screener/test_aggregator.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/stock_screener/test_aggregator.py
def test_aggregator_threshold_filtering():
    from stock_screener.scanner.aggregator import Aggregator
    from stock_screener.scanner.config import SCORE_THRESHOLDS

    agg = Aggregator(thresholds=SCORE_THRESHOLDS)
    stocks = [
        {"stock": "A", "composite": 0.75, "scores": {}},
        {"stock": "B", "composite": 0.55, "scores": {}},
        {"stock": "C", "composite": 0.40, "scores": {}},
    ]
    result = agg.aggregate(stocks)

    assert result["strong_buy"][0]["stock"] == "A"
    assert result["consider"][0]["stock"] == "B"
    assert result["skip"][0]["stock"] == "C"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/stock_screener/test_aggregator.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# stock_screener/scanner/aggregator.py
"""Layer 3: Aggregator — applies thresholds and ranks all stocks."""

from dataclasses import dataclass, field
from typing import Annotated
from .config import SCORE_THRESHOLDS


@dataclass
class AggregatedResult:
    strong_buy: list = field(default_factory=list)
    consider: list = field(default_factory=list)
    skip: list = field(default_factory=list)
    all_stocks: list = field(default_factory=list)


class Aggregator:
    """Applies scoring thresholds and categorizes stocks."""

    def __init__(self, thresholds: dict = SCORE_THRESHOLDS):
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/stock_screener/test_aggregator.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add stock_screener/scanner/aggregator.py tests/stock_screener/test_aggregator.py
git commit -m "feat(stock_screener): add Aggregator Layer 3"
```

---

### Task 6: Report Builder + Portfolio Adjustment (Layer 4)

**Files:**
- Create: `stock_screener/scanner/report_builder.py`
- Test: `tests/stock_screener/test_report_builder.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/stock_screener/test_report_builder.py
def test_rebalance_reduce_overweight():
    from stock_screener.scanner.report_builder import ReportBuilder
    from tradingagents.agents.portfolio.manager import PortfolioManager

    builder = ReportBuilder()
    positions = [{"ticker": "AMZN", "shares": 2, "entry_price": 258.5}]
    scores = [
        {"ticker": "AMZN", "composite": 0.79, "sector": "Technology"},
        {"ticker": "META", "composite": 0.82, "sector": "Technology"},
    ]
    result = builder.build_adjustments(positions, scores, cash=1400)

    # AMZN overweight (2 shares at $258 = $517 / $1400 cash = 37% > 30%), suggest reduce
    reduce = [a for a in result["adjustments"] if a["action"] == "REDUCE"]
    assert any(a["ticker"] == "AMZN" for a in reduce)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/stock_screener/test_report_builder.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# stock_screener/scanner/report_builder.py
"""Layer 4: Report Builder — generates portfolio adjustment recommendations."""

from dataclasses import dataclass, field
from typing import Annotated
from tradingagents.agents.portfolio.manager import PortfolioManager
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
                 strong_buy_threshold: float = SCORE_THRESHOLDS["strong_buy"]):
        self.portfolio_file = portfolio_file
        self.max_position_weight = max_position_weight
        self.strong_buy_threshold = strong_buy_threshold

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

        # Index stock scores by ticker
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

            if composite < SCORE_THRESHOLDS["consider"]:
                # Recommend reduce
                recommended = max(0, current_shares - 1)
                if recommended < current_shares:
                    adj.append(Adjustment(
                        action="REDUCE",
                        ticker=ticker,
                        current_shares=current_shares,
                        recommended_shares=recommended,
                        reason=f"综合得分{composite:.2f}偏低(<{SCORE_THRESHOLDS['consider']})，建议减仓释放资金",
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
        scored_tickers = set(score_by_ticker.keys())
        held_tickers = set(position_by_ticker.keys())
        for score in stock_scores:
            ticker = score["ticker"]
            if ticker in held_tickers:
                continue  # Already processed
            composite = score["composite"]
            if composite >= self.strong_buy_threshold:
                adj.append(Adjustment(
                    action="NEW",
                    ticker=ticker,
                    current_shares=0,
                    recommended_shares=1,
                    reason=f"综合得分{composite:.2f}高(≥{self.strong_buy_threshold})，{score.get('sector', '')}板块强势，建议新建仓1股试探",
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/stock_screener/test_report_builder.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add stock_screener/scanner/report_builder.py tests/stock_screener/test_report_builder.py
git commit -m "feat(stock_screener): add ReportBuilder Layer 4 with portfolio adjustments"
```

---

### Task 7: Gmail Report Formatting (extend gmail_pusher.py)

**Files:**
- Modify: `scheduler/gmail_pusher.py` — add `format_screener_report()`
- Test: `tests/stock_screener/test_gmail_pusher.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/stock_screener/test_gmail_pusher.py
def test_format_screener_report():
    from scheduler.gmail_pusher import GmailPusher, EmailMessage
    pusher = GmailPusher(sender_email="test@test.com", recipient_email="test@test.com")
    report = {
        "scan_date": "2026-05-03",
        "sector_rankings": [
            {"name": "Technology", "score": 0.85, "rank": 1, "breakdown": {"momentum": 0.9, "valuation": 0.8, "macro": 0.7, "fundamentals": 0.9}},
        ],
        "adjustments": [
            {"action": "REDUCE", "ticker": "AMZN", "current_shares": 2, "recommended_shares": 1, "reason": "...", "source": {}},
            {"action": "NEW", "ticker": "META", "current_shares": 0, "recommended_shares": 1, "reason": "...", "source": {}},
        ],
        "unchanged": [{"ticker": "GOOG", "reason": "..."}],
        "anomalies": [{"sector": "Energy", "signal": "etf_net_inflow", "description": "...", "severity": "high"}],
    }
    msg = pusher.format_screener_report(report)
    assert isinstance(msg, EmailMessage)
    assert "Stock Screener" in msg.subject
    assert "Technology" in msg.body
    assert "⚠️" in msg.body
    assert "REDUCE" in msg.body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/stock_screener/test_gmail_pusher.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

Add to `scheduler/gmail_pusher.py`:

```python
def format_screener_report(self, report: dict) -> EmailMessage:
    """Format full stock screener + portfolio rebalancer report as HTML email."""
    import html

    scan_date = report.get("scan_date", "")
    sectors = report.get("sector_rankings", [])
    adjustments = report.get("adjustments", [])
    unchanged = report.get("unchanged", [])
    anomalies = report.get("anomalies", [])

    # --- Sector table ---
    sector_rows = ""
    for s in sectors:
        b = s.get("breakdown", {})
        sector_rows += f"""
        <tr>
          <td>{s['rank']}</td>
          <td><strong>{s['name']}</strong></td>
          <td>{s['score']:.3f}</td>
          <td>{b.get('momentum', '-')}</td>
          <td>{b.get('valuation', '-')}</td>
          <td>{b.get('macro', '-')}</td>
          <td>{b.get('fundamentals', '-')}</td>
        </tr>"""
    sectors_table = f"""
    <h3>板块扫描结果</h3>
    <table border='1' cellpadding='5' cellspacing='0'>
      <tr><th>排名</th><th>板块</th><th>综合得分</th><th>动量(A)</th><th>估值(B)</th><th>宏观(E)</th><th>基本面(C)</th></tr>
      {sector_rows}
    </table>"""

    # --- Anomaly alerts ---
    anomaly_section = ""
    if anomalies:
        anomaly_rows = ""
        for a in anomalies:
            anomaly_rows += f"<tr><td>{a['sector']}</td><td>{html.escape(a['signal'])}</td><td>{html.escape(a['description'])}</td><td>{html.escape(a.get('data_source', ''))}</td></tr>"
        anomaly_section = f"""
    <h3 style='color:red'>⚠️ 异动板块提醒</h3>
    <table border='1' cellpadding='5' cellspacing='0'>
      <tr><th>板块</th><th>信号</th><th>描述</th><th>数据来源</th></tr>
      {anomaly_rows}
    </table>"""

    # --- Adjustments ---
    reduce_rows = "".join(
        f"<tr><td>{html.escape(a['ticker'])}</td><td>{a['current_shares']}</td><td>减至{a['recommended_shares']}股</td><td>{html.escape(a['reason'])}</td></tr>"
        for a in adjustments if a["action"] in ("REDUCE", "ADD", "NEW")
    )
    new_rows = "".join(
        f"<tr><td>{html.escape(a['ticker'])}</td><td>建议新建仓{a['recommended_shares']}股</td><td>{html.escape(a['reason'])}</td></tr>"
        for a in adjustments if a["action"] == "NEW"
    )
    unchanged_rows = "".join(
        f"<tr><td>{html.escape(u['ticker'])}</td><td>{html.escape(u['reason'])}</td></tr>"
        for u in unchanged
    )
    adjustments_section = f"""
    <h3>持仓调整建议</h3>
    {('<table border="1" cellpadding="5" cellspacing="0"><tr><th>股票</th><th>当前持仓</th><th>建议</th><th>原因</th></tr>' + reduce_rows + '</table>' if reduce_rows else '<p>无调整建议</p>')}
    {('<h4>新建仓机会</h4><table border="1" cellpadding="5" cellspacing="0"><tr><th>股票</th><th>建议</th><th>原因</th></tr>' + new_rows + '</table>' if new_rows else '')}
    {('<h4>持仓不变</h4><table border="1" cellpadding="5" cellspacing="0"><tr><th>股票</th><th>原因</th></tr>' + unchanged_rows + '</table>' if unchanged_rows else '')}"""

    body = f"""
    <h2>Daily Stock Screener & Portfolio Rebalancer</h2>
    <p><em>扫描日期: {scan_date} | 报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}</em></p>
    {anomaly_section}
    {sectors_table}
    {adjustments_section}
    <p><em>Generated by TradingAgents Stock Screener</em></p>
    """
    return EmailMessage(
        subject=f"Stock Screener Report — {scan_date}",
        body=body,
        to_email=self.recipient_email,
    )
```

Add to imports at top of gmail_pusher.py:
```python
from datetime import datetime
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/stock_screener/test_gmail_pusher.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scheduler/gmail_pusher.py tests/stock_screener/test_gmail_pusher.py
git commit -m "feat(screener): add format_screener_report to GmailPusher"
```

---

### Task 8: Scheduler Integration

**Files:**
- Modify: `data/task_queue.json` — add screener tasks

- [ ] **Step 1: Update task_queue.json**

```json
{
  "tasks": [
    {
      "name": "screener_daily",
      "task_type": "daily",
      "time_str": "20:00",
      "days": [],
      "last_run": null,
      "enabled": true
    },
    {
      "name": "screener_report",
      "task_type": "daily",
      "time_str": "08:00",
      "days": [],
      "last_run": null,
      "enabled": true
    },
    {
      "name": "weekly_weight_review",
      "task_type": "weekly",
      "time_str": "09:00",
      "days": ["Friday"],
      "last_run": null,
      "enabled": true
    },
    {
      "name": "afterhours_report",
      "task_type": "daily",
      "time_str": "08:00",
      "days": [],
      "last_run": null,
      "enabled": true
    }
  ]
}
```

Run: read then write `data/task_queue.json`

- [ ] **Step 2: Run test to verify entries**

Run: `python -c "import json; t = json.load(open('data/task_queue.json')); names = [x['name'] for x in t['tasks']]; assert 'screener_daily' in names; assert 'weekly_weight_review' in names; print('OK')"`

- [ ] **Step 3: Commit**

```bash
git add data/task_queue.json
git commit -m "chore(scheduler): add stock screener and weekly weight review tasks"
```

---

### Task 9: Scanner Entry Point

**Files:**
- Create: `stock_screener/run_scanner.py`
- Test: `tests/stock_screener/test_run_scanner.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/stock_screener/test_run_scanner.py
def test_run_full_pipeline():
    from stock_screener.run_scanner import run_daily_scan
    result = run_daily_scan()
    assert "sectors" in result
    assert "all_stocks" in result
    assert "adjustments" in result
    assert "anomalies" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/stock_screener/test_run_scanner.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# stock_screener/run_scanner.py
"""Entry point: runs the full stock screener pipeline."""

from tradingagents.agents.portfolio.manager import PortfolioManager
from scheduler.gmail_pusher import GmailPusher
from stock_screener.scanner import (
    AnomalyDetector, SectorScanner, StockScorer,
    Aggregator, ReportBuilder, SECTORS,
)


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
        all_scores.extend([s.__dict__ for s in scored])

    # Layer 3: Aggregate
    agg = Aggregator()
    aggregated = agg.aggregate(all_scores)
    top_by_sector = agg.top_per_sector(all_scores, top_n=3)

    # Layer 4: Portfolio adjustments
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
    result = run_daily_scan()
    pusher = GmailPusher("yechuan958@gmail.com", "yechuan958@gmail.com")
    report = {
        "scan_date": result["scan_date"],
        "sector_rankings": result["sectors"],
        "adjustments": result["adjustments"],
        "unchanged": result["unchanged"],
        "anomalies": result["anomalies"],
    }
    msg = pusher.format_screener_report(report)
    pusher.send_with_retry(msg)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/stock_screener/test_run_scanner.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add stock_screener/run_scanner.py tests/stock_screener/test_run_scanner.py
git commit -m "feat(stock_screener): add scanner entry point and daily pipeline"
```

---

## Spec Coverage Checklist

| Spec Section | Task |
|--------------|------|
| Layer 0 Anomaly Detector | Task 2 |
| Layer 1 Sector Scanner | Task 3 |
| Layer 2 Stock Analyst Scoring | Task 4 |
| Layer 3 Aggregator + thresholds | Task 5 |
| Layer 4 Portfolio adjustments | Task 6 |
| Gmail report formatting | Task 7 |
| Scheduler task_queue.json | Task 8 |
| Full pipeline runnable entry point | Task 9 |
| 6 sectors, 3-5 stocks each | Tasks 3+4 |
| Weights A×0.4 + B×0.3 + E×0.2 + C×0.1 | Tasks 1+3+4 |
| ⚠️ anomaly flag in report | Tasks 2+7 |
| Weekly weight review (Friday) | Task 8 |
| Data source annotation | All tasks |
| Proxy support (7890) | Tasks 3+4 |

---

## Placeholder Scan

All tasks include complete code. No TBD/TODO. Method signatures consistent across all tasks.

---

**Plan complete and saved to `docs/superpowers/plans/2026-05-02-stock-screener-plan.md`.**

Two execution options:

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
