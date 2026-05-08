# Theme Scanner Design Spec

## Context

当前 Scanner 按 6 个固定传统板块（Technology、Healthcare、Finance...）扫描。用户希望新增**主题扫描**能力：输入一个主题词（如 "AI"），系统自动发散相关子领域，细分股票池，评分后推荐。

## Architecture

### Theme Scanning Flow

```
用户输入主题词 (Theme)
    ↓
LLM 推断子领域列表 (Sub-sectors)
    e.g. "AI" → ["AI芯片", "存储", "电力基础设施", "数据中心", "云计算"]
    ↓
LLM 从候选股票池中为每个子领域选股
    ↓
现有 StockScorer 评分引擎打分
    ↓
结果复用 format_deep_screener_report 邮件模板推送
```

### Candidate Pool

固定候选股票池 `THEME_CANDIDATE_POOL`，覆盖主流 AI/科技相关股票。LLM 按子领域从中挑选。

## Files to Modify

### `stock_screener/scanner/theme_scanner.py` — NEW
```
ThemeScanner class
  .scan(theme: str, top_n_per_sector=3) → dict
    1. prompt LLM 推断子领域列表
    2. prompt LLM 为每子领域选股（来自候选池）
    3. StockScorer 评分
    4. 返回 { sub_sectors: { name: [stock_results] }, theme, scan_date }
```

### `stock_screener/scanner/config.py` — MODIFY
```python
# 固定候选股票池
THEME_CANDIDATE_POOL = {
    "AI芯片": ["NVDA", "AMD", "INTC", "QCOM", "AVGO", "MRVL", "MU"],
    "存储": ["SMCI", "WD", "STX", "NTAP"],
    "电力基础设施": ["XEL", "VST", "CEG", "EXC", "NEE", "DUK"],
    "数据中心": ["EQIX", "DLR", "AVB", "CONE", "CORR"],
    "云计算": ["AMZN", "MSFT", "GOOG", "META", "ORCL", "CRM", "NOW"],
    "网络安全": ["PANW", "CRWD", "ZS", "NET"],
    "量子计算": ["IBM", "IONQ", "RGTI", "QUBT"],
    "机器人": ["TSLA", "IRBT", "ISRG", "DEST"],
    "新能源车": ["TSLA", "RIVN", "LCID", "NIO"],
    "半导体设备": ["AMAT", "LRCX", "KLAC", "ASML"],
    "光通信": ["ACIA", "LITE", "FN", "IIVI"],
    "卫星通信": ["IRDM", "SATL", "GHGS"],
    "生物科技": ["REGN", "MRNA", "VRTX", "BIIB"],
    "金融科技": ["COIN", "SQ", "PYPL", "AFRM"],
}
```

### `stock_screener/run_scanner.py` — MODIFY
```python
def run_theme_scan(theme: str) -> dict:
    scanner = ThemeScanner()
    return scanner.scan(theme)

def send_theme_report(theme: str):
    result = run_theme_scan(theme)
    # ... 复用现有 GmailPusher + ReportDB
```

### `stock_screener/scanner/stock_scorer.py` — MINOR MODIFY
`score_sector_stocks` 方法接受 `tickers` list 参数，无需依赖 SECTORS config

### `scheduler/tasks.py` — MODIFY
支持 `theme_scan` 任务类型

### `scheduler/gmail_pusher.py` — MINOR MODIFY
`format_deep_screener_report` 支持 `report_type="theme"` 显示主题名

## LLM Prompt Design

### Sub-sector deduction prompt
```
给定主题 "{theme}"，列出 5-8 个最相关的子领域/细分方向。
每个子领域返回一个词或短语（如"AI芯片"、"电力基础设施"）。
只返回子领域名称列表，每行一个，不要解释。
```

### Stock selection prompt
```
主题是 "{theme}"，子领域是 "{sub_sector}"。
候选股票池：{candidate_pool}
从候选池中选择 3-8 只与该子领域最相关的股票。
只返回股票代码，每行一个，不要解释。
```

## Key Classes

### `ThemeScanner`
```python
class ThemeScanner:
    def __init__(self):
        self._llm = _build_llm_client()

    def scan(self, theme: str, top_n_per_sector=3) -> dict:
        """Run full theme scan pipeline."""
        sub_sectors = self._deduce_sub_sectors(theme)
        all_results = []
        for sub_sector in sub_sectors:
            tickers = self._select_stocks(theme, sub_sector)
            scores = self._score_tickers(tickers)
            scores.sort(key=lambda x: x["composite"], reverse=True)
            all_results.append({
                "sub_sector": sub_sector,
                "stocks": scores[:top_n_per_sector]
            })
        return {
            "theme": theme,
            "sub_sectors": all_results,
            "scan_date": date.today().isoformat(),
        }
```

## Data Flow

```
ThemeScanner.scan()
  → _deduce_sub_sectors()     → [sub1, sub2, ...]
  → _select_stocks()          → {sub1: [tickers], sub2: [tickers], ...}
  → StockScorer.score_tickers()  → scored results per sub-sector
  → Aggregator.aggregate()    → sorted + rated
  → send_theme_report()        → email via GmailPusher
```

## Report Output Format

邮件报告结构与 screener 相同，区别：
- 板块表格 → 子领域表格（每个子领域列出 top 3 股票）
- 保留持仓、调整建议 section
- 主题扫描专属头部：`[TradingAgents] Theme Scan: {theme} — {date}`

## Testing

```python
def test_theme_scanner_ai():
    scanner = ThemeScanner()
    result = scanner.scan("AI")
    assert len(result["sub_sectors"]) >= 4
    assert all(len(s["stocks"]) >= 1 for s in result["sub_sectors"])
    assert all("composite" in s for s in result["sub_sectors"][0]["stocks"])
```

## Verification

1. `pytest tests/stock_screener/test_theme_scanner.py -v`
2. `send_theme_report("AI")` 邮件发送成功
3. 邮件包含：子领域表格 + 每子领域 top 3 股票 + 评分 + 评级
