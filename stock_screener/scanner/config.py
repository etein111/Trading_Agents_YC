SECTORS = {
    "Technology":  {"etf": "XLK", "stocks": ["AMZN", "GOOG", "META", "MSFT", "ORCL"]},
    "Healthcare":   {"etf": "XLV", "stocks": ["JNJ", "PFE", "UNH", "MRK", "ABBV"]},
    "Finance":     {"etf": "XLF", "stocks": ["JPM", "BAC", "GS", "MS", "BLK"]},
    "Consumer":    {"etf": "XLY", "stocks": ["TSLA", "NKE", "KO", "PEP", "COST"]},
    "Energy":      {"etf": "XLE", "stocks": ["XOM", "CVX", "COP", "SLB", "OXY"]},
    "Industrials": {"etf": "XLI", "stocks": ["CAT", "BA", "HON", "GE", "UPS"]},
}

# Candidate stock pool for theme scanning — LLM picks from here per sub-sector
THEME_CANDIDATE_POOL = {
    "AI芯片": ["NVDA", "AMD", "INTC", "QCOM", "AVGO", "MRVL", "MU", "AMAT"],
    "存储": ["SMCI", "WD", "STX", "NTAP", "PSTG", "NXPI"],
    "电力基础设施": ["XEL", "VST", "CEG", "EXC", "NEE", "DUK", "SO", "D"],
    "数据中心": ["EQIX", "DLR", "AVB", "CONE", "CORR", "AMT", "PLDT"],
    "云计算": ["AMZN", "MSFT", "GOOG", "META", "ORCL", "CRM", "NOW", "WDAY"],
    "网络安全": ["PANW", "CRWD", "ZS", "NET", "AKAM", "FTNT"],
    "量子计算": ["IBM", "IONQ", "RGTI", "QUBT", "HON"],
    "机器人": ["TSLA", "IRBT", "ISRG", "DEST", "KUKA"],
    "新能源车": ["TSLA", "RIVN", "LCID", "NIO", "F", "GM"],
    "半导体设备": ["AMAT", "LRCX", "KLAC", "ASML", "TOVYY"],
    "光通信": ["ACIA", "LITE", "FN", "IIVI", "LRCX"],
    "卫星通信": ["IRDM", "SATL", "GHGS", "AMZN"],
    "生物科技": ["REGN", "MRNA", "VRTX", "BIIB", "MRK"],
    "金融科技": ["COIN", "SQ", "PYPL", "AFRM", "NU"],
    "消费AI": ["SHOP", "U", "AI", "APP", "PATH"],
    "自动驾驶": ["TSLA", "GM", "F", "BIDU", "TOYOY"],
}

WEIGHTS = {"momentum": 0.4, "valuation": 0.3, "macro": 0.2, "fundamentals": 0.1}
SCORE_THRESHOLDS = {"strong_buy": 0.70, "consider": 0.50}
MAX_POSITION_WEIGHT = 0.30