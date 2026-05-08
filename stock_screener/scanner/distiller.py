"""Distill raw agent reports into concise summaries + structured chart_data."""

import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent.parent.parent.parent.parent / ".env")

from tradingagents.llm_clients.factory import create_llm_client
from tradingagents.default_config import DEFAULT_CONFIG


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
    model = cfg.get("deep_think_llm", "gpt-4o")
    return create_llm_client(provider, model, backend_url)


_PROMPT_TEMPLATES = {
    "market": """You are a financial analyst summarizing a Market Analyst report.

Raw report:
{raw_report}

Return a JSON object:
{{
  "summary": "3-5 sentence ~100-word summary in Chinese highlighting RSI, MACD, moving averages, trend, volume",
  "chart_data": {{
    "rsi": <float or null>,
    "sma_20": <float or null>,
    "sma_50": <float or null>,
    "macd_signal": "<golden_cross|death_cross|neutral or null>",
    "trend_direction": "<bullish|bearish|neutral or null>",
    "volume_change_pct": "<e.g. '+23%' or null>"
  }}
}}

Return ONLY valid JSON. Do NOT use <think> tags — return plain JSON only.""",

    "social": """You are a financial analyst summarizing a Social Media Analyst report.

Raw report:
{raw_report}

Return JSON:
{{
  "summary": "~100-word summary in Chinese of social sentiment and investor mood",
  "chart_data": {{
    "sentiment_score": <float 0-1 or null>,
    "mention_volume": "<volume description or null>",
    "positive_pct": "<e.g. '68%' or null>",
    "negative_pct": "<e.g. '22%' or null>",
    "trend": "<bullish|bearish|neutral or null>"
  }}
}}

Return ONLY valid JSON. Do NOT use <think> tags — return plain JSON only.""",

    "news": """You are a financial analyst summarizing a News Analyst report.

Raw report:
{raw_report}

Return JSON:
{{
  "summary": "~100-word summary in Chinese of news and macro factors",
  "chart_data": {{
    "news_count": <int or null>,
    "polarity": <float -1 to 1 or null>,
    "sector_relevance_score": "<high|medium|low or null>"
  }}
}}

Return ONLY valid JSON. Do NOT use <think> tags — return plain JSON only.""",

    "fundamentals": """You are a financial analyst summarizing a Fundamentals Analyst report.

Raw report:
{raw_report}

Return JSON:
{{
  "summary": "~100-word summary in Chinese of financial health and valuation",
  "chart_data": {{
    "pe_ratio": <float or null>,
    "forward_pe": <float or null>,
    "rev_growth": "<e.g. '23%' or null>",
    "profit_margin": "<e.g. '18%' or null>",
    "eps": <float or null>,
    "dividend_yield": "<e.g. '2.1%' or null>"
  }}
}}

Return ONLY valid JSON. Do NOT use <think> tags — return plain JSON only.""",

    "research": """You are a financial analyst summarizing a Research Manager investment plan.

Raw report:
{raw_report}

Return JSON:
{{
  "summary": "~100-word summary in Chinese of bull/bear case and risk assessment",
  "chart_data": {{
    "bull_case_prob": "<e.g. '65%' or null>",
    "bear_case_prob": "<e.g. '35%' or null>",
    "risk_score": "<high|medium|low or null>"
  }}
}}

Return ONLY valid JSON. Do NOT use <think> tags — return plain JSON only.""",

    "trader": """You are a financial analyst summarizing a Trader investment plan.

Raw report:
{raw_report}

Return JSON:
{{
  "summary": "~100-word summary in Chinese of entry strategy and risk/reward",
  "chart_data": {{
    "entry_price": <float or null>,
    "target_price": <float or null>,
    "stop_loss": <float or null>,
    "position_size_pct": "<e.g. '5%' or null>",
    "risk_reward_ratio": "<e.g. '2.5:1' or null>"
  }}
}}

Return ONLY valid JSON. Do NOT use <think> tags — return plain JSON only.""",

    "portfolio_manager": """You are a financial analyst summarizing a Portfolio Manager final decision.

Raw report:
{raw_report}

Return JSON:
{{
  "summary": "~100-word summary in Chinese of rating rationale and key thesis",
  "chart_data": {{
    "rating": "<Buy|Hold|Sell|Overweight|Underweight or null>",
    "conviction_pct": "<e.g. '78%' or null>",
    "holding_period": "<e.g. '3-6 months' or null>"
  }}
}}

Return ONLY valid JSON. Do NOT use <think> tags — return plain JSON only.""",
}


def _find_all_json_objects(text: str) -> list[dict]:
    """Find all balanced JSON objects in text. Returns list of parsed dicts."""
    objects = []
    search_pos = 0
    while search_pos < len(text):
        brace_pos = text.find('{', search_pos)
        if brace_pos < 0:
            break
        depth = 0
        obj_end = -1
        for i in range(brace_pos, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    obj_end = i
                    break
        if obj_end >= 0:
            candidate_text = text[brace_pos:obj_end + 1]
            try:
                candidate = json.loads(candidate_text)
                objects.append(candidate)
            except json.JSONDecodeError:
                pass
            search_pos = obj_end + 1
        else:
            break
    return objects


class Distiller:
    def __init__(self):
        self._raw_client = _build_llm_client()
        self._llm = self._raw_client.get_llm()

    def distill(self, raw_report: str, agent_name: str) -> dict:
        if not raw_report or not raw_report.strip():
            return {"summary": "No data available.", "chart_data": {}}

        template = _PROMPT_TEMPLATES.get(agent_name, _PROMPT_TEMPLATES["market"])
        prompt = template.format(raw_report=raw_report)

        try:
            response = self._llm.invoke(prompt)
            text = response.content if hasattr(response, "content") else str(response)
            # Remove <think>... blocks (non-greedy first, then greedy for unclosed trailing tag)
            text = re.sub(r'<think>.*?', '', text, flags=re.DOTALL).strip()
            text = re.sub(r'<think>.*', '', text, flags=re.DOTALL).strip()

            # Find ALL balanced JSON objects in the stripped text.
            # The LLM may embed the schema example as the first JSON and the actual
            # response as a later JSON — use the LAST one that has both required keys.
            all_objs = _find_all_json_objects(text)

            # Find all candidates with both required keys; prefer the LAST
            parsed = None
            for candidate in all_objs:
                if "summary" in candidate and "chart_data" in candidate:
                    parsed = candidate  # keep overwriting → LAST wins

            # Fallback: if no object had both keys, try regex extraction of summary + chart_data
            if parsed is None:
                chart_data = {}
                for kv_match in re.finditer(r'"(\w+)"\s*:\s*([0-9."+-]+)', text):
                    k, v = kv_match.group(1), kv_match.group(2)
                    try:
                        chart_data[k] = int(v) if v.lstrip('-').isdigit() else float(v)
                    except ValueError:
                        chart_data[k] = v.strip('"')

                summary_candidates = [
                    m.group(1) for m in re.finditer(r'"summary"\s*:\s*"(.*?)"', text, re.DOTALL)
                ]
                if summary_candidates:
                    parsed = {"summary": summary_candidates[-1], "chart_data": chart_data}

            if parsed is None:
                print(f"[Distiller] {agent_name}: no valid JSON with required keys found")
                return {"summary": "No data available.", "chart_data": {}}

            if "summary" not in parsed or "chart_data" not in parsed:
                print(f"[Distiller] {agent_name}: valid JSON but missing keys")
                return {"summary": "No data available.", "chart_data": {}}

            return parsed
        except (json.JSONDecodeError, Exception) as e:
            print(f"[Distiller] {agent_name}: exception {e}")
            return {"summary": "No data available.", "chart_data": {}}