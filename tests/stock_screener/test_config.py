def test_sector_config_has_required_fields():
    import pytest
    from stock_screener.scanner.config import SECTORS, WEIGHTS
    assert "Technology" in SECTORS
    assert SECTORS["Technology"]["etf"] == "XLK"
    assert len(SECTORS["Technology"]["stocks"]) >= 3
    assert sum(WEIGHTS.values()) == pytest.approx(1.0)