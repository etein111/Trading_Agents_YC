def test_format_screener_report():
    from scheduler.gmail_pusher import GmailPusher, EmailMessage
    pusher = GmailPusher(sender_email="test@test.com", recipient_email="test@test.com")
    report = {
        "scan_date": "2026-05-03",
        "sector_rankings": [
            {"name": "Technology", "score": 0.85, "rank": 1, "breakdown": {"momentum": 0.9, "valuation": 0.8, "macro": 0.7, "fundamentals": 0.9}},
        ],
        "adjustments": [
            {"action": "REDUCE", "ticker": "AMZN", "current_shares": 2, "recommended_shares": 1, "reason": "...", "source": {}},
            {"action": "NEW", "ticker": "META", "current_shares": 0, "recommended_shares": 1, "reason": "...", "source": {}},
        ],
        "unchanged": [{"ticker": "GOOG", "reason": "..."}],
        "anomalies": [{"sector": "Energy", "signal": "etf_net_inflow", "description": "...", "severity": "high", "data_source": "test"}],
    }
    msg = pusher.format_screener_report(report)
    assert isinstance(msg, EmailMessage)
    assert "Stock Screener" in msg.subject
    assert "Technology" in msg.body
    assert "⚠️" in msg.body
    assert "AMZN" in msg.body
    assert "减至" in msg.body
