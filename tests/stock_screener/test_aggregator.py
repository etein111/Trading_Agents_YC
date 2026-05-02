def test_aggregator_threshold_filtering():
    from stock_screener.scanner.aggregator import Aggregator
    from stock_screener.scanner.config import SCORE_THRESHOLDS

    agg = Aggregator(thresholds=SCORE_THRESHOLDS)
    stocks = [
        {"stock": "A", "composite": 0.75, "scores": {}},
        {"stock": "B", "composite": 0.55, "scores": {}},
        {"stock": "C", "composite": 0.40, "scores": {}},
    ]
    result = agg.aggregate(stocks)

    assert result.strong_buy[0]["stock"] == "A"
    assert result.consider[0]["stock"] == "B"
    assert result.skip[0]["stock"] == "C"
    assert result.all_stocks[0]["rating"] == "Strong Buy"