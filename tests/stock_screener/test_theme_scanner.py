import pytest
from stock_screener.scanner.theme_scanner import ThemeScanner

def test_deduces_sub_sectors():
    scanner = ThemeScanner()
    subs = scanner._deduce_sub_sectors("AI")
    assert isinstance(subs, list)
    assert len(subs) >= 3

def test_theme_scanner_scan_returns_structure():
    scanner = ThemeScanner()
    result = scanner.scan("AI")
    assert "theme" in result
    assert "sub_sectors" in result
    assert result["theme"] == "AI"
    assert isinstance(result["sub_sectors"], list)

def test_theme_scanner_scan_includes_scores():
    scanner = ThemeScanner()
    result = scanner.scan("AI")
    first_sub = result["sub_sectors"][0]
    assert "sub_sector" in first_sub
    assert "stocks" in first_sub
    assert len(first_sub["stocks"]) >= 1
    assert "composite" in first_sub["stocks"][0]
