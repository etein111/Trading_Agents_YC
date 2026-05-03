import pytest
import os
import tempfile
from scheduler.report_db import ReportDB


def test_save_and_retrieve_screener_report():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        db = ReportDB(db_path=db_path)
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
            {"sector_name": "Technology", "rank": 1, "score": 0.823,
             "momentum": 0.9, "valuation": 0.7, "macro_score": 0.8, "fundamentals": 0.6}
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
        assert stocks_returned[0]["market_chart_data"]["rsi"] == 78.1
    finally:
        os.unlink(db_path)


def test_update_status():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        db = ReportDB(db_path=db_path)
        report_id = db.save_screener_report(
            {"report_type": "screener", "scan_date": "2026-05-03",
             "subject": "Test", "body_html": "<p>Test</p>", "status": "pending"},
            [], []
        )
        db.update_status(report_id, "sent")
        report = db.get_report(report_id)
        assert report["status"] == "sent"
    finally:
        os.unlink(db_path)


def test_list_reports_filtered():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        db = ReportDB(db_path=db_path)
        db.save_screener_report(
            {"report_type": "screener", "scan_date": "2026-05-03",
             "subject": "S1", "body_html": "<p>1</p>", "status": "sent"},
            [], []
        )
        db.save_afterhours_report(
            {"report_type": "afterhours", "scan_date": "2026-05-03",
             "subject": "A1", "body_html": "<p>2</p>", "status": "sent"},
            []
        )
        reports = db.list_reports(report_type="screener")
        assert len(reports) == 1
        assert reports[0]["subject"] == "S1"
    finally:
        os.unlink(db_path)
