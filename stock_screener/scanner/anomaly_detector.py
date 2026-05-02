from dataclasses import dataclass
from typing import Optional


@dataclass
class Anomaly:
    sector: str
    signal: str  # "etf_net_inflow" | "price_breakout" | "policy_catalyst" | "institutional_building"
    description: str
    data_source: str
    severity: str = "medium"  # "low" | "medium" | "high"


class AnomalyDetector:
    """Detects anomalous sector activity across multiple signal types."""

    def __init__(self, etf_volume_data: Optional[dict] = None,
                 etf_price_data: Optional[dict] = None,
                 policy_events: Optional[list] = None,
                 insider_data: Optional[dict] = None):
        self.etf_volume_data = etf_volume_data or {}
        self.etf_price_data = etf_price_data or {}
        self.policy_events = policy_events or []
        self.insider_data = insider_data or {}
        # All detection methods handle None/empty inputs gracefully

    def detect(self) -> list[Anomaly]:
        anomalies = []
        anomalies.extend(self._check_etf_net_inflow())
        anomalies.extend(self._check_price_breakout())
        anomalies.extend(self._check_policy_catalyst())
        anomalies.extend(self._check_institutional_building())
        return anomalies

    def _check_etf_net_inflow(self) -> list[Anomaly]:
        """ETF volume > 3x 5-day average = unusual institutional interest."""
        results = []
        for sector, volumes in self.etf_volume_data.items():
            if len(volumes) < 5:
                continue
            avg = sum(volumes[:-2]) / max(len(volumes[:-2]), 1)
            recent = volumes[-1]
            if avg > 0 and recent > avg * 3:
                results.append(Anomaly(
                    sector=sector,
                    signal="etf_net_inflow",
                    description=f"ETF净流入激增: 近期日均{recent:.0f}股 vs 历史均值{avg:.0f}股 ({(recent/avg):.1f}x)",
                    data_source="yfinance ETF.history(volume=True)",
                    severity="high" if recent > avg * 5 else "medium",
                ))
        return results

    def _check_price_breakout(self) -> list[Anomaly]:
        """Price breakout above 50-day high."""
        results = []
        for sector, prices in self.etf_price_data.items():
            if len(prices) < 50:
                continue
            current = prices[-1]
            high_50d = max(prices[:-1])
            if current > high_50d * 1.02:
                results.append(Anomaly(
                    sector=sector,
                    signal="price_breakout",
                    description=f"价格突破50日高点: 当前${current:.2f} vs 50日高${high_50d:.2f}",
                    data_source="yfinance ETF.history(close=True)",
                    severity="medium",
                ))
        return results

    def _check_policy_catalyst(self) -> list[Anomaly]:
        """First-time policy coverage for a sector."""
        results = []
        sector_keywords = {
            "Technology": ["antitrust", "AI regulation", "data privacy", "CHIPS Act"],
            "Healthcare": ["drug pricing", "Medicare", "FDA approval", "health policy"],
            "Energy": ["OPEC", "carbon tax", "renewable subsidy", "oil reserve"],
            "Finance": ["interest rate", "bank regulation", "Dodd-Frank", "Basel"],
        }
        for event in self.policy_events:
            sector = event.get("sector", "")
            text = event.get("event", "")
            keywords = sector_keywords.get(sector, [])
            for kw in keywords:
                if kw.lower() in text.lower() and kw not in event.get("_seen", []):
                    results.append(Anomaly(
                        sector=sector,
                        signal="policy_catalyst",
                        description=f"政策催化: {kw} — {text[:80]}",
                        data_source="News Analyst output",
                        severity="high",
                    ))
                    break
        return results

    def _check_institutional_building(self) -> list[Anomaly]:
        """Large net insider buys in sector."""
        results = []
        for sector, data in self.insider_data.items():
            net = data.get("net_shares", 0)
            tx_count = data.get("transactions", 0)
            if net > 1_000_000 and tx_count > 5:
                results.append(Anomaly(
                    sector=sector,
                    signal="institutional_building",
                    description=f"机构持仓大幅增加: 净买入{net:,.0f}股, {tx_count}笔交易",
                    data_source="yfinance insider_transactions + 13F filings",
                    severity="high" if net > 5_000_000 else "medium",
                ))
        return results
