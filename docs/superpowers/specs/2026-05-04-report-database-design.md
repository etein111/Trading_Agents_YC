# Report Database & Web Viewer Design

## Context

Currently, all four report types (screener_report, afterhours_report, premarket_report, weekly_report) are generated and emailed but not stored persistently. If email delivery fails, the report is lost. There is no historical record to query.

Goal: store every generated report in SQLite, and provide a web interface to browse/search historical reports.

---

## Architecture

### Database: SQLite

File location: `data/reports.db`

**Tables:**

```sql
-- Main report metadata + full HTML body
CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_type TEXT NOT NULL,  -- 'screener' | 'afterhours' | 'premarket' | 'weekly'
    scan_date TEXT NOT NULL,   -- YYYY-MM-DD
    generated_at TEXT NOT NULL, -- ISO timestamp
    subject TEXT,
    status TEXT DEFAULT 'sent', -- 'sent' | 'failed' | 'pending'
    body_html TEXT             -- full email HTML body
);

-- Per-stock distilled analysis (for screener deep reports)
CREATE TABLE stock_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL REFERENCES reports(id),
    ticker TEXT NOT NULL,
    sector TEXT,
    composite_score REAL,
    rating TEXT,
    market_summary TEXT,
    market_chart_data TEXT,    -- JSON string
    sentiment_summary TEXT,
    sentiment_chart_data TEXT,
    news_summary TEXT,
    news_chart_data TEXT,
    fundamentals_summary TEXT,
    fundamentals_chart_data TEXT,
    investment_plan_summary TEXT,
    trader_plan_summary TEXT,
    final_decision_summary TEXT,
    raw_reports TEXT            -- JSON of original raw agent texts (for fallback)
);

-- Sector rankings for screener reports
CREATE TABLE sector_rankings (
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

-- Portfolio positions snapshot
CREATE TABLE portfolio_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL REFERENCES reports(id),
    ticker TEXT,
    shares INTEGER,
    entry_price REAL,
    broker TEXT
);
```

**Indexes:**
```sql
CREATE INDEX idx_reports_type_date ON reports(report_type, scan_date);
CREATE INDEX idx_stock_analysis_ticker ON stock_analysis(ticker);
CREATE INDEX idx_stock_analysis_report ON stock_analysis(report_id);
```

### Storage Trigger Points

1. `run_scanner.py` — `send_daily_report()`: after deep analysis completes → save to DB → send email
2. `scheduler/tasks.py` — `afterhours_report_callback()`: save → send
3. `scheduler/tasks.py` — `weekly_weight_review_callback()`: save → send
4. `scheduler/tasks.py` — `screener_daily_callback()`: save → send

Each save captures the full report state (HTML body + structured data). Email sending failure does NOT prevent save — report is stored with `status='sent'` only after confirmed send.

### Web Interface: Streamlit

**File:** `scripts/report_viewer.py`

**Startup:** `streamlit run scripts/report_viewer.py`

**Layout:**

```
┌──────────────────────────────────────────────────────────────┐
│  TradingAgents Report Viewer                                  │
├────────────┬─────────────────────────────────────────────────┤
│ Sidebar:   │  Main content area:                              │
│            │                                                 │
│ Report Type│  [Filter bar: search ticker, date range]         │
│ [All ▼]    │                                                 │
│ ○ Screener │  Report cards (list):                          │
│ ○ Afterhrs │  ┌─────────────────────────────────────────────┐│
│ ○ Weekly   │  │ 2026-05-03  Screener Report    ✅ Sent      ││
│ ○ PreMkt   │  │ 8 stocks · Composite scores + ratings        ││
│            │  └─────────────────────────────────────────────┘│
│ Date Range │  ┌─────────────────────────────────────────────┐│
│ [2026-05-01│  │ 2026-05-02  Afterhours Report   ✅ Sent      ││
│  to 2026-  │  │ Portfolio positions + adjustments           ││
│  05-04]    │  └─────────────────────────────────────────────┘│
│            │                                                 │
│ Ticker     │  [Click card → full report view with HTML]     │
│ Search:    │                                                 │
│ [____]     │                                                 │
└────────────┴─────────────────────────────────────────────────┘
```

**Features:**
- Filter by report type (sidebar checkboxes)
- Date range picker (sidebar)
- Ticker search (filters stock_analysis table)
- Report card list showing: date, type, status, stock count
- Click to expand → renders stored HTML in an embedded frame
- "Re-send email" button per report (re-sends via GmailPusher)
- "Download HTML" button per report

---

## Files to Modify/Create

| File | Action | Purpose |
|------|--------|---------|
| `scheduler/report_db.py` | Create | `ReportDB` class — SQLite CRUD operations |
| `stock_screener/run_scanner.py` | Modify | After deep analysis, call `ReportDB.save_screener_report()` |
| `scheduler/tasks.py` | Modify | After each callback's scan, call `ReportDB.save_*()` before sending |
| `scripts/report_viewer.py` | Create | Streamlit web app |

---

## Data Flow

```
[Report Generation]
    ↓
[ReportDB.save_report(html, meta, stocks, sectors)]
    ↓
[SQLite insert: reports + stock_analysis + sector_rankings]
    ↓
[GmailPusher.send_with_retry()]
    ↓
[Update report.status = 'sent' or 'failed']
```

---

## Key Decisions

1. **One DB file per project** (`data/reports.db`) — not per report type
2. **Raw agent texts stored as JSON** in `stock_analysis.raw_reports` — fallback for re-sending
3. **HTML stored in full** — enables "view original email" feature in web UI
4. **Streamlit over Flask/FastAPI** — simpler, faster to build, no HTML templates needed
5. **Status updated AFTER successful send** — ensures DB reflects actual delivery state

---

## Verification

1. Generate a screener report → check `data/reports.db` has 1 row in `reports` + 8 rows in `stock_analysis`
2. Start Streamlit → browse to historical report → click to expand HTML
3. "Re-send" button → email arrives again
4. Filter by ticker → only shows reports containing that stock