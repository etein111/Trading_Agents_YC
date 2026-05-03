# Report Database & Web Viewer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store all generated reports in SQLite and provide a Streamlit web interface for browsing/searching historical reports.

**Architecture:** A `ReportDB` class wraps SQLite operations. Each report generation callback saves to DB before sending email. Streamlit app reads from DB and renders an interactive viewer.

**Tech Stack:** Python, SQLite (stdlib), Streamlit.

---

## Task 1: Create ReportDB class

**Files:**
- Create: `scheduler/report_db.py`
- Test: `tests/scheduler/test_report_db.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/scheduler/test_report_db.py
import os, tempfile
from scheduler.report_db import ReportDB

def test_save_and_retrieve_screener_report():
    db = ReportDB(db_path=":memory:")
    meta = {
        "report_type": "screener",
        "scan_date": "2026-05-03",
        "subject": "[TradingAgents] Stock Screener — 2026-05-03",
        "body_html": "<h1>Test Report</h1>",
        "status": "pending",
    }
    stocks = [
        {
            "ticker": "AMZN",
            "sector": "Technology",
            "composite_score": 0.847,
            "rating": "Buy",
            "market_summary": "技术面 RSI 78.1 超买",
            "market_chart_data": {"rsi": 78.1, "sma_20": 245.3},
            "sentiment_summary": "社交情绪偏多",
            "sentiment_chart_data": {"sentiment_score": 0.72},
            "news_summary": "本周行业利好",
            "news_chart_data": {"news_count": 12},
            "fundamentals_summary": "PE 28.4 低于行业均值",
            "fundamentals_chart_data": {"pe_ratio": 28.4},
            "investment_plan_summary": "牛熊盘算要点",
            "trader_plan_summary": "入场价$245",
            "final_decision_summary": "评级 Buy",
        }
    ]
    sectors = [
        {"sector_name": "Technology", "rank": 1, "score": 0.823, "momentum": 0.9, "valuation": 0.7, "macro_score": 0.8, "fundamentals": 0.6}
    ]
    report_id = db.save_screener_report(meta, stocks, sectors)
    assert report_id == 1

    report = db.get_report(report_id)
    assert report["report_type"] == "screener"
    assert report["scan_date"] == "2026-05-03"

    stocks_returned = db.get_stocks_for_report(report_id)
    assert len(stocks_returned) == 1
    assert stocks_returned[0]["ticker"] == "AMZN"
    assert stocks_returned[0]["market_summary"] == "技术面 RSI 78.1 超买"

def test_update_status():
    db = ReportDB(db_path=":memory:")
    report_id = db.save_screener_report(
        {"report_type": "screener", "scan_date": "2026-05-03", "subject": "Test", "body_html": "<p>Test</p>", "status": "pending"},
        [], []
    )
    db.update_status(report_id, "sent")
    report = db.get_report(report_id)
    assert report["status"] == "sent"

def test_list_reports_filtered():
    db = ReportDB(db_path=":memory:")
    db.save_screener_report(
        {"report_type": "screener", "scan_date": "2026-05-03", "subject": "S1", "body_html": "<p>1</p>", "status": "sent"},
        [], []
    )
    db.save_screener_report(
        {"report_type": "afterhours", "scan_date": "2026-05-03", "subject": "A1", "body_html": "<p>2</p>", "status": "sent"},
        [], []
    )
    reports = db.list_reports(report_type="screener")
    assert len(reports) == 1
    assert reports[0]["subject"] == "S1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/scheduler/test_report_db.py -v`
Expected: FAIL — `import error: No module named 'scheduler.report_db'`

- [ ] **Step 3: Write ReportDB class**

`scheduler/report_db.py`:

```python
"""SQLite storage for all TradingAgents reports."""

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


def _json_dumps(val) -> str:
    if val is None:
        return None
    if isinstance(val, dict):
        return json.dumps(val, ensure_ascii=False)
    return val


def _json_loads(val) -> any:
    if val is None:
        return None
    if isinstance(val, str):
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            return None
    return val


class ReportDB:
    _CREATE_TABLES = """
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_type TEXT NOT NULL,
        scan_date TEXT NOT NULL,
        generated_at TEXT NOT NULL,
        subject TEXT,
        status TEXT DEFAULT 'pending',
        body_html TEXT
    );
    CREATE TABLE IF NOT EXISTS stock_analysis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL REFERENCES reports(id),
        ticker TEXT NOT NULL,
        sector TEXT,
        composite_score REAL,
        rating TEXT,
        market_summary TEXT,
        market_chart_data TEXT,
        sentiment_summary TEXT,
        sentiment_chart_data TEXT,
        news_summary TEXT,
        news_chart_data TEXT,
        fundamentals_summary TEXT,
        fundamentals_chart_data TEXT,
        investment_plan_summary TEXT,
        trader_plan_summary TEXT,
        final_decision_summary TEXT,
        raw_reports TEXT
    );
    CREATE TABLE IF NOT EXISTS sector_rankings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL REFERENCES reports(id),
        sector_name TEXT NOT NULL,
        rank INTEGER,
        score REAL,
        momentum REAL,
        valuation REAL,
        macro_score REAL,
        fundamentals REAL
    );
    CREATE TABLE IF NOT EXISTS portfolio_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL REFERENCES reports(id),
        ticker TEXT,
        shares INTEGER,
        entry_price REAL,
        broker TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_reports_type_date ON reports(report_type, scan_date);
    CREATE INDEX IF NOT EXISTS idx_stock_analysis_ticker ON stock_analysis(ticker);
    CREATE INDEX IF NOT EXISTS idx_stock_analysis_report ON stock_analysis(report_id);
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = os.path.join(
                Path(__file__).parent.parent, "data", "reports.db"
            )
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(self._CREATE_TABLES)

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        return dict(row)

    # ── Screener report ───────────────────────────────────────────────────────

    def save_screener_report(
        self,
        meta: dict,
        stocks: list[dict],
        sectors: list[dict],
    ) -> int:
        """Save a screener deep report. Returns report_id."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO reports (report_type, scan_date, generated_at, subject, status, body_html)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    meta["report_type"],
                    meta["scan_date"],
                    datetime.now().isoformat(),
                    meta.get("subject", ""),
                    meta.get("status", "pending"),
                    meta.get("body_html", ""),
                ),
            )
            report_id = cur.lastrowid

            for s in stocks:
                cur.execute(
                    """INSERT INTO stock_analysis
                       (report_id, ticker, sector, composite_score, rating,
                        market_summary, market_chart_data, sentiment_summary, sentiment_chart_data,
                        news_summary, news_chart_data, fundamentals_summary, fundamentals_chart_data,
                        investment_plan_summary, trader_plan_summary, final_decision_summary, raw_reports)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        report_id,
                        s.get("ticker", ""),
                        s.get("sector", ""),
                        s.get("composite_score"),
                        s.get("rating", ""),
                        s.get("market_summary", ""),
                        _json_dumps(s.get("market_chart_data", {})),
                        s.get("sentiment_summary", ""),
                        _json_dumps(s.get("sentiment_chart_data", {})),
                        s.get("news_summary", ""),
                        _json_dumps(s.get("news_chart_data", {})),
                        s.get("fundamentals_summary", ""),
                        _json_dumps(s.get("fundamentals_chart_data", {})),
                        s.get("investment_plan_summary", ""),
                        s.get("trader_plan_summary", ""),
                        s.get("final_decision_summary", ""),
                        _json_dumps(s.get("raw_reports", {})),
                    ),
                )

            for sec in sectors:
                cur.execute(
                    """INSERT INTO sector_rankings
                       (report_id, sector_name, rank, score, momentum, valuation, macro_score, fundamentals)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        report_id,
                        sec.get("sector_name", ""),
                        sec.get("rank"),
                        sec.get("score"),
                        sec.get("momentum"),
                        sec.get("valuation"),
                        sec.get("macro_score"),
                        sec.get("fundamentals"),
                    ),
                )
            conn.commit()
            return report_id

    def save_afterhours_report(
        self,
        meta: dict,
        positions: list[dict],
        analysis: str = "",
    ) -> int:
        """Save an afterhours report."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO reports (report_type, scan_date, generated_at, subject, status, body_html)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    meta["report_type"],
                    meta["scan_date"],
                    datetime.now().isoformat(),
                    meta.get("subject", ""),
                    meta.get("status", "pending"),
                    meta.get("body_html", ""),
                ),
            )
            report_id = cur.lastrowid
            for p in positions:
                cur.execute(
                    """INSERT INTO portfolio_snapshots (report_id, ticker, shares, entry_price, broker)
                       VALUES (?, ?, ?, ?, ?)""",
                    (report_id, p.get("ticker", ""), p.get("shares", 0),
                     p.get("entry_price", 0), p.get("broker", "")),
                )
            conn.commit()
            return report_id

    def save_weekly_report(self, meta: dict, positions: list[dict],
                            gain_loss: float, portfolio_value: float) -> int:
        """Save a weekly report."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO reports (report_type, scan_date, generated_at, subject, status, body_html)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    meta["report_type"],
                    meta["scan_date"],
                    datetime.now().isoformat(),
                    meta.get("subject", ""),
                    meta.get("status", "pending"),
                    meta.get("body_html", ""),
                ),
            )
            report_id = cur.lastrowid
            for p in positions:
                cur.execute(
                    """INSERT INTO portfolio_snapshots (report_id, ticker, shares, entry_price, broker)
                       VALUES (?, ?, ?, ?, ?)""",
                    (report_id, p.get("ticker", ""), p.get("shares", 0),
                     p.get("entry_price", 0), p.get("broker", "")),
                )
            conn.commit()
            return report_id

    def update_status(self, report_id: int, status: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE reports SET status = ? WHERE id = ?",
                (status, report_id),
            )
            conn.commit()

    # ── Queries ────────────────────────────────────────────────────────────────

    def get_report(self, report_id: int) -> Optional[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM reports WHERE id = ?", (report_id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def get_stocks_for_report(self, report_id: int) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM stock_analysis WHERE report_id = ?",
                (report_id,),
            ).fetchall()
            result = []
            for row in rows:
                d = dict(row)
                # parse JSON fields
                for key in ("market_chart_data", "sentiment_chart_data",
                            "news_chart_data", "fundamentals_chart_data", "raw_reports"):
                    d[key] = _json_loads(d.get(key))
                result.append(d)
            return result

    def list_reports(
        self,
        report_type: Optional[str] = None,
        scan_date: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM reports WHERE 1=1"
            params = []
            if report_type:
                query += " AND report_type = ?"
                params.append(report_type)
            if scan_date:
                query += " AND scan_date = ?"
                params.append(scan_date)
            query += " ORDER BY generated_at DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_sector_rankings(self, report_id: int) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM sector_rankings WHERE report_id = ? ORDER BY rank",
                (report_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_portfolio_snapshots(self, report_id: int) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM portfolio_snapshots WHERE report_id = ?",
                (report_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def search_by_ticker(self, ticker: str, limit: int = 20) -> list[dict]:
        """Return reports that contain a specific ticker in stock_analysis."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT DISTINCT r.* FROM reports r
                   JOIN stock_analysis sa ON sa.report_id = r.id
                   WHERE sa.ticker = ?
                   ORDER BY r.generated_at DESC LIMIT ?""",
                (ticker.upper(), limit),
            ).fetchall()
            return [dict(r) for r in rows]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/scheduler/test_report_db.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scheduler/report_db.py tests/scheduler/test_report_db.py
git commit -m "feat(scheduler): add ReportDB for SQLite report storage"
```

---

## Task 2: Integrate ReportDB into run_scanner.py and tasks.py

**Files:**
- Modify: `stock_screener/run_scanner.py`
- Modify: `scheduler/tasks.py`

### run_scanner.py changes

Find `send_daily_report()` in `stock_screener/run_scanner.py`. After the line `msg = pusher.format_deep_screener_report(report)`, before `pusher.send_with_retry(msg)`, add:

```python
from scheduler.report_db import ReportDB

db = ReportDB()
sectors_data = [{"sector_name": s["name"], "rank": s["rank"],
                "score": s["score"],
                "momentum": s.get("breakdown", {}).get("momentum"),
                "valuation": s.get("breakdown", {}).get("valuation"),
                "macro_score": s.get("breakdown", {}).get("macro"),
                "fundamentals": s.get("breakdown", {}).get("fundamentals")}
               for s in result["sectors"]]

report_id = db.save_screener_report(
    meta={
        "report_type": "screener",
        "scan_date": result["scan_date"],
        "subject": f"[TradingAgents] Stock Screener — {result['scan_date']}",
        "body_html": msg.body,
        "status": "pending",
    },
    stocks=[{**s.__dict__} for s in deep_results],
    sectors=sectors_data,
)

# Try to send; update status on success/failure
if pusher.send_with_retry(msg):
    db.update_status(report_id, "sent")
else:
    db.update_status(report_id, "failed")
```

### tasks.py changes

In each callback function (`afterhours_report_callback`, `weekly_weight_review_callback`, `screener_daily_callback`), after the scan/analysis is done and before `pusher.send_with_retry(msg)`:

```python
from scheduler.report_db import ReportDB
db = ReportDB()

# For afterhours_report_callback:
report_id = db.save_afterhours_report(
    meta={"report_type": "afterhours", "scan_date": report.get("date", ""),
          "subject": msg.subject, "body_html": msg.body, "status": "pending"},
    positions=report.get("positions", []),
    analysis=report.get("analysis", ""),
)
if pusher.send_with_retry(msg):
    db.update_status(report_id, "sent")
else:
    db.update_status(report_id, "failed")
```

For `weekly_weight_review_callback`, use `db.save_weekly_report(...)`.

- [ ] **Step 1: Modify run_scanner.py**

Read the current `stock_screener/run_scanner.py` and add the DB save + update flow as described.

- [ ] **Step 2: Modify tasks.py**

Read the current `scheduler/tasks.py` and add DB save to `afterhours_report_callback` and `weekly_weight_review_callback`.

- [ ] **Step 3: Verify syntax**

Run: `python -c "from scheduler.report_db import ReportDB; from stock_screener.run_scanner import send_daily_report; from scheduler.tasks import afterhours_report_callback; print('OK')"`

- [ ] **Step 4: Commit**

```bash
git add stock_screener/run_scanner.py scheduler/tasks.py
git commit -m "feat: persist reports to SQLite before email sending"
```

---

## Task 3: Create Streamlit web viewer

**Files:**
- Create: `scripts/report_viewer.py`
- No new test (manual verification)

### scripts/report_viewer.py

```python
"""Streamlit web interface for browsing historical TradingAgents reports."""

import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scheduler.report_db import ReportDB
from scheduler.gmail_pusher import GmailPusher


st.set_page_config(page_title="TradingAgents Report Viewer", layout="wide")

st.title("TradingAgents Report Viewer")

# Sidebar filters
st.sidebar.header("Filters")
report_type = st.sidebar.selectbox(
    "Report Type",
    options=["all", "screener", "afterhours", "premarket", "weekly"],
    index=0,
)
date_from = st.sidebar.text_input("From Date (YYYY-MM-DD)", value="")
date_to = st.sidebar.text_input("To Date (YYYY-MM-DD)", value="")
ticker_search = st.sidebar.text_input("Ticker Search (e.g. AMZN)", value="")

# Build query
rtype = None if report_type == "all" else report_type
db = ReportDB()

if ticker_search:
    reports = db.search_by_ticker(ticker_search.upper())
else:
    reports = db.list_reports(report_type=rtype, limit=100)

# Filter by date range
if date_from:
    reports = [r for r in reports if r["scan_date"] >= date_from]
if date_to:
    reports = [r for r in reports if r["scan_date"] <= date_to]

st.write(f"Found {len(reports)} report(s)")

TYPE_LABELS = {
    "screener": "Screener",
    "afterhours": "Afterhours",
    "premarket": "Pre-market",
    "weekly": "Weekly",
}

STATUS_EMOJI = {"sent": "✅", "failed": "❌", "pending": "⏳"}

for report in reports:
    with st.container():
        col1, col2 = st.columns([5, 1])
        with col1:
            t = TYPE_LABELS.get(report["report_type"], report["report_type"])
            status = STATUS_EMOJI.get(report["status"], "❓")
            st.markdown(
                f"**{report['scan_date']}** — {t} Report {status} — {report.get('subject', '')}"
            )
        with col2:
            if st.button(f"Re-send", key=f"send_{report['id']}"):
                pusher = GmailPusher("yechuan958@gmail.com", "yechuan958@gmail.com")
                msg_body = report.get("body_html", "")
                from scheduler.gmail_pusher import EmailMessage
                msg = EmailMessage(
                    subject=report.get("subject", ""),
                    body=msg_body,
                    to_email="yechuan958@gmail.com",
                )
                if pusher.send_with_retry(msg):
                    db.update_status(report["id"], "sent")
                    st.success("Email re-sent!")
                else:
                    st.error("Failed to send email.")

        # Show stock summaries if screener report
        if report["report_type"] == "screener":
            stocks = db.get_stocks_for_report(report["id"])
            if stocks:
                data = []
                for s in stocks:
                    data.append({
                        "Ticker": s["ticker"],
                        "Sector": s.get("sector", ""),
                        "Score": f"{s.get('composite_score', 0):.3f}",
                        "Rating": s.get("rating", ""),
                        "Market Summary": s.get("market_summary", "")[:80] + "...",
                        "Fundamentals Summary": s.get("fundamentals_summary", "")[:80] + "...",
                    })
                st.table(data)

        # Show sectors if available
        sectors = db.get_sector_rankings(report["id"])
        if sectors:
            sec_data = [{"Rank": s["rank"], "Sector": s["sector_name"],
                         "Score": f"{s['score']:.3f}",
                         "Momentum": f"{s.get('momentum', 0):.3f}",
                         "Valuation": f"{s.get('valuation', 0):.3f}"}
                        for s in sectors]
            st.table(sec_data)

        st.markdown("---")
```

- [ ] **Step 1: Create scripts/report_viewer.py with the code above**

- [ ] **Step 2: Verify it runs**

Run: `streamlit run scripts/report_viewer.py --server.port 8501`
Navigate to http://localhost:8501

- [ ] **Step 3: Commit**

```bash
git add scripts/report_viewer.py
git commit -m "feat: add Streamlit web viewer for historical reports"
```

---

## Task 4: End-to-end test

- [ ] **Step 1: Generate a screener report** (or reuse existing DB if populated)

```bash
python -c "
from scheduler.report_db import ReportDB
db = ReportDB(':memory:')
# quick smoke test
r = db.save_screener_report(
    {'report_type': 'screener', 'scan_date': '2026-05-03',
     'subject': 'Test', 'body_html': '<p>Test</p>', 'status': 'pending'},
    [{'ticker': 'AMZN', 'sector': 'Tech', 'composite_score': 0.8,
      'rating': 'Buy', 'market_summary': '技术面 RSI 78.1',
      'market_chart_data': {'rsi': 78.1}, 'sentiment_summary': '',
      'sentiment_chart_data': {}, 'news_summary': '', 'news_chart_data': {},
      'fundamentals_summary': '', 'fundamentals_chart_data': {},
      'investment_plan_summary': '', 'trader_plan_summary': '',
      'final_decision_summary': ''}],
    [{'sector_name': 'Technology', 'rank': 1, 'score': 0.823,
      'momentum': 0.9, 'valuation': 0.7, 'macro_score': 0.8, 'fundamentals': 0.6}]
)
print('Saved report_id:', r)
"
```

Expected: `Saved report_id: 1`

- [ ] **Step 2: Start Streamlit viewer and confirm it loads**

```bash
streamlit run scripts/report_viewer.py --server.port 8501
```

- [ ] **Step 3: Commit final state**

```bash
git add -A
git commit -m "feat: complete report database storage and Streamlit web viewer"
git push
```
