def test_run_full_pipeline():
    from stock_screener.run_scanner import run_daily_scan
    result = run_daily_scan()
    assert "sectors" in result
    assert "all_stocks" in result
    assert "adjustments" in result
    assert "anomalies" in result
    # sectors should have 6 entries with rank and score
    assert len(result["sectors"]) == 6
    assert result["sectors"][0]["rank"] == 1