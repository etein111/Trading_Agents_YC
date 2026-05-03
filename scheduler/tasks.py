"""Scheduler task callbacks — wires task names to actual implementations."""

import os
import threading
from pathlib import Path
from dotenv import load_dotenv

# Load .env file for all callbacks
load_dotenv(Path(__file__).parent.parent / ".env")

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


def afterhours_report_callback():
    """Send afterhours report email at 20:00 (market close)."""
    result = run_daily_scan()

    # Build afterhours positions from PortfolioManager if available
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
    # Use top movers from scan as "afterhours analysis"
    top_movers = [
        f"{s['ticker']} ({s.get('composite', 0):.3f})"
        for s in result["all_stocks"][:5]
    ]
    msg = pusher.format_afterhours_report({
        "date": __import__("datetime").datetime.now().strftime("%Y-%m-%d"),
        "positions": positions,
        "analysis": f"Top movers today: {', '.join(top_movers)}. "
                    f"Sector leaders: {[s['name'] for s in result['sectors'][:3]]}",
    })
    pusher.send_with_retry(msg)


def weekly_weight_review_callback():
    """Send weekly weight review email on Friday 09:00."""
    result = run_daily_scan()

    # Collect sector weight recommendations from scan
    recommendations = [
        f"Top sector: {s['name']} (score {s['score']:.3f})"
        for s in result["sectors"][:3]
    ]
    adjustments = result.get("adjustments", [])
    if adjustments:
        recommendations.append(
            f"Action items: {len(adjustments)} adjustment(s) recommended"
        )

    pusher = GmailPusher(
        sender_email=os.getenv("GMAIL_EMAIL"),
        recipient_email=os.getenv("GMAIL_EMAIL")
    )
    msg = pusher.format_weekly_report({
        "week": __import__("datetime").datetime.now().strftime("%Y-W%W"),
        "portfolio_value": 0,
        "gain_loss": 0,
        "positions": [],
        "recommendations": recommendations,
        "market_outlook": f"Sector rankings: " + " | ".join(
            f"{s['rank']}. {s['name']}({s['score']:.3f})" for s in result["sectors"]
        ),
    })
    pusher.send_with_retry(msg)


TASK_CALLBACKS = {
    "screener_daily": screener_daily_callback,
    "screener_report": screener_report_callback,
    "afterhours_report": afterhours_report_callback,
    "weekly_weight_review": weekly_weight_review_callback,
}
