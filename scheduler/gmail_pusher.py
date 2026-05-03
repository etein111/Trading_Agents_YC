"""Gmail Pusher - sends analysis reports via Gmail."""

import html
import smtplib
import ssl
import os
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass
from typing import Optional


def _escape_html(text):
    """Escape HTML characters to prevent injection."""
    if isinstance(text, str):
        return html.escape(text)
    return str(text)


COLOR_BUY = "#2E7D32"     # green — positive values
COLOR_SELL = "#C62828"   # red — negative values
COLOR_NEUTRAL = "#1565C0" # blue — neutral/key metrics
COLOR_HEADER_BG = "#f0f4f8"


def _render_metrics_table(chart_data: dict) -> str:
    """Render chart_data dict as a compact HTML metrics table."""
    if not chart_data:
        return ""
    label_map = {
        "rsi": "RSI",
        "sma_20": "SMA20",
        "sma_50": "SMA50",
        "macd_signal": "MACD",
        "trend_direction": "Trend",
        "volume_change_pct": "Volume Δ",
        "sentiment_score": "Sentiment",
        "mention_volume": "Volume",
        "positive_pct": "Positive",
        "negative_pct": "Negative",
        "trend": "Trend",
        "news_count": "News #",
        "polarity": "Polarity",
        "sector_relevance_score": "Sector Relevance",
        "pe_ratio": "PE",
        "forward_pe": "Forward PE",
        "rev_growth": "Revenue Growth",
        "profit_margin": "Profit Margin",
        "eps": "EPS",
        "dividend_yield": "Dividend Yield",
        "bull_case_prob": "Bull %",
        "bear_case_prob": "Bear %",
        "risk_score": "Risk",
        "entry_price": "Entry",
        "target_price": "Target",
        "stop_loss": "Stop Loss",
        "position_size_pct": "Position",
        "risk_reward_ratio": "Risk:Reward",
        "rating": "Rating",
        "conviction_pct": "Conviction",
        "holding_period": "Holding",
    }
    rows = ""
    for key, label in label_map.items():
        val = chart_data.get(key)
        if val is None:
            continue
        val_str = str(val)
        if isinstance(val, (int, float)):
            color = COLOR_BUY if val > 0 else (COLOR_SELL if val < 0 else COLOR_NEUTRAL)
            val_str = f'<span style="color:{color}">{val_str}</span>'
        rows += f"<tr><td style='padding:3px 10px;font-weight:bold;font-size:12px'>{label}</td><td style='padding:3px 10px;font-size:12px'>{val_str}</td></tr>"
    if not rows:
        return ""
    return f"<table style='border-collapse:collapse;margin-top:6px;background:#fff'><tbody>{rows}</tbody></table>"


def _agent_section(label: str, summary: str, chart_data: dict, border_color: str) -> str:
    """Build one agent section with summary paragraph + metrics table."""
    if not summary:
        summary = "No data"
    metrics_html = _render_metrics_table(chart_data)
    metrics_block = f"<div style='margin-top:6px'>{metrics_html}</div>" if metrics_html else ""
    return f"""
    <div style='border-left:4px solid {border_color};padding:8px 12px;margin:6px 0;background:#fafafa'>
      <div style='font-size:13px;line-height:1.6;color:#333;white-space:pre-wrap'>{_escape_html(summary)}</div>
      {metrics_block}
    </div>"""


@dataclass
class EmailMessage:
    """Email message structure."""
    subject: str
    body: str
    to_email: str
    cc_email: Optional[str] = None


class GmailPusher:
    """Sends emails via Gmail SMTP."""

    def __init__(self, sender_email: str, recipient_email: str,
                 smtp_host: str = "smtp.gmail.com",
                 smtp_port: int = 465):
        self.sender_email = sender_email
        self.recipient_email = recipient_email
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port

    def _get_credentials(self) -> tuple[str, str]:
        """Get SMTP credentials from environment."""
        email_user = os.getenv("GMAIL_EMAIL")
        email_pass = os.getenv("GMAIL_APP_PASSWORD")
        if not email_user or not email_pass:
            raise ValueError(
                "Gmail credentials not set. Please set GMAIL_EMAIL and GMAIL_APP_PASSWORD environment variables."
            )
        return email_user, email_pass

    def send_email(self, message: EmailMessage) -> bool:
        """Send an email via Gmail SMTP over SSL (port 465)."""
        try:
            email_user, email_pass = self._get_credentials()

            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = message.to_email
            if message.cc_email:
                msg['Cc'] = message.cc_email
            msg['Subject'] = message.subject

            msg.attach(MIMEText(message.body, 'html'))

            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context) as server:
                server.login(email_user, email_pass)
                server.send_message(msg)

            return True
        except smtplib.SMTPException as e:
            print(f"Failed to send email: {e}")
            return False

    def send_with_retry(self, message: EmailMessage, max_retries: int = 3) -> bool:
        """Send email with retry logic."""
        delays = [5, 15, 60]  # minutes
        for attempt in range(max_retries):
            if self.send_email(message):
                return True
            if attempt < max_retries - 1:
                wait_time = delays[attempt] * 60
                print(f"Retry {attempt + 1}/{max_retries} in {delays[attempt]} minutes...")
                time.sleep(wait_time)
        return False

    def format_premarket_briefing(self, report: dict) -> EmailMessage:
        """Format premarket briefing email."""
        positions = report.get("positions", [])
        sentiment = report.get("sentiment", "neutral")
        events = report.get("events", [])

        # Build table rows
        rows = []
        for p in positions:
            ticker = _escape_html(p['ticker'])
            shares = _escape_html(str(p['shares']))
            price = _escape_html(str(p['entry_price']))
            rows.append(f"<tr><td style='padding:5px 10px'>{ticker}</td><td style='padding:5px 10px'>{shares}</td><td style='padding:5px 10px'>{price}</td></tr>")

        body = f"""
<div style="font-family:Arial,sans-serif;max-width:950px;margin:0 auto;padding:16px;background:#f5f5f5">
<div style="background:#fff;padding:16px 20px;border-radius:8px">
<h2 style="margin-top:0;color:#333">Pre-market Briefing</h2>

<h3 style="color:#555">Portfolio Positions</h3>
<table style="border-collapse:collapse;width:100%;background:#fff;border:1px solid #ddd">
  <tr style="background:{COLOR_HEADER_BG};padding:6px 10px"><th style="padding:6px 10px;text-align:left">Ticker</th><th style="padding:6px 10px;text-align:left">Shares</th><th style="padding:6px 10px;text-align:left">Entry Price</th></tr>
  {''.join(rows)}
</table>

<h3 style="color:#555">Market Sentiment</h3>
<p>{_escape_html(sentiment.upper())}</p>

<h3 style="color:#555">Key Events Today</h3>
<ul>
{''.join(f"<li style='padding:3px 0'>{_escape_html(e)}</li>" for e in events)}
</ul>

<p style="color:#888;font-size:12px;margin-bottom:0"><em>Generated by TradingAgents</em></p>
</div>
</div>"""

        return EmailMessage(
            subject=f"Pre-market Briefing - {_escape_html(report.get('date', 'Today'))}",
            body=body,
            to_email=self.recipient_email
        )

    def format_afterhours_report(self, report: dict) -> EmailMessage:
        """Format after-hours report email."""
        positions = report.get("positions", [])
        analysis = report.get("analysis", "")

        # Build table rows
        rows = []
        for p in positions:
            ticker = _escape_html(p['ticker'])
            shares = _escape_html(str(p['shares']))
            current = _escape_html(p.get('current_price', 'N/A'))
            action = _escape_html(p.get('action', 'Hold'))
            rows.append(f"<tr><td style='padding:5px 10px'>{ticker}</td><td style='padding:5px 10px'>{shares}</td><td style='padding:5px 10px'>{current}</td><td style='padding:5px 10px'>{action}</td></tr>")

        body = f"""
<div style="font-family:Arial,sans-serif;max-width:950px;margin:0 auto;padding:16px;background:#f5f5f5">
<div style="background:#fff;padding:16px 20px;border-radius:8px">
<h2 style="margin-top:0;color:#333">After-hours Report</h2>

<h3 style="color:#555">Portfolio Performance</h3>
<table style="border-collapse:collapse;width:100%;background:#fff;border:1px solid #ddd">
  <tr style="background:{COLOR_HEADER_BG};padding:6px 10px"><th style="padding:6px 10px;text-align:left">Ticker</th><th style="padding:6px 10px;text-align:left">Shares</th><th style="padding:6px 10px;text-align:left">Current/Pivot</th><th style="padding:6px 10px;text-align:left">Action</th></tr>
  {''.join(rows)}
</table>

<h3 style="color:#555">Analysis Summary</h3>
<p>{_escape_html(analysis)}</p>

<p style="color:#888;font-size:12px;margin-bottom:0"><em>Generated by TradingAgents</em></p>
</div>
</div>"""

        return EmailMessage(
            subject=f"After-hours Report - {_escape_html(report.get('date', 'Today'))}",
            body=body,
            to_email=self.recipient_email
        )

    def format_screener_report(self, report: dict) -> "EmailMessage":
        """Format full stock screener + portfolio rebalancer report as HTML email."""
        scan_date = report.get("scan_date", "")
        sectors = report.get("sector_rankings", [])
        all_stocks = report.get("all_stocks", [])
        top_by_sector = report.get("top_by_sector", {})
        adjustments = report.get("adjustments", [])
        unchanged = report.get("unchanged", [])
        anomalies = report.get("anomalies", [])
        positions = report.get("portfolio_positions", [])

        # --- Anomaly alerts (top of report) ---
        anomaly_section = ""
        if anomalies:
            anomaly_rows = ""
            for a in anomalies:
                severity_color = {"high": "red", "medium": "orange", "low": "gray"}.get(a.get("severity", "medium"), "gray")
                anomaly_rows += f"""
                <tr style="color:{severity_color}">
                  <td style="padding:5px 10px"><strong>{_escape_html(a.get('sector', ''))}</strong></td>
                  <td style="padding:5px 10px"><strong>{_escape_html(a.get('signal', ''))}</strong></td>
                  <td style="padding:5px 10px">{_escape_html(a.get('description', ''))}</td>
                  <td style="padding:5px 10px">{_escape_html(a.get('data_source', ''))}</td>
                  <td style="padding:5px 10px">{_escape_html(a.get('severity', 'medium').upper())}</td>
                </tr>"""
            anomaly_section = f"""
<div style="border:2px solid #C62828;padding:10px;margin:10px 0;border-radius:5px;background:#fff">
<h2 style="color:#C62828;margin-top:0">异动板块提醒</h2>
<table style="border-collapse:collapse;width:100%;background:#fff;border:1px solid #ddd">
  <tr style="background:{COLOR_HEADER_BG};padding:6px 10px"><th style="padding:6px 10px;text-align:left">板块</th><th style="padding:6px 10px;text-align:left">信号类型</th><th style="padding:6px 10px;text-align:left">描述</th><th style="padding:6px 10px;text-align:left">数据来源</th><th style="padding:6px 10px;text-align:left">严重程度</th></tr>
  {anomaly_rows}
</table>
</div>"""

        # --- Sector table ---
        sector_rows = ""
        for s in sectors:
            b = s.get("breakdown", {})
            sector_rows += f"""
        <tr>
          <td style="padding:5px 10px">{s['rank']}</td>
          <td style="padding:5px 10px"><strong>{_escape_html(s['name'])}</strong></td>
          <td style="padding:5px 10px"><strong>{s['score']:.3f}</strong></td>
          <td style="padding:5px 10px">{b.get('momentum', '-'):.3f}</td>
          <td style="padding:5px 10px">{b.get('valuation', '-'):.3f}</td>
          <td style="padding:5px 10px">{b.get('macro', '-'):.3f}</td>
          <td style="padding:5px 10px">{b.get('fundamentals', '-'):.3f}</td>
        </tr>"""
        sectors_table = f"""
<div style="background:#fff;padding:16px 20px;border-radius:8px">
<h2 style="margin-top:0;color:#333">一、板块扫描结果</h2>
<p>权重方法: A(动量)×0.4 + B(估值)×0.3 + E(宏观)×0.2 + C(基本面)×0.1</p>
<table style="border-collapse:collapse;width:100%;background:#fff;border:1px solid #ddd">
  <tr style="background:{COLOR_HEADER_BG};padding:6px 10px"><th style="padding:6px 10px;text-align:left">排名</th><th style="padding:6px 10px;text-align:left">板块</th><th style="padding:6px 10px;text-align:left">综合得分</th><th style="padding:6px 10px;text-align:left">动量(A)</th><th style="padding:6px 10px;text-align:left">估值(B)</th><th style="padding:6px 10px;text-align:left">宏观(E)</th><th style="padding:6px 10px;text-align:left">基本面(C)</th></tr>
  {sector_rows}
</table>
</div>"""

        # --- Individual stock recommendations (top 3 per sector) ---
        stock_rows = ""
        for sector_name, stocks in top_by_sector.items():
            for stock_data in stocks:
                scores = stock_data.get("scores", {})
                stock_rows += f"""
        <tr>
          <td style="padding:5px 10px"><strong>{_escape_html(stock_data.get('stock', ''))}</strong></td>
          <td style="padding:5px 10px">{_escape_html(sector_name)}</td>
          <td style="padding:5px 10px"><strong>{stock_data.get('composite', 0):.3f}</strong></td>
          <td style="padding:5px 10px">{scores.get('momentum', '-')}</td>
          <td style="padding:5px 10px">{scores.get('valuation', '-')}</td>
          <td style="padding:5px 10px">{scores.get('macro', '-')}</td>
          <td style="padding:5px 10px">{scores.get('fundamentals', '-')}</td>
          <td style="padding:5px 10px">{_escape_html(stock_data.get('rating', ''))}</td>
        </tr>"""
        stocks_table = f"""
<div style="background:#fff;padding:16px 20px;border-radius:8px">
<h2 style="margin-top:0;color:#333">二、个股推荐（每板块 Top 3）</h2>
<table style="border-collapse:collapse;width:100%;background:#fff;border:1px solid #ddd">
  <tr style="background:{COLOR_HEADER_BG};padding:6px 10px"><th style="padding:6px 10px;text-align:left">股票</th><th style="padding:6px 10px;text-align:left">板块</th><th style="padding:6px 10px;text-align:left">综合得分</th><th style="padding:6px 10px;text-align:left">动量</th><th style="padding:6px 10px;text-align:left">估值</th><th style="padding:6px 10px;text-align:left">宏观</th><th style="padding:6px 10px;text-align:left">基本面</th><th style="padding:6px 10px;text-align:left">评级</th></tr>
  {stock_rows}
</table>
</div>"""

        # --- Portfolio positions ---
        pos_section = ""
        if positions:
            pos_rows = ""
            total_value = 0
            for p in positions:
                value = p.get("shares", 0) * p.get("entry_price", 0)
                total_value += value
                pos_rows += f"""
        <tr>
          <td style="padding:5px 10px">{_escape_html(p.get('ticker', ''))}</td>
          <td style="padding:5px 10px">{p.get('shares', 0)}</td>
          <td style="padding:5px 10px">${p.get('entry_price', 0):.2f}</td>
          <td style="padding:5px 10px">${value:.2f}</td>
          <td style="padding:5px 10px">{_escape_html(p.get('broker', ''))}</td>
        </tr>"""
            pos_section = f"""
<div style="background:#fff;padding:16px 20px;border-radius:8px">
<h2 style="margin-top:0;color:#333">三、现有持仓</h2>
<p>总持仓市值: <strong>${total_value:.2f}</strong></p>
<table style="border-collapse:collapse;width:100%;background:#fff;border:1px solid #ddd">
  <tr style="background:{COLOR_HEADER_BG};padding:6px 10px"><th style="padding:6px 10px;text-align:left">股票</th><th style="padding:6px 10px;text-align:left">股数</th><th style="padding:6px 10px;text-align:left">买入价</th><th style="padding:6px 10px;text-align:left">市值</th><th style="padding:6px 10px;text-align:left">券商</th></tr>
  {pos_rows}
</table>
</div>"""

        # --- Adjustments ---
        reduce_rows = "".join(
            f"<tr><td style='padding:5px 10px'>{_escape_html(a['ticker'])}</td><td style='padding:5px 10px'>{a['current_shares']}</td><td style='padding:5px 10px'>减至{a['recommended_shares']}股</td><td style='padding:5px 10px'>{_escape_html(a.get('reason', ''))}</td></tr>"
            for a in adjustments if a["action"] in ("REDUCE", "ADD")
        )
        new_rows = "".join(
            f"<tr><td style='padding:5px 10px'>{_escape_html(a['ticker'])}</td><td style='padding:5px 10px'>建议新建仓{a['recommended_shares']}股</td><td style='padding:5px 10px'>{_escape_html(a.get('reason', ''))}</td></tr>"
            for a in adjustments if a["action"] == "NEW"
        )
        hold_rows = "".join(
            f"<tr><td style='padding:5px 10px'>{_escape_html(u['ticker'])}</td><td style='padding:5px 10px'>{_escape_html(u.get('reason', ''))}</td></tr>"
            for u in unchanged
        )
        adjustments_section = f"""
<div style="background:#fff;padding:16px 20px;border-radius:8px">
<h2 style="margin-top:0;color:#333">四、持仓调整建议</h2>
{('<h3>建议减仓</h3><table style="border-collapse:collapse;width:100%;background:#fff;border:1px solid #ddd"><tr style="background:' + COLOR_HEADER_BG + ';padding:6px 10px"><th style="padding:6px 10px;text-align:left">股票</th><th style="padding:6px 10px;text-align:left">当前持仓</th><th style="padding:6px 10px;text-align:left">建议</th><th style="padding:6px 10px;text-align:left">原因</th></tr>' + reduce_rows + '</table>' if reduce_rows else '<p>无减仓建议</p>')}
{('<h3>新建仓机会</h3><table style="border-collapse:collapse;width:100%;background:#fff;border:1px solid #ddd"><tr style="background:' + COLOR_HEADER_BG + ';padding:6px 10px"><th style="padding:6px 10px;text-align:left">股票</th><th style="padding:6px 10px;text-align:left">建议</th><th style="padding:6px 10px;text-align:left">原因</th></tr>' + new_rows + '</table>' if new_rows else '')}
{('<h3>持仓不变</h3><table style="border-collapse:collapse;width:100%;background:#fff;border:1px solid #ddd"><tr style="background:' + COLOR_HEADER_BG + ';padding:6px 10px"><th style="padding:6px 10px;text-align:left">股票</th><th style="padding:6px 10px;text-align:left">原因</th></tr>' + hold_rows + '</table>' if hold_rows else '')}
</div>"""

        body = f"""
<div style="font-family:Arial,sans-serif;max-width:950px;margin:0 auto;padding:16px;background:#f5f5f5">
<h1 style="color:#333">Daily Stock Screener & Portfolio Rebalancer</h1>
<p><em>扫描日期: {scan_date} | 报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}</em></p>
{anomaly_section}
{sectors_table}
{stocks_table}
{pos_section}
{adjustments_section}
<p style="margin-top:20px"><em>Generated by TradingAgents Stock Screener | 权重: A×0.4 + B×0.3 + E×0.2 + C×0.1</em></p>
</div>
"""
        return EmailMessage(
            subject=f"[TradingAgents] Stock Screener Report — {scan_date}",
            body=body,
            to_email=self.recipient_email,
        )

    def format_deep_screener_report(self, report: dict) -> "EmailMessage":
        """Full report with per-stock TradingAgents analysis + decision layers."""
        scan_date = report.get("scan_date", "")
        deep_stocks = report.get("deep_stocks", [])
        sector_rankings = report.get("sector_rankings", [])
        anomalies = report.get("anomalies", [])
        portfolio_positions = report.get("portfolio_positions", [])
        adjustments = report.get("adjustments", [])
        unchanged = report.get("unchanged", [])

        # --- Anomaly alerts ---
        anomaly_section = ""
        if anomalies:
            anomaly_rows = ""
            for a in anomalies:
                severity_color = {"high": "red", "medium": "orange", "low": "gray"}.get(
                    a.get("severity", "medium"), "gray"
                )
                anomaly_rows += f"""
                <tr style="color:{severity_color}">
                  <td><strong>{html.escape(a.get('sector', ''))}</strong></td>
                  <td><strong>{html.escape(a.get('signal', ''))}</strong></td>
                  <td>{html.escape(a.get('description', ''))}</td>
                  <td>{html.escape(a.get('data_source', ''))}</td>
                  <td>{html.escape(a.get('severity', 'medium').upper())}</td>
                </tr>"""
            anomaly_section = f"""
    <div style="border:2px solid red;padding:10px;margin:10px 0;border-radius:5px">
    <h2 style="color:red;margin-top:0">异动板块提醒</h2>
    <table border='1' cellpadding='5' cellspacing='0'>
      <tr><th>板块</th><th>信号类型</th><th>描述</th><th>数据来源</th><th>严重程度</th></tr>
      {anomaly_rows}
    </table>
    </div>"""

        # --- Sector table ---
        sector_rows = ""
        for s in sector_rankings:
            b = s.get("breakdown", {})
            sector_rows += f"""
        <tr style="background:{COLOR_HEADER_BG}">
          <td style="padding:5px">{s['rank']}</td>
          <td style="padding:5px"><strong>{html.escape(s['name'])}</strong></td>
          <td style="padding:5px"><strong>{s['score']:.3f}</strong></td>
          <td style="padding:5px">{b.get('momentum', '-'):.3f}</td>
          <td style="padding:5px">{b.get('valuation', '-'):.3f}</td>
          <td style="padding:5px">{b.get('macro', '-'):.3f}</td>
          <td style="padding:5px">{b.get('fundamentals', '-'):.3f}</td>
        </tr>"""
        sectors_table = f"""
    <h2>一、板块扫描结果</h2>
    <p>权重方法: A(动量)×0.4 + B(估值)×0.3 + E(宏观)×0.2 + C(基本面)×0.1</p>
    <table style="border-collapse:collapse;width:100%" border='1' cellpadding='5' cellspacing='0'>
      <tr style="background:{COLOR_HEADER_BG}"><th style="padding:5px">排名</th><th style="padding:5px">板块</th><th style="padding:5px">综合得分</th><th style="padding:5px">动量(A)</th><th style="padding:5px">估值(B)</th><th style="padding:5px">宏观(E)</th><th style="padding:5px">基本面(C)</th></tr>
      {sector_rows}
    </table>"""

        # --- Per-stock deep agent analysis ---
        stock_sections = ""
        for stock in deep_stocks:
            if stock.get("error"):
                stock_sections += f"""
        <div style="border:1px solid #ccc;padding:15px;margin:15px 0;background:#fff3f3">
        <h2>{html.escape(stock['ticker'])} — {html.escape(stock['sector'])}</h2>
        <p style="color:red">Error: {html.escape(stock['error'])}</p>
        </div>"""
                continue

            ticker = html.escape(stock.get('ticker', ''))
            sector = html.escape(stock.get('sector', ''))
            composite = stock.get('composite_score', 0)
            rating = stock.get('rating', 'Hold')
            rating_color = {
                "Buy": COLOR_BUY, "Overweight": COLOR_NEUTRAL, "Hold": "gray",
                "Underweight": "#E65100", "Sell": COLOR_SELL
            }.get(rating, "gray")
            rating_badge = f"<span style='background:{rating_color};color:#fff;padding:2px 8px;border-radius:10px;font-size:12px'>{html.escape(rating)}</span>"

            # Build stock header
            stock_header = f"""
        <div style="border:1px solid #333;padding:15px;margin:15px 0;border-radius:8px;background:#fff">
          <h2 style="color:#1a1a1a;margin:0 0 8px">{ticker} — {sector}</h2>
          <p style="font-size:13px;margin:0">
            综合得分: <strong>{composite:.3f}</strong> &nbsp;|&nbsp; 评级: {rating_badge}
          </p>
        </div>"""

            # 7 agent sections using _agent_section helper
            market_sec = _agent_section(
                "技术面",
                stock.get("market_summary", ""),
                stock.get("market_chart_data", {}),
                "#1565C0"
            )
            sentiment_sec = _agent_section(
                "情绪面",
                stock.get("sentiment_summary", ""),
                stock.get("sentiment_chart_data", {}),
                "#6A1B9A"
            )
            news_sec = _agent_section(
                "宏观/新闻面",
                stock.get("news_summary", ""),
                stock.get("news_chart_data", {}),
                "#E65100"
            )
            fundamentals_sec = _agent_section(
                "基本面",
                stock.get("fundamentals_summary", ""),
                stock.get("fundamentals_chart_data", {}),
                "#2E7D32"
            )
            research_sec = _agent_section(
                "研究结论",
                stock.get("investment_plan_summary", ""),
                {},
                "#0277BD"
            )
            trader_sec = _agent_section(
                "交易计划",
                stock.get("trader_plan_summary", ""),
                {},
                "#33691E"
            )
            decision_sec = _agent_section(
                "最终决策",
                stock.get("final_decision_summary", ""),
                {},
                "#BF360C"
            )

            stock_sections += stock_header + market_sec + sentiment_sec + news_sec + fundamentals_sec + research_sec + trader_sec + decision_sec

        # --- Portfolio positions ---
        pos_section = ""
        if portfolio_positions:
            pos_rows = ""
            total_value = 0
            for p in portfolio_positions:
                value = p.get("shares", 0) * p.get("entry_price", 0)
                total_value += value
                pos_rows += f"""
        <tr>
          <td>{html.escape(p.get('ticker', ''))}</td>
          <td>{p.get('shares', 0)}</td>
          <td>${p.get('entry_price', 0):.2f}</td>
          <td>${value:.2f}</td>
          <td>{html.escape(p.get('broker', ''))}</td>
        </tr>"""
            pos_section = f"""
    <h2 style="margin-top:30px">三、现有持仓</h2>
    <p>总持仓市值: <strong>${total_value:.2f}</strong></p>
    <table border='1' cellpadding='5' cellspacing='0'>
      <tr><th>股票</th><th>股数</th><th>买入价</th><th>市值</th><th>券商</th></tr>
      {pos_rows}
    </table>"""

        # --- Adjustments ---
        reduce_rows = "".join(
            f"<tr><td>{html.escape(a['ticker'])}</td><td>{a['current_shares']}</td>"
            f"<td>减至{a['recommended_shares']}股</td><td>{html.escape(a.get('reason', ''))}</td></tr>"
            for a in adjustments if a["action"] in ("REDUCE", "ADD")
        )
        new_rows = "".join(
            f"<tr><td>{html.escape(a['ticker'])}</td><td>建议新建仓{a['recommended_shares']}股</td>"
            f"<td>{html.escape(a.get('reason', ''))}</td></tr>"
            for a in adjustments if a["action"] == "NEW"
        )
        hold_rows = "".join(
            f"<tr><td>{html.escape(u['ticker'])}</td><td>{html.escape(u.get('reason', ''))}</td></tr>"
            for u in unchanged
        )
        adjustments_section = f"""
    <h2 style="margin-top:30px">四、持仓调整建议</h2>
    {('<h3>建议减仓</h3><table border="1" cellpadding="5" cellspacing="0"><tr><th>股票</th><th>当前持仓</th><th>建议</th><th>原因</th></tr>' + reduce_rows + '</table>' if reduce_rows else '<p>无减仓建议</p>')}
    {('<h3>新建仓机会</h3><table border="1" cellpadding="5" cellspacing="0"><tr><th>股票</th><th>建议</th><th>原因</th></tr>' + new_rows + '</table>' if new_rows else '')}
    {('<h3>持仓不变</h3><table border="1" cellpadding="5" cellspacing="0"><tr><th>股票</th><th>原因</th></tr>' + hold_rows + '</table>' if hold_rows else '')}"""

        body = f"""
    <div style="font-family:Arial,sans-serif;max-width:950px">
    <h1 style="color:#333">Daily Stock Screener & Agent Analysis</h1>
    <p><em>扫描日期: {scan_date} | 报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}</em></p>
    {anomaly_section}
    {sectors_table}
    <h2 style="margin-top:30px">二、Top 8 个股深度 Agent 分析</h2>
    <p>每只股票经过: Market Analyst → Social Media Analyst → News Analyst → Fundamentals Analyst → Research Manager → Trader → Portfolio Manager</p>
    {stock_sections}
    {pos_section}
    {adjustments_section}
    <p style="margin-top:20px"><em>Generated by TradingAgents Stock Screener | 权重: A×0.4 + B×0.3 + E×0.2 + C×0.1</em></p>
    </div>"""
        return EmailMessage(
            subject=f"[TradingAgents] Stock Screener — {scan_date}",
            body=body,
            to_email=self.recipient_email,
        )

    def format_weekly_report(self, report: dict) -> EmailMessage:
        """Format weekly comprehensive report."""
        portfolio_value = report.get("portfolio_value", 0)
        gain_loss = report.get("gain_loss", 0)
        positions = report.get("positions", [])
        recommendations = report.get("recommendations", [])

        gl_color = 'green' if gain_loss >= 0 else 'red'
        gl_formatted = f"${gain_loss:.2f}"

        rows = []
        for p in positions:
            ticker = html.escape(p['ticker'])
            shares = html.escape(str(p['shares']))
            entry = html.escape(f"${p['entry_price']:.2f}")
            current = html.escape(p.get('current_price', 'N/A'))
            pnl = p.get('pnl', 0)
            pnl_color = 'green' if pnl >= 0 else 'red'
            pnl_formatted = html.escape(f"${pnl:.2f}")
            rec = html.escape(p.get('recommendation', 'Hold'))
            rows.append(f"<tr><td>{ticker}</td><td>{shares}</td><td>{entry}</td><td>{current}</td><td style='color: {pnl_color}'>{pnl_formatted}</td><td>{rec}</td></tr>")

        body = f"""
        <h2>Weekly Portfolio Report</h2>

        <h3>Portfolio Summary</h3>
        <p>Total Value: <strong>{html.escape(f"${portfolio_value:.2f}")}</strong></p>
        <p>Gain/Loss: <strong style="color: {gl_color}">{gl_formatted}</strong></p>

        <h3>Current Positions</h3>
        <table border="1" cellpadding="5" cellspacing="0">
            <tr><th>Ticker</th><th>Shares</th><th>Entry</th><th>Current</th><th>P/L</th><th>Action</th></tr>
            {''.join(rows)}
        </table>

        <h3>Recommendations</h3>
        <ul>
            {''.join(f"<li>{html.escape(r)}</li>" for r in recommendations)}
        </ul>

        <h3>Market Outlook</h3>
        <p>{html.escape(report.get('market_outlook', 'No data available'))}</p>

        <p><em>Generated by TradingAgents - Weekly Analysis</em></p>
        """

        return EmailMessage(
            subject=f"Weekly Portfolio Report - {html.escape(report.get('week', 'This Week'))}",
            body=body,
            to_email=self.recipient_email
        )