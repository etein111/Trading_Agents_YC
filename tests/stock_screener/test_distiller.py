import pytest
from stock_screener.scanner.distiller import Distiller


@pytest.fixture
def distiller():
    return Distiller()


def test_distill_market_analyst_returns_summary_and_chart_data(distiller):
    raw = (
        "RSI is 78.1 indicating overbought conditions. "
        "The price is trading above both SMA20 ($245.3) and SMA50 ($238.7). "
        "MACD indicator just generated a golden cross signal with momentum strengthening. "
        "Volume increased 23% vs the 20-day average. The overall trend is bullish with strong momentum."
    )
    result = distiller.distill(raw, "market")
    assert "summary" in result
    assert "chart_data" in result
    assert result["chart_data"]["rsi"] == 78.1
    assert result["chart_data"]["sma_20"] == 245.3
    assert result["chart_data"]["sma_50"] == 238.7
    assert "golden cross" in result["summary"].lower()
    assert len(result["summary"].split()) < 150


def test_distill_social_media_returns_sentiment_metrics(distiller):
    raw = (
        "Social sentiment is moderately positive with a score of 0.72. "
        "Twitter mention volume surged 42% this week with 68% positive posts vs 22% negative. "
        "Reddit discussion increased moderately. "
        "The overall mood is bullish among retail and institutional investors."
    )
    result = distiller.distill(raw, "social")
    assert "summary" in result
    assert result["chart_data"]["sentiment_score"] == 0.72
    assert result["chart_data"]["mention_volume"] == "42%"


def test_distill_fundamentals_extracts_pe_and_growth(distiller):
    raw = (
        "AMZN reports PE ratio of 28.4 vs sector average of 43. "
        "Forward PE is 24.1. Revenue growth came in at 23% YoY driven by AWS expansion. "
        "Profit margin expanded to 18%. EPS is $8.47. Dividend yield is 2.1%."
    )
    result = distiller.distill(raw, "fundamentals")
    assert result["chart_data"]["pe_ratio"] == 28.4
    assert result["chart_data"]["rev_growth"] == "23%"
    assert result["chart_data"]["profit_margin"] == "18%"