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
候选股票池（每行格式：子领域: ticker1,ticker2,...）：
{candidate_pool}

从候选池中选择 3-8 只与该子领域最相关的股票代码。
只返回股票代码，每行一个，不要编号，不要解释。"""


def _strip_think(text: str) -> str:
    text = re.sub(r'<think>.*?', '', text, flags=re.DOTALL).strip()
    text = re.sub(r'<think>.*', '', text, flags=re.DOTALL).strip()
    return text


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
        subs = [line.strip() for line in text.splitlines() if line.strip()]
        return subs

    def _select_stocks(self, theme: str, sub_sector: str) -> list[str]:
        pool_lines = "\n".join(f"{k}: {','.join(v)}" for k, v in THEME_CANDIDATE_POOL.items())
        prompt = _STOCKSEL_PROMPT.format(
            theme=theme,
            sub_sector=sub_sector,
            candidate_pool=pool_lines,
        )
        response = self._llm.invoke(prompt)
        text = _strip_think(response.content if hasattr(response, "content") else str(response))
        tickers = [line.strip().upper() for line in text.splitlines() if line.strip()]
        return tickers

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
