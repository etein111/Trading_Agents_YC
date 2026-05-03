"""Scheduler task callbacks — wires task names to actual implementations."""

from stock_screener.run_scanner import run_daily_scan, send_daily_report


def screener_daily_callback():
    """Run daily stock scan (Layer 0-3 pipeline). No email."""
    run_daily_scan()


def screener_report_callback():
    """Run daily scan and send Gmail report (Layer 4)."""
    send_daily_report()


def weekly_weight_review_callback():
    """Weekly weight review — stub for now."""
    # TODO: implement weight review against recent performance
    pass


def afterhours_report_callback():
    """Afterhours report — stub from existing implementation."""
    # Existing afterhours report logic
    pass


TASK_CALLBACKS = {
    "screener_daily": screener_daily_callback,
    "screener_report": screener_report_callback,
    "weekly_weight_review": weekly_weight_review_callback,
    "afterhours_report": afterhours_report_callback,
}