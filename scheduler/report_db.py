"""SQLite storage for all TradingAgents reports."""

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


def _json_dumps(val):
    if val is None:
        return None
    if isinstance(val, dict):
        return json.dumps(val, ensure_ascii=False)
    return val


def _json_loads(val):
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

    # ── Screener report ───────────────────────────────────────────────────────

    def _insert_report(self, meta: dict) -> int:
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
            conn.commit()
            return report_id

    def save_screener_report(
        self,
        meta: dict,
        stocks: list[dict],
        sectors: list[dict],
    ) -> int:
        report_id = self._insert_report(meta)
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
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
    ) -> int:
        report_id = self._insert_report(meta)
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            for p in positions:
                cur.execute(
                    """INSERT INTO portfolio_snapshots (report_id, ticker, shares, entry_price, broker)
                       VALUES (?, ?, ?, ?, ?)""",
                    (report_id, p.get("ticker", ""), p.get("shares", 0),
                     p.get("entry_price", 0), p.get("broker", "")),
                )
            conn.commit()
            return report_id

    def save_weekly_report(
        self,
        meta: dict,
        positions: list[dict],
    ) -> int:
        report_id = self._insert_report(meta)
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
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

    # ── Queries ───────────────────────────────────────────────────────────────

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
