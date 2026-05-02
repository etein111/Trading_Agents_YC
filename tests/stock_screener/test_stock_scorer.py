def test_score_stock_returns_all_dimensions():
    from stock_screener.scanner.stock_scorer import StockScorer

    scorer = StockScorer()
    result = scorer.score_stock("AMZN")

    assert hasattr(result, 'scores')
    assert set(result.scores.keys()) == {"momentum", "valuation", "macro", "fundamentals"}
    for v in result.scores.values():
        assert 0.0 <= v <= 1.0
    assert hasattr(result, 'peer_avg')
    assert hasattr(result, 'above_peer')
    assert result.sector == "Technology"
    assert result.stock == "AMZN"