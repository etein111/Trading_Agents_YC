"""Streamlit web interface for browsing historical TradingAgents reports."""

import sys
from pathlib import Path

# Add worktree to sys.path BEFORE any other imports
worktree_root = str(Path(__file__).parent.parent)
if worktree_root not in sys.path:
    sys.path.insert(0, worktree_root)

import streamlit as st

from scheduler.report_db import ReportDB


st.set_page_config(page_title="TradingAgents Report Viewer", layout="wide")

st.title("TradingAgents Report Viewer")

# Sidebar filters
st.sidebar.header("Filters")
report_type = st.sidebar.selectbox(
    "Report Type",
    options=["all", "screener", "theme", "afterhours", "premarket", "weekly"],
    index=0,
)
date_from = st.sidebar.text_input("From Date (YYYY-MM-DD)", value="")
date_to = st.sidebar.text_input("To Date (YYYY-MM-DD)", value="")
ticker_search = st.sidebar.text_input("Ticker Search (e.g. AMZN)", value="")

# Build query
rtype = None if report_type == "all" else report_type
worktree_root = str(Path(__file__).parent.parent / ".claude" / "worktrees" / "email-beautification")
db_path = str(Path(worktree_root) / "data" / "reports.db")
db = ReportDB(db_path)

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
    "theme": "Theme",
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
            pass

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
                        "Market Summary": s.get("market_summary", "")[:80],
                        "Fundamentals Summary": s.get("fundamentals_summary", "")[:80],
                    })
                st.table(data)

        # Show sector recommendations (top N per sector, without deep analysis)
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        sector_recs = conn.execute(
            "SELECT ticker, sector, composite_score, rating FROM sector_stock_recommendations WHERE report_id = ? ORDER BY sector, composite_score DESC",
            (report["id"],)
        ).fetchall()
        conn.close()
        if sector_recs:
            st.markdown("**各板块推荐（无深度分析）**")
            rec_data = [
                {"Ticker": r["ticker"], "Sector": r["sector"],
                 "Score": f"{r['composite_score']:.3f}", "Rating": r["rating"]}
                for r in sector_recs
            ]
            st.table(rec_data)

        # Show sectors if available
        sectors = db.get_sector_rankings(report["id"])
        if sectors:
            sec_data = [
                {"Rank": s["rank"], "Sector": s["sector_name"],
                 "Score": f"{s['score']:.3f}",
                 "Momentum": f"{s.get('momentum', 0):.3f}",
                 "Valuation": f"{s.get('valuation', 0):.3f}"}
                for s in sectors
            ]
            st.table(sec_data)

        # Full report body
        body = report.get("body_html", "")
        if body:
            with st.expander("📄 View Full Report Content"):
                st.markdown(body, unsafe_allow_html=True)

        st.markdown("---")
