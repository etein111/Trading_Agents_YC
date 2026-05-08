"""Theme Scanner — LLM-powered theme decomposition and stock picking."""

import os
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from tradingagents.llm_clients.factory import create_llm_client
from tradingagents.default_config import DEFAULT_CONFIG

from .config import THEME_CANDIDATE_POOL
from .stock_scorer import StockScorer
from .deep_analysis import _strip_think

def _build_llm_client():
    cfg = DEFAULT_CONFIG.copy()
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    deep_model = os.getenv("LLM_DEEP_MODEL", "")
    quick_model = os.getenv("LLM_QUICK_MODEL", "")
    backend_url = os.getenv("BACKEND_URL") or None
    if deep_model:
        cfg["deep_think_llm"] = deep_model
    if quick_model:
        cfg["quick_think_llm"] = quick_model
    cfg["backend_url"] = backend_url
    model = cfg.get("quick_think_llm", "gpt-4o")
    return create_llm_client(provider, model, backend_url)

_SUBSECTOR_PROMPT = """给定主题 "{theme}"，列出 5-8 个最相关的子领域/细分方向。
每个子领域返回一个词或短语（如"AI芯片"、"电力基础设施"）。
只返回子领域名称，每行一个，不要编号，不要解释。"""

_STOCKSEL_PROMPT = """主题是 "{theme}"，子领域是 "{sub_sector}"。
以下候选股票池包含真实股票代码（不是子领域名称）：
{candidate_pool}

目标：从上述候选池中，选择 3-8 只与「{sub_sector}」最相关的真实股票代码。
规则：
- 必须从上述候选池中选择
- 只能返回股票代码（如 NVDA、AMD、AMZN）
- 不得返回子领域名称、$符号、或候选池中不存在的代码
- 每行一个代码，不要编号，不要解释"""

_REASONING_MARKERS = {
    "the user", "user is", "we need", "we can", "we must",
    "check any", "policy issue", "disallowed", "deliver",
    "no extra", "commentary", "subfield", "relevant",
    "but ", "so we", "that would", "within 5",
}

def _is_valid_sub_sector(text: str) -> bool:
    """Return True if text looks like a Chinese sub-sector name (not LLM reasoning)."""
    stripped = text.strip()
    if not stripped:
        return False
    if any(m in stripped.lower() for m in _REASONING_MARKERS):
        return False
    return len(re.findall(r'[\u4e00-\u9fff]', stripped)) >= 2

class ThemeScanner:
    """Scans stocks by theme using LLM-driven sub-sector decomposition."""

    def __init__(self):
        client = _build_llm_client()
        self._llm = client.get_llm()
        self._scorer = StockScorer()

    def _deduce_sub_sectors(self, theme: str) -> list[str]:
        prompt = _SUBSECTOR_PROMPT.format(theme=theme)
        response = self._llm.invoke(prompt)
        text = _strip_think(response.content if hasattr(response, "content") else str(response))
        subs = [line.strip() for line in text.splitlines() if _is_valid_sub_sector(line)]
        return subs[:8]

    def _select_stocks(self, theme: str, sub_sector: str) -> list[str]:
        pool_lines = "\n".join(f"{k}: {','.join(v)}" for k, v in THEME_CANDIDATE_POOL.items())
        prompt = _STOCKSEL_PROMPT.format(
            theme=theme,
            sub_sector=sub_sector,
            candidate_pool=pool_lines,
        )
        response = self._llm.invoke(prompt)
        text = _strip_think(response.content if hasattr(response, "content") else str(response))
        raw_tickers = [line.strip().upper() for line in text.splitlines() if line.strip()]
        # Filter to only tickers that actually exist in candidate pool
        valid_tickers = set()
        for ticker in raw_tickers:
            for candidates in THEME_CANDIDATE_POOL.values():
                if ticker in candidates:
                    valid_tickers.add(ticker)
                    break
        return list(valid_tickers)

    def scan(self, theme: str, top_n_per_sector: int = 3) -> dict:
        sub_sectors = self._deduce_sub_sectors(theme)
        results = []
        for sub in sub_sectors:
            tickers = self._select_stocks(theme, sub)
            if not tickers:
                continue
            scored = self._scorer.score_tickers(tickers, sector=sub)
            scored_dicts = [
                {**s.__dict__, "ticker": s.stock}
                for s in scored
            ]
            scored_dicts.sort(key=lambda x: x["composite"], reverse=True)
            results.append({
                "sub_sector": sub,
                "stocks": scored_dicts[:top_n_per_sector],
            })
        return {
            "theme": theme,
            "sub_sectors": results,
            "scan_date": __import__("datetime").date.today().isoformat(),
        }
