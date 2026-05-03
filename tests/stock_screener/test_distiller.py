"""Tests for distiller.py"""

import pytest

from stock_screener.scanner.distiller import Distiller


class TestDistiller:
    def test_distill_market_analyst_returns_summary_and_chart_data(self):
        distiller = Distiller()
        raw_report = (
            "Market Analysis: RSI is 78.1 indicating overbought conditions. "
            "SMA 20 is at 245.3 while SMA 50 sits at 238.9, forming a golden cross. "
            "MACD histogram shows bullish divergence with signal line crossover today. "
            "Volume surged 45% above average on strong buying pressure. "
            "Price action confirms upward momentum with higher highs and higher lows pattern."
        )
        result = distiller.distill(raw_report, "market")
        assert "summary" in result
        assert "chart_data" in result
        assert result["chart_data"]["rsi"] == 78.1
        assert result["chart_data"]["sma_20"] == 245.3
        assert "golden cross" in result["summary"].lower()

    def test_distill_social_media_returns_sentiment_metrics(self):
        distiller = Distiller()
        raw_report = (
            "Social sentiment analysis shows strong bullish bias with sentiment score of 0.72. "
            "Mention volume increased 42% over the past 24 hours with 15,847 posts discussing AAPL. "
            "Positive posts account for 68% of total discussion while negative posts represent 22%. "
            "Retail investors show increasing interest with growing allocation to momentum strategies."
        )
        result = distiller.distill(raw_report, "social")
        assert "summary" in result
        assert "chart_data" in result
        assert result["chart_data"]["sentiment_score"] == 0.72
        assert "42%" in result["chart_data"]["mention_volume"]

    def test_distill_fundamentals_extracts_pe_and_growth(self):
        distiller = Distiller()
        raw_report = (
            "Fundamental analysis reveals healthy financial metrics. "
            "PE ratio stands at 28.4 with forward PE at 24.2 suggesting reasonable valuation. "
            "Revenue growth of 23% year-over-year demonstrates strong top-line expansion. "
            "Profit margin of 18% indicates operational efficiency. "
            "EPS of 6.85 and dividend yield of 2.1% round out the picture."
        )
        result = distiller.distill(raw_report, "fundamentals")
        assert "summary" in result
        assert "chart_data" in result
        assert result["chart_data"]["pe_ratio"] == 28.4
        assert result["chart_data"]["rev_growth"] == "23%"
        assert result["chart_data"]["profit_margin"] == "18%"