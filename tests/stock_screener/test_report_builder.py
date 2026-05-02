def test_rebalance_reduce_overweight():
    from stock_screener.scanner.report_builder import ReportBuilder

    builder = ReportBuilder()
    positions = [{"ticker": "AMZN", "shares": 2, "entry_price": 258.5}]
    scores = [
        {"ticker": "AMZN", "composite": 0.40, "sector": "Technology"},  # Low score -> reduce
        {"ticker": "META", "composite": 0.82, "sector": "Technology"},  # High score -> new
    ]
    result = builder.build_adjustments(positions, scores, cash=1400)

    reduce = [a for a in result["adjustments"] if a["action"] == "REDUCE"]
    new = [a for a in result["adjustments"] if a["action"] == "NEW"]
    assert any(a["ticker"] == "AMZN" for a in reduce)
    assert any(a["ticker"] == "META" for a in new)