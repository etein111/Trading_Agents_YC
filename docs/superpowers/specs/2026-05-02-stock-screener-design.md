# Multi-Agent Stock Screener & Portfolio Rebalancer Design

## Context

用户现有的 TradingAgents 只能分析单票（用户指定 ticker → 输出 Buy/Hold/Sell），缺乏：
1. **市场扫描能力** — 从全市场/行业板块中发现潜力股
2. **动态组合管理** — 基于市场变化给出持仓调整建议

目标：在现有 TradingAgents 架构上扩展，构建一个**每日选股 + 组合再平衡**的报告系统，次日开盘前通过邮件推送。

---

## 用户需求摘要

| 维度 | 要求 |
|------|------|
| 覆盖范围 | 行业/板块扫描，每板块 3-5 只代表性股票 |
| 板块筛选维度（优先级） | A动量 > B估值 > E宏观催化 > C基本面 |
| 扫描频率 | 每日收盘后扫描，次日开盘前推送 |
| 交付方式 | 邮件报告（主动推送，不只是 CLI 查询） |
| 报告深度 | 完整报告，包含：每个 Agent 的输入输出、数据来源、决策原因解释 |
| 持仓调整建议 | 详细，包含判断依据，不只是评分或结论 |

---

## 权重策略：静态基准 + 动态补充

### 静态基准权重

作为默认配置，保持固定（防止主观随意性）：

| 维度 | 权重 | 说明 |
|------|------|------|
| A. 动量 | 40% | 趋势跟踪，短线驱动 |
| B. 估值 | 30% | 中线价值锚定 |
| E. 宏观催化 | 20% | 政策/利率/板块轮动 |
| C. 基本面 | 10% | 长线支撑 |

### 动态补充机制（防止异军突起被忽略）

#### 1. 异军突起检测（Anomaly Detection）

在板块评分前增加检测模块，识别被低估的结构性机会：

**检测信号：**
- 近期涨幅远超板块历史均值 + 资金流入加速（ETF净流入）
- 政策利好首次覆盖的板块
- 机构持仓大幅增加但价格还未启动
- 板块内多只股票同时出现异常成交量

**处理方式：**
- 检测到异动时，在报告中单独标注 `⚠️ 异动板块：XXX`，不修改权重，但给你一个显眼的提醒，由你最终决策

**数据来源：**
- ETF净流入：`yfinance` `ETF名.history()` 成交量对比
- 政策信号：`News Analyst` 解析政策公告
- 机构持仓：`get_insider_transactions()` + 13F 持仓变化

#### 2. 月度权重回测（Monthly Review）

每周末运行一次权重有效性分析：

```
对过去1周数据回测：
- 维度A动量跑赢市场的比例？
- 维度B估值有效性评分？
- 哪些板块持续被低估/高估？

→ 输出权重调整建议邮件
```

### 权重调整决策流程

```
扫描触发
    │
    ▼
板块初筛（静态权重）
    │
    ▼
异常检测模块 ───→ ⚠️ 异动板块标记
    │
    ▼
生成报告 ───→ 包含"异动提醒"区块
    │
    ▼
每月末 ───→ 权重回测 + 调整建议邮件
```

### 异军突起示例

假设 Energy 板块平时权重很低，但 OPEC 突然宣布减产：

```
⚠️ 异动板块：Energy
原因：政策利好(OPEC减产) + 机构加仓(XLE净流入+15%) + 技术突破(50日均线)
建议：可关注但不建议重仓，等回调确认后再介入
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    STOCK SCREENER REPORT                      │
│              (次日开盘前推送至 Gmail)                          │
└─────────────────────────────────────────────────────────────┘

Layer 0: 异军突起检测（新增）
┌──────────────────┐
│ Anomaly Detector │ ──→ ⚠️ 异动板块标记（不修改权重，单独提醒）
│ (新增)           │     检测信号：ETF净流入+价格突破+政策催化
└──────────────────┘

Layer 1: 板块扫描
┌──────────────────┐
│ Sector Scanner   │ ──→ 板块吸引力排序 (A×40% + B×30% + E×20% + C×10%)
│ (新增)           │     输出: [板块1, 板块2, ...] + 各板块权重得分
└──────────────────┘

Layer 2: 个股筛选
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│Market Analyst│ │Fundamentals  │ │News Analyst  │ │Social Analyst│
│  (扩展)      │ │ Analyst(扩展) │ │  (扩展)      │ │  (扩展)      │
│  负责 A 动量 │ │  负责 B估值   │ │  负责 E宏观   │ │  负责 C基本面 │
│              │ │  + C基本面   │ │    催化      │ │  (辅助)      │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
  输出:           输出:            输出:           输出:
  动量得分        估值得分         宏观催化得分    基本面得分
  数据来源:       数据来源:        数据来源:       数据来源:
  yfinance        yfinance        yfinance       yfinance

Layer 3: 综合评分
┌──────────────────┐
│ Aggregator       │ ──→ 综合得分 = A×40% + B×30% + E×20% + C×10%
│ (新增/集成)     │     每只股票: [ticker, 板块, 各维度得分, 综合得分]
└──────────────────┘

Layer 4: 持仓调整建议
┌──────────────────────────┐
│ Portfolio Manager (扩展)  │
│ 输入: 综合评分 + 现有持仓  │
│ 输出:                     │
│   - 建议加仓股 (理由+来源) │
│   - 建议减仓股 (理由+来源) │
│   - 建议新建仓 (理由+来源) │
│   - 持仓不变 (理由)        │
└──────────────────────────┘
```

---

## 层1详解：板块扫描（ Sector Scanner ）

### 输入

| 维度 | 权重 | 数据来源 |
|------|------|----------|
| A. 动量 | 40% | yfinance: 板块 ETF（XLK/XLF/XLV/XLE...）近 N 日涨幅 |
| B. 估值 | 30% | yfinance: 板块内个股 PE/PB 中位数相对历史分位 |
| E. 宏观催化 | 20% | yfinance News + News Analyst（利率、政策、板块轮动规律）|
| C. 基本面 | 10% | yfinance: 板块整体 Revenue/EPS 增速 |

### 输出

```json
{
  "sectors": [
    {"name": "Technology", "score": 0.85, "rank": 1, "breakdown": {"momentum": 0.9, "valuation": 0.8, "macro": 0.7, "fundamentals": 0.9}},
    {"name": "Healthcare", "score": 0.72, "rank": 2, "breakdown": {...}},
    ...
  ],
  "scan_date": "2026-05-02",
  "methodology": "A×40% + B×30% + E×20% + C×10%"
}
```

### 覆盖板块

初始覆盖 6 个核心板块（可配置）：

| 板块 | 代表ETF | 代表股（初筛）|
|------|--------|--------------|
| Technology | XLK | AMZN, GOOG, META, MSFT, ORCL |
| Healthcare | XLV | JNJ, PFE, UNH, MRK, ABBV |
| Finance | XLF | JPM, BAC, GS, MS, BLK |
| Consumer | XLY | TSLA, NKE, KO, PEP, COST |
| Energy | XLE | XOM, CVX, COP, SLB, OXY |
| Industrials | XLI | CAT, BA, HON, GE, UPS |

---

## 层2详解：个股筛选（扩展现有 Analyst）

每个 Analyst 扩展后，负责对板块内初筛股票进行评分：

### Market Analyst（扩展）

- **职责**：A 动量分析 + 辅助 E 宏观
- **输入**：板块内 3-5 只股票的历史价格数据
- **输出**：动量得分（0-1）+ 近期趋势描述
- **数据来源**：yfinance `ticker.history()`

### Fundamentals Analyst（扩展）

- **职责**：B 估值分析 + C 基本面分析
- **输入**：PE、PB、EV/EBITDA、ROE、营收增速、净利润增速
- **输出**：估值得分 + 基本面得分
- **数据来源**：`get_fundamentals()` + `get_income_statement()` + `get_balance_sheet()`

### News Analyst（扩展）

- **职责**：E 宏观催化分析
- **输入**：近期相关新闻、政策公告、利率变化
- **输出**：宏观催化得分 + 事件描述
- **数据来源**：`get_news()` + Alpha Vantage news sentiment

### Social Analyst（扩展）

- **职责**：辅助基本面（非核心）
- **输入**：社交媒体情绪、机构持仓变化
- **输出**：情绪得分（辅助参考）
- **数据来源**：yfinance insider + news sentiment

---

## 层3详解：综合评分（Aggregator）

### 评分公式

```
综合得分 = A×0.4 + B×0.3 + E×0.2 + C×0.1
```

### 筛选阈值

- 综合得分 ≥ 0.70 → **强烈推荐（Buy）**
- 综合得分 0.50–0.70 → **谨慎推荐（Consider）**
- 综合得分 < 0.50 → **不推荐（Skip）**

### 输出格式

```json
{
  "stock": "AMZN",
  "sector": "Technology",
  "scores": {
    "momentum": 0.85,
    "valuation": 0.72,
    "macro": 0.68,
    "fundamentals": 0.90,
    "composite": 0.79
  },
  "rating": "Strong Buy",
  "peer_avg": {"momentum": 0.65, "valuation": 0.58},
  "above_peer": true
}
```

---

## 层4详解：持仓调整建议（Portfolio Manager 扩展）

### 输入

1. 综合评分结果（来自层3）
2. 现有持仓：`data/portfolio.json`

```json
{
  "cash_balance": 1400,
  "positions": [
    {"ticker": "AMZN", "shares": 2, "entry_price": 258.50, "entry_date": "2026-04-29", "broker": "Trade25"}
  ]
}
```

### 决策逻辑

```
IF stock in portfolio AND composite_score < threshold:
    → 建议减仓 (减多少？看分差和cash需求)

IF stock NOT in portfolio AND composite_score >= threshold:
    → 建议加仓 (加多少？看cash可用量和风险分散)

IF stock NOT in portfolio AND composite_score >= 0.85 AND top-3 sector:
    → 建议新建仓 (优先级最高)

IF stock in portfolio AND composite_score >= 0.70:
    → 持仓不变 (强势持有)
```

### 输出：完整持仓调整报告

```json
{
  "adjustments": [
    {
      "action": "REDUCE",
      "ticker": "AMZN",
      "current_shares": 2,
      "recommended_shares": 1,
      "reason": "AMZN composite_score=0.79 (Strong Buy)，但持仓占比过重(>60%)，建议减至1股释放$258用于新机会",
      "source": {
        "composite_score": 0.79,
        "peer_avg": 0.65,
        "position_weight": 0.62,
        "max_position_weight": 0.30
      }
    },
    {
      "action": "ADD",
      "ticker": "META",
      "current_shares": 0,
      "recommended_shares": 1,
      "reason": "META composite_score=0.82 (Strong Buy)，Technology板块rank=1，建议开盘买入1股",
      "source": {
        "composite_score": 0.82,
        "sector": "Technology",
        "sector_rank": 1,
        "cash_available": 1400,
        "estimated_cost": 480
      }
    }
  ],
  "unchanged": [
    {
      "ticker": "GOOG",
      "reason": "composite_score=0.68 (Consider)，但现有持仓合理，继续持有观察"
    }
  ]
}
```

---

## 邮件报告格式

### 结构

```
┌────────────────────────────────────────────┐
│ Daily Stock Screener & Portfolio Rebalancer │
│ 2026-05-03 开盘前报告                       │
└────────────────────────────────────────────┘

## 零、⚠️ 异动板块提醒（如有）
| 板块 | 异常信号 | 建议操作 |
|------|----------|----------|
| Energy | OPEC减产+机构加仓+XLE净流入+15% | 可关注，等回调确认 |

## 一、板块扫描结果
| 排名 | 板块 | 综合得分 | 动量 | 估值 | 宏观 | 基本面 |
|------|------|----------|------|------|------|--------|
| 1 | Technology | 0.85 | 0.9 | 0.8 | 0.7 | 0.9 |
| 2 | Healthcare | 0.72 | 0.6 | 0.8 | 0.8 | 0.7 |
...

## 二、个股推荐（每板块 Top 3）
### Technology（得分区间 0.72-0.88）
| 股票 | 综合得分 | 动量 | 估值 | 宏观 | 基本面 | 推荐理由 |
|------|----------|------|------|------|--------|----------|
| META | 0.88 | 0.9 | 0.85 | 0.8 | 0.9 | ... |
| GOOG | 0.82 | 0.8 | 0.8 | 0.9 | 0.8 | ... |
...

## 三、持仓调整建议
### 建议减仓
| 股票 | 当前持仓 | 建议 | 原因 |
|------|----------|------|------|
| AMZN | 2股 | 减至1股 | ... |

### 建议加仓/新建仓
| 股票 | 建议 | 原因 |
|------|------|------|
| META | 开盘买入1股 | ... |

### 持仓不变
| 股票 | 原因 |
|------|------|
| GOOG | ... |
```

---

## 数据来源汇总

| 数据类型 | 来源 | 备注 |
|----------|------|------|
| 价格/动量 | `yfinance` `ticker.history()` | 1个月数据 |
| 估值/基本面 | `yfinance` `ticker.info` | PE, PB, ROE, Debt/Equity 等 |
| 财务报表 | `yfinance` `income_stmt`, `balance_sheet` | 季度/年报 |
| 新闻/宏观 | `yfinance` news + `alpha_vantage` news sentiment | 近期相关事件 |
| 持仓数据 | `data/portfolio.json` | PortfolioManager |
| 板块 ETF | `yfinance` `XLK`, `XLF` 等 | 板块动量代理 |

---

## 实现路径

### Phase 0：异军突起检测（新增 Anomaly Detector）

- 新建 `AnomalyDetector` 模块
- 检测信号：ETF净流入、价格突破、政策催化、机构加仓
- 输出：⚠️ 异动板块标记（不修改权重，单独提醒）

### Phase 1：板块扫描（新增 Sector Scanner Agent）

- 新建 `SectorScanner` agent
- 覆盖 6 个核心板块
- 输出板块排序 + 权重得分

### Phase 2：个股筛选（扩展现有 Analyst）

- 扩展 `Market Analyst`、`Fundamentals Analyst`、`News Analyst`、`Social Analyst`
- 每只股票输出各维度评分
- 添加数据来源标注

### Phase 3：综合评分层（新增 Aggregator）

- 整合四维评分
- 输出个股排序列表
- 筛选阈值判断

### Phase 4：Portfolio Manager 扩展

- 整合综合评分 + 现有持仓
- 输出持仓调整建议（含详细原因）
- 支持邮件报告生成

### Phase 5：Scheduler 集成

- 每日收盘后（20:00）触发 Phase 0+1+2+3+4
- 次日开盘前（08:00）推送邮件报告（含异动提醒区块）
- `task_queue.json` 更新
- 每周五额外触发周度权重回测（单独任务）

---

## 成功标准

1. 每日邮件报告按时推送，包含板块排序 + 个股推荐 + 持仓建议
2. 每条建议都有明确的数据来源标注
3. Portfolio Manager 的判断逻辑可解释、可追溯
4. 覆盖 6 个核心板块，每板块 3-5 只股票
5. 与现有 TradingAgents 共存，不破坏现有 `analyze` 功能
6. 异动板块检测正常工作，能在报告中标记 ⚠️ 信号
7. 月度权重回测能输出调整建议（不自动修改，由用户决策）

---

## 风险与备选

| 风险 | 应对 |
|------|------|
| Yahoo Finance 限速（频繁调用多只股票）| 使用代理 7890，错峰调用，加缓存 |
| API 调用成本过高 | 限制扫描频率，优化 LLM 调用 |
| 报告信息量过大难以阅读 | 分级展示：摘要 + 详情，摘要控制在 1 页 |
