# Theme Scanner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增主题扫描功能：输入主题词（如"AI"），系统自动推断子领域、从候选池选股、评分后通过邮件推送。

**Architecture:** ThemeScanner 类负责 LLM 推断子领域 + 选股；复用现有 StockScorer 评分；新增 `send_theme_report()` 整合 GmailPusher + ReportDB；邮件格式复用现有模板。

**Tech Stack:** Python, yfinance, tradingagents LLM client factory, SQLite (ReportDB), Gmail SMTP

---

## File Structure

| File | Action |
|------|--------|
| `stock_screener/scanner/config.py` | Modify — ADD `THEME_CANDIDATE_POOL` |
| `stock_screener/scanner/stock_scorer.py` | Modify — ADD `score_tickers()` method |
| `stock_screener/scanner/theme_scanner.py` | Create — ThemeScanner class |
| `stock_screener/run_scanner.py` | Modify — ADD `run_theme_scan()`, `send_theme_report()` |
| `scheduler/gmail_pusher.py` | Modify — ADD `format_theme_report()` |
| `scheduler/tasks.py` | Modify — ADD `theme_scan` task type |
| `tests/stock_screener/test_theme_scanner.py` | Create — ThemeScanner tests |

---

### Task 1: Add THEME_CANDIDATE_POOL to config.py

**Files:**
- Modify: `stock_screener/scanner/config.py:1-10`

- [ ] **Step 1: Read current config.py**

```python
# Current config.py
SECTORS = {
    "Technology":  {"etf": "XLK", "stocks": ["AMZN", "GOOG", "META", "MSFT", "ORCL"]},
    ...
}
WEIGHTS = {"momentum": 0.4, "valuation": 0.3, "macro": 0.2, "fundamentals": 0.1}
SCORE_THRESHOLDS = {"strong_buy": 0.70, "consider": 0.50}
MAX_POSITION_WEIGHT = 0.30
```

- [ ] **Step 2: Add THEME_CANDIDATE_POOL dict after SECTORS definition**

```python
# Candidate stock pool for theme scanning — LLM picks from here per sub-sector
THEME_CANDIDATE_POOL = {
    "AI芯片": ["NVDA", "AMD", "INTC", "QCOM", "AVGO", "MRVL", "MU", "AMAT"],
    "存储": ["SMCI", "WD", "STX", "NTAP", "PSTG", "NXPI"],
    "电力基础设施": ["XEL", "VST", "CEG", "EXC", "NEE", "DUK", "SO", "D"],
    "数据中心": ["EQIX", "DLR", "AVB", "CONE", "CORR", "AMT", "PLDT"],
    "云计算": ["AMZN", "MSFT", "GOOG", "META", "ORCL", "CRM", "NOW", "WDAY"],
    "网络安全": ["PANW", "CRWD", "ZS", "NET", "AKAM", "FTNT"],
    "量子计算": ["IBM", "IONQ", "RGTI", "QUBT", "HON"],
    "机器人": ["TSLA", "IRBT", "ISRG", "DEST", "KUKA"],
    "新能源车": ["TSLA", "RIVN", "LCID", "NIO", "F", "GM"],
    "半导体设备": ["AMAT", "LRCX", "KLAC", "ASML", "TOVYY"],
    "光通信": ["ACIA", "LITE", "FN", "IIVI", "LRCX"],
    "卫星通信": ["IRDM", "SATL", "GHGS", "AMZN"],
    "生物科技": ["REGN", "MRNA", "VRTX", "BIIB", "MRK"],
    "金融科技": ["COIN", "SQ", "PYPL", "AFRM", "NU"],
    "消费AI": ["SHOP", "U", "AI", "APP", "PATH"],
    "自动驾驶": ["TSLA", "GM", "F", "BIDU", "TOYOY"],
}
```

- [ ] **Step 3: Commit**

```bash
git add stock_screener/scanner/config.py
git commit -m "feat(config): add THEME_CANDIDATE_POOL for theme scanning"
```

---

### Task 2: Add score_tickers() to StockScorer

**Files:**
- Modify: `stock_screener/scanner/stock_scorer.py:65-76`

- [ ] **Step 1: Write failing test**

```python
# tests/stock_screener/test_stock_scorer.py
def test_score_tickers_returns_scored_results():
    from stock_screener.scanner.stock_scorer import StockScorer
    scorer = StockScorer()
    results = scorer.score_tickers(["AMZN", "GOOG"], sector="Technology")
    assert len(results) == 2
    assert all(hasattr(r, "composite") for r in results)
    assert all(r.sector == "Technology" for r in results)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/stock_screener/test_stock_scorer.py::test_score_tickers_returns_scored_results -v
```
Expected: FAIL with "StockScorer does not have score_tickers"

- [ ] **Step 3: Add score_tickers() method to StockScorer class**

```python
def score_tickers(self, tickers: list[str], sector: str = "Unknown") -> list[StockScore]:
    """Score an arbitrary list of tickers (no SECTORS config required)."""
    return [self.score_stock(t) for t in tickers]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/stock_screener/test_stock_scorer.py::test_score_tickers_returns_scored_results -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add stock_screener/scanner/stock_scorer.py tests/stock_screener/test_stock_scorer.py
git commit -m "feat(stock_scorer): add score_tickers() for arbitrary ticker lists"
```

---

### Task 3: Create theme_scanner.py

**Files:**
- Create: `stock_screener/scanner/theme_scanner.py`
- Test: `tests/stock_screener/test_theme_scanner.py`

- [ ] **Step 1: Write failing test**

```python
# tests/stock_screener/test_theme_scanner.py
import pytest
from stock_screener.scanner.theme_scanner import ThemeScanner

def test_deduces_sub_sectors():
    scanner = ThemeScanner()
    subs = scanner._deduce_sub_sectors("AI")
    assert isinstance(subs, list)
    assert len(subs) >= 3

def test_theme_scanner_scan_returns_structure():
    scanner = ThemeScanner()
    result = scanner.scan("AI")
    assert "theme" in result
    assert "sub_sectors" in result
    assert result["theme"] == "AI"
    assert isinstance(result["sub_sectors"], list)

def test_theme_scanner_scan_includes_scores():
    scanner = ThemeScanner()
    result = scanner.scan("AI")
    first_sub = result["sub_sectors"][0]
    assert "sub_sector" in first_sub
    assert "stocks" in first_sub
    assert len(first_sub["stocks"]) >= 1
    assert "composite" in first_sub["stocks"][0]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/stock_screener/test_theme_scanner.py -v
```
Expected: FAIL with "module 'theme_scanner' has no attribute 'ThemeScanner'"

- [ ] **Step 3: Create theme_scanner.py**

```python
"""Theme Scanner — LLM-powered theme decomposition and stock picking."""

import os
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from tradingagents.llm_clients.factory import create_llm_client
from tradingagents.default_config import DEFAULT_CONFIG

from .config import THEME_CANDIDATE_POOL
from .stock_scorer import StockScorer


def _build_llm_client():
    cfg = DEFAULT_CONFIG.copy()
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    deep_model = os.getenv("LLM_DEEP_MODEL", "")
    quick_model = os.getenv("LLM_QUICK_MODEL", "")
    backend_url = os.getenv("BACKEND_URL") or None
    if deep_model:
        cfg["deep_think_llm"] = deep_model
    if quick_model:
        cfg["quick_think_llm"] = quick_model
    cfg["backend_url"] = backend_url
    model = cfg.get("quick_think_llm", "gpt-4o")
    return create_llm_client(provider, model, backend_url)


_SUBSECTOR_PROMPT = """给定主题 "{theme}"，列出 5-8 个最相关的子领域/细分方向。
每个子领域返回一个词或短语（如"AI芯片"、"电力基础设施"）。
只返回子领域名称，每行一个，不要编号，不要解释。"""

_STOCKSEL_PROMPT = """主题是 "{theme}"，子领域是 "{sub_sector}"。
候选股票池（每行一个代码）：
{candidate_pool}

从候选池中选择 3-8 只与该子领域最相关的股票。
只返回股票代码，每行一个，不要编号，不要解释。"""


def _strip_think(text: str) -> str:
    text = re.sub(r'<think>.*?', '', text, flags=re.DOTALL).strip()
    text = re.sub(r'<think>.*', '', text, flags=re.DOTALL).strip()
    return text


class ThemeScanner:
    """Scans stocks by theme using LLM-driven sub-sector decomposition."""

    def __init__(self):
        client = _build_llm_client()
        self._llm = client.get_llm()
        self._scorer = StockScorer()

    def _deduce_sub_sectors(self, theme: str) -> list[str]:
        prompt = _SUBSECTOR_PROMPT.format(theme=theme)
        response = self._llm.invoke(prompt)
        text = _strip_think(response.content if hasattr(response, "content") else str(response))
        subs = [line.strip() for line in text.splitlines() if line.strip()]
        return subs

    def _select_stocks(self, theme: str, sub_sector: str) -> list[str]:
        pool_lines = "\n".join(f"{k}: {','.join(v)}" for k, v in THEME_CANDIDATE_POOL.items())
        prompt = _STOCKSEL_PROMPT.format(
            theme=theme,
            sub_sector=sub_sector,
            candidate_pool=pool_lines,
        )
        response = self._llm.invoke(prompt)
        text = _strip_think(response.content if hasattr(response, "content") else str(response))
        tickers = [line.strip().upper() for line in text.splitlines() if line.strip()]
        return tickers

    def scan(self, theme: str, top_n_per_sector: int = 3) -> dict:
        """Run full theme scan pipeline.

        Returns:
            {
                "theme": str,
                "sub_sectors": [
                    {
                        "sub_sector": str,
                        "stocks": [dict, ...]  # scored stock dicts, sorted by composite desc
                    },
                    ...
                ],
                "scan_date": str,
            }
        """
        sub_sectors = self._deduce_sub_sectors(theme)
        results = []
        for sub in sub_sectors:
            tickers = self._select_stocks(theme, sub)
            if not tickers:
                continue
            scored = self._scorer.score_tickers(tickers, sector=sub)
            scored_dicts = [
                {**s.__dict__, "ticker": s.stock}
                for s in scored
            ]
            scored_dicts.sort(key=lambda x: x["composite"], reverse=True)
            results.append({
                "sub_sector": sub,
                "stocks": scored_dicts[:top_n_per_sector],
            })
        return {
            "theme": theme,
            "sub_sectors": results,
            "scan_date": __import__("datetime").date.today().isoformat(),
        }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/stock_screener/test_theme_scanner.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add stock_screener/scanner/theme_scanner.py tests/stock_screener/test_theme_scanner.py
git commit -m "feat(theme_scanner): add ThemeScanner with LLM-driven sub-sector deduction"
```

---

### Task 4: Add format_theme_report() to gmail_pusher.py

**Files:**
- Modify: `scheduler/gmail_pusher.py`

- [ ] **Step 1: Read gmail_pusher.py end (after format_deep_screener_report)**

Find the end of `format_deep_screener_report` method (around line 622).

- [ ] **Step 2: Add format_theme_report() method**

```python
def format_theme_report(self, report: dict) -> "EmailMessage":
    """Format theme scan report as email.

    report structure from ThemeScanner.scan():
      {
        "theme": str,
        "sub_sectors": [
          {"sub_sector": str, "stocks": [dict, ...]},
          ...
        ],
        "scan_date": str,
      }
    """
    theme = report.get("theme", "")
    scan_date = report.get("scan_date", "")
    sub_sectors = report.get("sub_sectors", [])

    # Build sub-sector table rows
    sector_rows = ""
    for sub in sub_sectors:
        sub_name = html.escape(sub["sub_sector"])
        for stock_data in sub["stocks"]:
            ticker = html.escape(stock_data.get("ticker", ""))
            score = stock_data.get("composite", 0)
            rating = stock_data.get("rating", "-")
            momentum = stock_data.get("scores", {}).get("momentum", "-")
            sector_rows += f"""
        <tr>
          <td style="padding:5px"><strong>{ticker}</strong></td>
          <td style="padding:5px">{sub_name}</td>
          <td style="padding:5px"><strong>{score:.3f}</strong></td>
          <td style="padding:5px">{momentum}</td>
          <td style="padding:5px">{html.escape(rating)}</td>
        </tr>"""

    body = f"""
<div style="font-family:Arial,sans-serif;max-width:950px">
  <h1 style="color:#333">Theme Scan: {html.escape(theme)}</h1>
  <p><em>扫描日期: {scan_date} | 报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}</em></p>

  <h2 style="margin-top:20px">子领域扫描结果</h2>
  <table style="border-collapse:collapse;width:100%" border="1" cellpadding="5" cellspacing="0">
    <tr style="background:{COLOR_HEADER_BG}">
      <th style="padding:5px">股票</th>
      <th style="padding:5px">子领域</th>
      <th style="padding:5px">综合得分</th>
      <th style="padding:5px">动量</th>
      <th style="padding:5px">评级</th>
    </tr>
    {sector_rows}
  </table>

  <p style="margin-top:20px"><em>Generated by TradingAgents Theme Scanner</em></p>
</div>"""

    return EmailMessage(
        subject=f"[TradingAgents] Theme Scan: {theme} — {scan_date}",
        body=body,
        to_email=self.recipient_email,
    )
```

- [ ] **Step 3: Verify syntax**

```bash
cd /d D:/yechuan/work/My_project/TradingAgents && .venv/Scripts/python.exe -c "from scheduler.gmail_pusher import GmailPusher; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add scheduler/gmail_pusher.py
git commit -m "feat(gmail_pusher): add format_theme_report() method"
```

---

### Task 5: Add run_theme_scan() and send_theme_report() to run_scanner.py

**Files:**
- Modify: `stock_screener/run_scanner.py`

- [ ] **Step 1: Read end of run_scanner.py (after send_daily_report)**

- [ ] **Step 2: Add run_theme_scan() and send_theme_report() functions**

```python
def run_theme_scan(theme: str) -> dict:
    """Run theme scan: LLM deduces sub-sectors, picks stocks, scores them."""
    from stock_screener.scanner.theme_scanner import ThemeScanner
    scanner = ThemeScanner()
    return scanner.scan(theme)


def send_theme_report(theme: str):
    """Run theme scan and send email report."""
    if not _has_gmail_pusher:
        raise ImportError("GmailPusher not available")
    result = run_theme_scan(theme)

    portfolio_positions = []
    if _has_portfolio_manager:
        pm = PortfolioManager("data/portfolio.json")
        portfolio_positions = pm.get_positions()

    pusher = GmailPusher("yechuan958@gmail.com", "yechuan958@gmail.com")
    report = {
        "theme": result["theme"],
        "sub_sectors": result["sub_sectors"],
        "scan_date": result["scan_date"],
        "portfolio_positions": portfolio_positions,
    }
    msg = pusher.format_theme_report(report)

    from scheduler.report_db import ReportDB
    db = ReportDB()

    report_id = db.save_screener_report(
        meta={
            "report_type": "theme",
            "scan_date": result["scan_date"],
            "subject": msg.subject,
            "body_html": msg.body,
            "status": "pending",
        },
        stocks=[],  # no deep stocks for theme scans
        sectors=[],  # no sector rankings for theme scans
    )

    if pusher.send_with_retry(msg):
        db.update_status(report_id, "sent")
    else:
        db.update_status(report_id, "failed")
```

- [ ] **Step 3: Verify syntax**

```bash
cd /d D:/yechuan/work/My_project/TradingAgents && .venv/Scripts/python.exe -c "from stock_screener.run_scanner import run_theme_scan, send_theme_report; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add stock_screener/run_scanner.py
git commit -m "feat(run_scanner): add run_theme_scan() and send_theme_report()"
```

---

### Task 6: Add theme_scan task to tasks.py

**Files:**
- Modify: `scheduler/tasks.py`

- [ ] **Step 1: Read tasks.py to find task registration pattern**

```bash
grep -n "def.*task\|screener\|daily_report" scheduler/tasks.py | head -20
```

- [ ] **Step 2: Add theme_scan task**

```python
# In tasks.py, add theme scan task registration
# (exact pattern depends on existing task registration format — adapt to match)
theme_scan_task = {
    "name": "theme_scan",
    "func": lambda: send_theme_report("AI"),  # default theme
    "schedule": "0 20 * * *",  # 20:00 daily, like screener
    "description": "Theme-based stock scan and email report",
}
```

- [ ] **Step 3: Verify syntax**

```bash
cd /d D:/yechuan/work/My_project/TradingAgents && .venv/Scripts/python.exe -c "from scheduler.tasks import *; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add scheduler/tasks.py
git commit -m "feat(tasks): add theme_scan task registration"
```

---

### Task 7: Integration test — run full theme scan with email

- [ ] **Step 1: Run theme scan from project root (with .env credentials)**

```bash
cd /d D:/yechuan/work/My_project/TradingAgents && .venv/Scripts/python.exe -c "
from stock_screener.run_scanner import send_theme_report
send_theme_report('AI')
print('OK')
"
```

Expected: LLM deduces sub-sectors → picks stocks → scores → email sent (or saved to DB if SMTP fails)

- [ ] **Step 2: Verify database entry**

```bash
cd /d D:/yechuan/work/My_project/TradingAgents && .venv/Scripts/python.exe -c "
from scheduler.report_db import ReportDB
db = ReportDB()
reports = db.list_reports(report_type='theme', limit=1)
print(reports)
"
```

- [ ] **Step 3: Commit if all tests pass**

```bash
git add -A && git commit -m "test: add theme scanner integration test"
```

---

## Verification Checklist

1. `pytest tests/stock_screener/test_theme_scanner.py -v` — all PASS
2. `pytest tests/stock_screener/test_stock_scorer.py -v` — all PASS
3. `send_theme_report("AI")` — email generated and sent (or saved to DB)
4. Email contains: sub-sector table with tickers, scores, ratings
5. Report saved to `reports.db` with `report_type="theme"`
