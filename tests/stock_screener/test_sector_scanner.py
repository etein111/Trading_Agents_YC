def test_sector_ranking_output():
    from stock_screener.scanner.sector_scanner import SectorScanner
    from stock_screener.scanner.config import SECTORS, WEIGHTS

    scanner = SectorScanner(sectors=SECTORS, weights=WEIGHTS)
    result = scanner.scan()

    assert "sectors" in result
    assert len(result["sectors"]) == 6
    assert result["sectors"][0]["rank"] == 1
    assert result["methodology"] == "A×0.4 + B×0.3 + E×0.2 + C×0.1"
    # Score should be between 0 and 1
    for s in result["sectors"]:
        assert 0 <= s["score"] <= 1