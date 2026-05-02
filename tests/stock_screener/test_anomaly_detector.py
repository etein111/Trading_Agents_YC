def test_detect_anomaly_etf_inflow():
    """Test ETF net inflow anomaly detection."""
    from stock_screener.scanner.anomaly_detector import AnomalyDetector, Anomaly

    mock_data = {
        "Technology": [1e6, 1.2e6, 1.1e6, 5e6, 6e6],  # Last 2 days 5x+ average
        "Finance": [1e6, 1.1e6, 1e6, 1.2e6, 1.1e6],  # Normal
    }
    detector = AnomalyDetector(etf_volume_data=mock_data)
    anomalies = detector.detect()

    assert len(anomalies) == 1
    assert anomalies[0].sector == "Technology"
    assert anomalies[0].signal == "etf_net_inflow"
    assert anomalies[0].severity == "high"
