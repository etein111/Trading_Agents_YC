"""Streamlit web interface for browsing historical TradingAgents reports."""

import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scheduler.report_db import ReportDB
from scheduler.gmail_pusher import GmailPusher, EmailMessage


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
                        "Market Summary": s.get("market_summary", "")[:80],
                        "Fundamentals Summary": s.get("fundamentals_summary", "")[:80],
                    })
                st.table(data)

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
