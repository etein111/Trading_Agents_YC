SECTORS = {
    "Technology":  {"etf": "XLK", "stocks": ["AMZN", "GOOG", "META", "MSFT", "ORCL"]},
    "Healthcare":   {"etf": "XLV", "stocks": ["JNJ", "PFE", "UNH", "MRK", "ABBV"]},
    "Finance":     {"etf": "XLF", "stocks": ["JPM", "BAC", "GS", "MS", "BLK"]},
    "Consumer":    {"etf": "XLY", "stocks": ["TSLA", "NKE", "KO", "PEP", "COST"]},
    "Energy":      {"etf": "XLE", "stocks": ["XOM", "CVX", "COP", "SLB", "OXY"]},
    "Industrials": {"etf": "XLI", "stocks": ["CAT", "BA", "HON", "GE", "UPS"]},
}
WEIGHTS = {"momentum": 0.4, "valuation": 0.3, "macro": 0.2, "fundamentals": 0.1}
SCORE_THRESHOLDS = {"strong_buy": 0.70, "consider": 0.50}
MAX_POSITION_WEIGHT = 0.30