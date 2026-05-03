# Email Beautification — Deep Agent Report Optimization

## Context

The current `format_deep_screener_report()` in `gmail_pusher.py` dumps the full raw output of each TradingAgents agent as plain text wrapped in `<pre>` tags. This produces emails that are:
- Too long (8 stocks × 7 agents = 56 blocks of unprocessed text)
- Unreadable in Gmail (no markdown rendering, `##` headers not parsed)
- Filled with verbose LLM output that obscures key signals

The goal is to distill each agent's output into a **~100-word brief paragraph** highlighting key findings, with **critical numbers** surfaced in a compact metrics table.

---

## Architecture

### Pipeline

```
run_deep_analysis()  [deep_analysis.py]
  └─ propagate(ticker, date) → raw reports (market_report, sentiment_report, ...)
       │
       ▼
Distiller.distill(raw_report, agent_name)  [NEW: scanner/distiller.py]
  └─ LLM call → {"summary": str, "chart_data": dict}
       │
       ▼
DeepStockAnalysis gets new fields:
  - market_summary: str (~100 words)
  - market_chart_data: dict
  - sentiment_summary: str
  - sentiment_chart_data: dict
  - news_summary: str
  - news_chart_data: dict
  - fundamentals_summary: str
  - fundamentals_chart_data: dict
  - investment_plan_summary: str
  - trader_plan_summary: str
  - final_decision_summary: str
       │
       ▼
format_deep_screener_report()  [gmail_pusher.py]
  └─ renders each stock block with:
       - Colored header (ticker, sector, composite score, rating)
       - 7 agent sections, each: summary paragraph + metrics table
```

### Distillation Prompt Strategy

Each distillation call sends the raw agent report to the LLM with a prompt instructing it to:
1. Extract 3-5 key findings as a ~100-word narrative summary
2. Extract numeric/metric values into structured `chart_data` dict
3. Preserve original language (English) since LLM responses are in English

### Metrics Per Agent

| Agent | chart_data fields |
|-------|-------------------|
| Market Analyst | rsi, sma_20, sma_50, macd_signal, trend_direction, volume_change_pct |
| Social Media Analyst | sentiment_score, mention_volume, positive_pct, negative_pct, trend |
| News Analyst | news_count, polarity, sector_relevance_score |
| Fundamentals Analyst | pe_ratio, forward_pe, rev_growth, profit_margin, eps, dividend_yield |
| Research Manager | bull_case_prob, bear_case_prob, risk_score |
| Trader | entry_price, target_price, stop_loss, position_size_pct, risk_reward_ratio |
| Portfolio Manager | rating (Buy/Hold/Sell), conviction_pct, holding_period |

---

## Files to Modify

- `stock_screener/scanner/distiller.py` — **NEW**: `Distiller` class with `.distill(raw_report, agent_name) -> dict`
- `stock_screener/scanner/deep_analysis.py` — after `propagate()`, call `Distiller` for each agent report; add new summary/chart_data fields to `DeepStockAnalysis`
- `scheduler/gmail_pusher.py` — `format_deep_screener_report()` rewritten with new per-stock block layout: summary paragraph + metrics table grid per agent, HTML table for sector rankings, colored key numbers

---

## Email Layout

```
[Subject: TradingAgents Stock Screener — YYYY-MM-DD]

┌─────────────────────────────────────────────────────┐
│ 板块扫描结果                                          │
│ 排名 | 板块 | 综合得分 | 动量 | 估值 | 宏观 | 基本面    │
│   1  | XXX |  0.823   | 0.xx | 0.xx | 0.xx | 0.xx  │
└─────────────────────────────────────────────────────┘

┌─ AMZN — Technology ───────────────────────────────┐
│ 综合得分 0.847  |  评级: Buy                        │
│                                                      │
│ 【Market Analyst · 技术面】                           │
│ RSI 78.1 超买，均线多头排列，MACD 形成金叉...         │
│ ┌──────────────────────────────┐                   │
│ │ RSI      │ SMA20    │ Trend  │                   │
│ │ 78.1    │ $245.3   │   ↑   │                   │
│ └──────────────────────────────┘                   │
│                                                      │
│ 【Social Media · 情绪面】                             │
│ Twitter 讨论量较上周+42%，机构情绪偏多...             │
│ ┌──────────────────────────────┐                   │
│ │ Sentiment │ Volume  │  Pos%  │                   │
│ │   0.72   │  +42%   │  68%   │                   │
│ └──────────────────────────────┘                   │
│ ... (7 agents total)                                │
└─────────────────────────────────────────────────────┘
[next stock block]
```

Key numbers (RSI, PE, prices, %, ratings) use inline CSS color:
- Positive values: `color:#2E7D32` (green)
- Negative values: `color:#C62828` (red)
- Neutral/bold metrics: `color:#1565C0` (blue)
- Rating badge: background-colored pill

---

## HTML Style Guidelines

- No markdown — pure HTML inline styles
- Font: Arial, max-width 950px
- Section headers: colored left border (4px) + padding
- Metrics tables: compact (padding: 4px 8px), alternating row background
- Stock blocks: rounded border (8px radius), subtle shadow
- Key numbers highlighted inline with colored `<span>`
- `white-space: pre-wrap` only for summary text, never for layout
