# US Stock Investment Analysis System - Design Spec

**Date:** 2026-05-01
**Author:** TradingAgents Assistant
**Status:** Approved

---

## 1. Overview

This system provides automated investment analysis for US stock market, combining multi-agent AI analysis with daily/weekly automated reports delivered via Gmail.

**User Profile:**
- Investment style: Long-term value investment (primary) + short-term trading (secondary)
- Current positions: AMZN 2 shares @ $258.5 (Trade25, opened 2026-04-29)
- Cash balance: $1,400
- Broker: Trade25
- Communication: Gmail

**Goals:**
1. Passive stock recommendations based on policy changes and market analysis
2. On-demand comprehensive analysis of any stock symbol

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    System Architecture                   │
│                                                         │
│  ┌─────────────────┐         ┌─────────────────────┐   │
│  │   CLI Layer     │         │   Scheduler Service│   │
│  │  (Interactive)   │         │  (Automated Push)   │   │
│  └────────┬────────┘         └──────────┬──────────┘   │
│           │                              │              │
│           └──────────────┬─────────────────┘             │
│                          ▼                               │
│  ┌─────────────────────────────────────────────────┐    │
│  │              TradingAgents Engine               │    │
│  │  (Sentiment, Fundamentals, News, Technical     │    │
│  │   Analysts + Bull/Bear Researchers + Risk Mgmt)  │    │
│  └─────────────────────────────────────────────────┘    │
│                          │                              │
│                          ▼                              │
│  ┌─────────────────────────────────────────────────┐    │
│  │              Gmail Push Service                 │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Push Schedule

| Type | Frequency | Content |
|------|-----------|---------|
| **Daily Briefing** | Pre-market + After-hours | Market sentiment, key events, action summary |
| **Real-time Alert** | On-demand (major events) | Breaking opportunities or risks |
| **Weekly Report** | Weekly (Monday) | Portfolio health check + market deep analysis |

---

## 4. Data Storage

**Portfolio File:** `data/portfolio.json`

```json
{
  "cash_balance": 1400,
  "last_updated": "2026-05-01",
  "positions": [
    {
      "ticker": "AMZN",
      "shares": 2,
      "entry_price": 258.5,
      "entry_date": "2026-04-29",
      "broker": "Trade25"
    }
  ]
}
```

**Report Output:** `reports/{ticker}/{date}/`

**Scheduler Log:** `logs/scheduler.log`

---

## 5. Error Handling

| Scenario | Handling |
|----------|----------|
| Gmail send failure | Retry 3x (5min / 15min / 60min), then log error |
| Analysis timeout | 10min auto-skip, notify user of incomplete result |
| Network interruption | Reconnect and retry missed tasks |
| LLM API rate limit | Exponential backoff, notify user of delay |

---

## 6. CLI Commands

| Command | Function | Example |
|---------|----------|---------|
| `/analyze <ticker>` | Full analysis of a stock | `/analyze AMZN` |
| `/portfolio` | View current portfolio summary | `/portfolio` |
| `/add <ticker> <shares> <price>` | Add position | `/add AMZN 2 258.5` |
| `/remove <ticker>` | Remove position | `/remove AMZN` |
| `/alert <ticker> <condition>` | Set alert | `/alert AMZN below 250` |
| `/report` | Generate latest full report | `/report` |
| `/scan` | Quick market scan for opportunities | `/scan` |
| `/weekly` | Trigger weekly analysis | `/weekly` |

**Natural Language Support:**
- "AMZN又补了1股，价格261，建仓日期今天" → Add position
- "清仓ORCL" → Remove position
- "INTC跌到42了，我考虑减仓一半" → Trigger INTC reduction analysis

---

## 7. Analysis Report Format

For `/analyze <ticker>`, output includes:

**Operation Suggestion:**
```
Recommendation: HOLD
Target Price: $320 (20% upside potential)
Stop Loss: $235 (reduce 50% if broken)
Holding Logic: Long-term uptrend, solid fundamentals, watch for pre-earnings volatility
```

---

## 8. Gmail Push Content Format

**Pre-market Briefing:**
- Portfolio sentiment summary
- Key events today (earnings/policy)
- Action recommendation summary

**After-hours Report:**
- Full market analysis summary
- Portfolio performance review
- Next week watchlist

**Weekly Report:**
- Portfolio health check (P&L, risk rating)
- Market opportunity scan
- Position adjustment suggestions (reduce/add/hold)

---

## 9. Components

| Component | Responsibility |
|-----------|----------------|
| CLI Interactive | Handle user queries |
| Scheduler Service | Manage daily/weekly task execution |
| TradingAgents Engine | Core analysis logic |
| Gmail Pusher | Send reports via Gmail |
| Portfolio Manager | Store positions locally |

---

## 10. Implementation Priorities

### Phase 1: Core CLI
- `/analyze` command using existing TradingAgents
- `/portfolio` view command
- `/add` `/remove` position management

### Phase 2: Gmail Integration
- Gmail API / SMTP setup
- Email templates
- Send on-demand reports

### Phase 3: Scheduler Service
- Daily pre-market / after-hours push
- Weekly portfolio report
- Background daemon setup

### Phase 4: Real-time Monitoring
- News / sentiment monitoring
- Price alert triggers
- Automatic analysis on events

---

## 11. File Structure

```
TradingAgents/
├── docs/superpowers/specs/
│   └── 2026-05-01-us-stock-analysis-design.md
├── data/
│   └── portfolio.json
├── reports/
│   └── {ticker}/{date}/
├── logs/
│   └── scheduler.log
├── cli/
│   └── main.py (existing)
├── scheduler/
│   ├── __init__.py
│   ├── service.py
│   └── gmail_pusher.py
└── portfolio/
    └── manager.py
```