"""Scheduler task callbacks — wires task names to actual implementations."""

import os
import threading
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (4 parents up from scheduler/tasks.py)
_env_path = Path(__file__).parent.parent.parent.parent.parent / ".env"
load_dotenv(_env_path)

from stock_screener.run_scanner import run_daily_scan, send_daily_report
from scheduler.gmail_pusher import GmailPusher


def _run_and_wait(target, *args):
    """Run target in a non-daemon thread and wait for completion."""
    t = threading.Thread(target=target, args=args, daemon=False)
    t.start()
    t.join()


def screener_daily_callback():
    """Run daily stock scan (Layer 0-3 pipeline). No email."""
    run_daily_scan()


def screener_report_callback():
    """Run daily scan and send Gmail report (Layer 4)."""
    _run_and_wait(send_daily_report)


def _build_deep_report(result: dict, top_n: int, report_type: str, scan_date: str) -> tuple:
    """Shared logic for deep analysis: run DEEP_ANALYSIS, build message, save to DB, send email."""
    all_stocks = result["all_stocks"]
    top_tickers = [s["ticker"] for s in all_stocks[:top_n]]
    from stock_screener.scanner.deep_analysis import run_deep_analysis
    from stock_screener.scanner.config import SECTORS
    deep_results = run_deep_analysis(top_tickers, scan_date, SECTORS, top_n=top_n)
    score_map = {s["ticker"]: s["composite"] for s in all_stocks}
    for d in deep_results:
        d.composite_score = score_map.get(d.ticker, 0.0)

    positions = []
    try:
        from tradingagents.agents.portfolio.manager import PortfolioManager
        pm = PortfolioManager("data/portfolio.json")
        positions = pm.get_positions()
    except Exception:
        pass

    pusher = GmailPusher(
        sender_email=os.getenv("GMAIL_EMAIL"),
        recipient_email=os.getenv("GMAIL_EMAIL")
    )
    msg = pusher.format_deep_screener_report({
        "scan_date": scan_date,
        "sector_rankings": result["sectors"],
        "all_stocks": result["all_stocks"],
        "top_by_sector": result["top_by_sector"],
        "adjustments": result["adjustments"],
        "unchanged": result["unchanged"],
        "anomalies": result["anomalies"],
        "portfolio_positions": positions,
        "deep_stocks": [d.__dict__ for d in deep_results],
    }, report_type=report_type)

    from scheduler.report_db import ReportDB
    db = ReportDB()
    sectors_data = [
        {"sector_name": s["name"], "rank": s["rank"],
         "score": s["score"],
         "momentum": s.get("breakdown", {}).get("momentum"),
         "valuation": s.get("breakdown", {}).get("valuation"),
         "macro_score": s.get("breakdown", {}).get("macro"),
         "fundamentals": s.get("breakdown", {}).get("fundamentals")}
        for s in result["sectors"]
    ]
    report_id = db.save_screener_report(
        meta={
            "report_type": report_type,
            "scan_date": scan_date,
            "subject": msg.subject,
            "body_html": msg.body,
            "status": "pending",
        },
        stocks=[{**s.__dict__} for s in deep_results],
        sectors=sectors_data,
    )
    if pusher.send_with_retry(msg):
        db.update_status(report_id, "sent")
    else:
        db.update_status(report_id, "failed")


def afterhours_report_callback():
    """Send afterhours report email at 20:00 (market close)."""
    result = run_daily_scan()
    scan_date = result.get("scan_date") or __import__("datetime").datetime.now().strftime("%Y-%m-%d")
    _build_deep_report(result, top_n=5, report_type="afterhours", scan_date=scan_date)


def weekly_weight_review_callback():
    """Send weekly weight review email on Friday 09:00."""
    result = run_daily_scan()
    week_str = __import__("datetime").datetime.now().strftime("%Y-W%W")
    _build_deep_report(result, top_n=8, report_type="weekly", scan_date=week_str)


TASK_CALLBACKS = {
    "screener_daily": screener_daily_callback,
    "screener_report": screener_report_callback,
    "afterhours_report": afterhours_report_callback,
    "weekly_weight_review": weekly_weight_review_callback,
}
