# US Stock Investment Analysis System - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a hybrid investment analysis system combining TradingAgents CLI for interactive queries with a background scheduler for automated daily/weekly Gmail reports.

**Architecture:** Phase 1 builds a local portfolio manager + CLI commands for position tracking and stock analysis. Phase 2 adds Gmail integration for sending reports. Phase 3 implements the background scheduler for automated daily/weekly pushes. Phase 4 adds real-time monitoring.

**Tech Stack:** Python, TradingAgents, Gmail API/SMTP, cron/scheduler, local JSON storage

---

## File Structure

```
TradingAgents/
├── cli/main.py                    # Modify: add portfolio commands
├── portfolio/
│   ├── __init__.py
│   └── manager.py                 # Create: portfolio data manager
├── data/portfolio.json            # Create: portfolio storage
├── scheduler/
│   ├── __init__.py
│   ├── service.py                 # Create: scheduler daemon
│   └── gmail_pusher.py            # Create: email sender
├── docs/superpowers/specs/2026-05-01-us-stock-analysis-design.md
└── docs/superpowers/plans/2026-05-01-us-stock-analysis-plan.md
```

---

## Task 1: Portfolio Manager

**Files:**
- Create: `portfolio/__init__.py`
- Create: `portfolio/manager.py`
- Create: `data/portfolio.json`
- Test: `tests/test_portfolio_manager.py`

- [ ] **Step 1: Create directory structure**

Run: `mkdir -p portfolio tests`

- [ ] **Step 2: Write portfolio/\_\_init\_\_.py**

```python
from .manager import PortfolioManager

__all__ = ["PortfolioManager"]
```

- [ ] **Step 3: Write failing test for PortfolioManager**

```python
import pytest
import os
import json
from portfolio.manager import PortfolioManager

@pytest.fixture
def test_portfolio_file(tmp_path):
    return str(tmp_path / "test_portfolio.json")

@pytest.fixture
def manager(test_portfolio_file):
    return PortfolioManager(portfolio_file=test_portfolio_file)

def test_load_empty_portfolio(manager):
    """Test that empty portfolio initializes correctly."""
    assert manager.get_positions() == []
    assert manager.get_cash_balance() == 0

def test_add_position(manager):
    """Test adding a new position."""
    manager.add_position("AMZN", shares=2, entry_price=258.5, entry_date="2026-04-29", broker="Trade25")
    positions = manager.get_positions()
    assert len(positions) == 1
    assert positions[0]["ticker"] == "AMZN"
    assert positions[0]["shares"] == 2
    assert positions[0]["entry_price"] == 258.5

def test_remove_position(manager):
    """Test removing a position."""
    manager.add_position("AMZN", shares=2, entry_price=258.5, entry_date="2026-04-29", broker="Trade25")
    manager.remove_position("AMZN")
    assert manager.get_positions() == []

def test_get_position(manager):
    """Test getting a specific position."""
    manager.add_position("AMZN", shares=2, entry_price=258.5, entry_date="2026-04-29", broker="Trade25")
    pos = manager.get_position("AMZN")
    assert pos is not None
    assert pos["ticker"] == "AMZN"

def test_update_cash_balance(manager):
    """Test updating cash balance."""
    manager.update_cash_balance(1400)
    assert manager.get_cash_balance() == 1400

def test_save_and_load(manager):
    """Test that portfolio persists to disk."""
    manager.add_position("AMZN", shares=2, entry_price=258.5, entry_date="2026-04-29", broker="Trade25")
    manager.update_cash_balance(1400)
    manager.save()

    # Load in new instance
    new_manager = PortfolioManager(portfolio_file=manager.portfolio_file)
    positions = new_manager.get_positions()
    assert len(positions) == 1
    assert new_manager.get_cash_balance() == 1400
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest tests/test_portfolio_manager.py -v`
Expected: FAIL - ModuleNotFoundError: No module named 'portfolio'

- [ ] **Step 5: Write portfolio/manager.py**

```python
"""Portfolio Manager - handles local portfolio storage and retrieval."""

import json
import os
from typing import Optional
from dataclasses import dataclass, asdict


@dataclass
class Position:
    ticker: str
    shares: float
    entry_price: float
    entry_date: str
    broker: str = "unknown"


class PortfolioManager:
    """Manages local portfolio data storage."""

    def __init__(self, portfolio_file: str = "data/portfolio.json"):
        self.portfolio_file = portfolio_file
        self._positions: list[dict] = []
        self._cash_balance: float = 0
        self._ensure_data_dir()
        self._load()

    def _ensure_data_dir(self):
        """Ensure the data directory exists."""
        dir_path = os.path.dirname(self.portfolio_file)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

    def _load(self):
        """Load portfolio from disk."""
        if os.path.exists(self.portfolio_file):
            try:
                with open(self.portfolio_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._positions = data.get("positions", [])
                    self._cash_balance = data.get("cash_balance", 0)
            except (json.JSONDecodeError, IOError):
                self._positions = []
                self._cash_balance = 0
        else:
            self._positions = []
            self._cash_balance = 0

    def save(self):
        """Save portfolio to disk."""
        data = {
            "cash_balance": self._cash_balance,
            "last_updated": self._get_date(),
            "positions": self._positions
        }
        with open(self.portfolio_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _get_date(self) -> str:
        """Get current date string."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d")

    def add_position(self, ticker: str, shares: float, entry_price: float,
                     entry_date: str, broker: str = "unknown") -> None:
        """Add or update a position."""
        # Check if position already exists
        for pos in self._positions:
            if pos["ticker"].upper() == ticker.upper():
                pos["shares"] = shares
                pos["entry_price"] = entry_price
                pos["entry_date"] = entry_date
                pos["broker"] = broker
                self.save()
                return

        # Add new position
        self._positions.append({
            "ticker": ticker.upper(),
            "shares": shares,
            "entry_price": entry_price,
            "entry_date": entry_date,
            "broker": broker
        })
        self.save()

    def remove_position(self, ticker: str) -> bool:
        """Remove a position by ticker."""
        original_len = len(self._positions)
        self._positions = [p for p in self._positions if p["ticker"].upper() != ticker.upper()]
        if len(self._positions) < original_len:
            self.save()
            return True
        return False

    def get_positions(self) -> list[dict]:
        """Get all positions."""
        return self._positions.copy()

    def get_position(self, ticker: str) -> Optional[dict]:
        """Get a specific position by ticker."""
        for pos in self._positions:
            if pos["ticker"].upper() == ticker.upper():
                return pos.copy()
        return None

    def update_cash_balance(self, amount: float) -> None:
        """Update cash balance."""
        self._cash_balance = amount
        self.save()

    def get_cash_balance(self) -> float:
        """Get current cash balance."""
        return self._cash_balance

    def clear_all(self) -> None:
        """Clear all positions and reset cash balance."""
        self._positions = []
        self._cash_balance = 0
        self.save()
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_portfolio_manager.py -v`
Expected: PASS

- [ ] **Step 7: Create initial data/portfolio.json**

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

- [ ] **Step 8: Commit**

```bash
git add portfolio/ data/portfolio.json tests/test_portfolio_manager.py
git commit -m "feat: add portfolio manager for position tracking"
```

---

## Task 2: CLI Commands Integration

**Files:**
- Modify: `cli/main.py:1-50` (add imports)
- Modify: `cli/main.py:463-613` (add portfolio command functions)
- Modify: `cli/main.py:1200-1221` (register analyze command)
- Test: `tests/test_cli_portfolio.py`

- [ ] **Step 1: Write failing test for CLI portfolio commands**

```python
import pytest
from typer.testing import CliRunner
from cli.main import app

@pytest.fixture
def cli_runner():
    return CliRunner()

def test_portfolio_view_empty(cli_runner, tmp_path):
    """Test portfolio view with no positions."""
    result = cli_runner.invoke(app, ["portfolio", "--help"])
    assert result.exit_code == 0

def test_analyze_command_exists(cli_runner):
    """Test that analyze command exists."""
    result = cli_runner.invoke(app, ["analyze", "--help"])
    # Should not fail with "no such command"
    assert "no such command" not in result.output.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli_portfolio.py -v`
Expected: FAIL - analyze command not found

- [ ] **Step 3: Add portfolio manager import to cli/main.py**

Add after line 9:
```python
from portfolio.manager import PortfolioManager
```

- [ ] **Step 4: Add portfolio commands to cli/main.py**

Add after `get_user_selections()` function (around line 613):

```python
@app.command()
def portfolio():
    """View current portfolio summary."""
    portfolio_file = Path(__file__).parent.parent / "data" / "portfolio.json"
    manager = PortfolioManager(str(portfolio_file))

    positions = manager.get_positions()
    cash = manager.get_cash_balance()

    console.print("\n[bold cyan]Portfolio Summary[/bold cyan]\n")
    console.print(f"Cash Balance: ${cash:,.2f}\n")

    if not positions:
        console.print("[yellow]No positions found.[/yellow]")
        return

    table = Table(show_header=True, box=box.MINIMAL)
    table.add_column("Ticker", style="green")
    table.add_column("Shares", style="cyan")
    table.add_column("Entry Price", style="yellow")
    table.add_column("Entry Date", style="magenta")
    table.add_column("Broker", style="white")

    for pos in positions:
        table.add_row(
            pos["ticker"],
            str(pos["shares"]),
            f"${pos['entry_price']:.2f}",
            pos["entry_date"],
            pos["broker"]
        )

    console.print(table)
    console.print()

@app.command()
def add_position(
    ticker: str = typer.Argument(..., help="Stock ticker symbol"),
    shares: float = typer.Argument(..., help="Number of shares"),
    price: float = typer.Argument(..., help="Entry price per share"),
    date: str = typer.Option(None, "--date", help="Entry date (YYYY-MM-DD)"),
    broker: str = typer.Option("Trade25", "--broker", help="Broker name")
):
    """Add a position to the portfolio."""
    from datetime import datetime

    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    portfolio_file = Path(__file__).parent.parent / "data" / "portfolio.json"
    manager = PortfolioManager(str(portfolio_file))
    manager.add_position(ticker.upper(), shares, price, date, broker)

    console.print(f"[green]Added position:[/green] {ticker.upper()} {shares} shares @ ${price:.2f}")

@app.command()
def remove_position(
    ticker: str = typer.Argument(..., help="Stock ticker symbol to remove")
):
    """Remove a position from the portfolio."""
    portfolio_file = Path(__file__).parent.parent / "data" / "portfolio.json"
    manager = PortfolioManager(str(portfolio_file))

    if manager.remove_position(ticker.upper()):
        console.print(f"[green]Removed position:[/green] {ticker.upper()}")
    else:
        console.print(f"[yellow]Position not found:[/yellow] {ticker.upper()}")

@app.command()
def analyze(
    ticker: str = typer.Argument(..., help="Stock ticker to analyze"),
    date: str = typer.Option(None, "--date", help="Analysis date (YYYY-MM-DD)")
):
    """Analyze a stock using TradingAgents framework."""
    from datetime import datetime

    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    console.print(f"[cyan]Analyzing {ticker.upper()} on {date}...[/cyan]")

    # Import here to avoid circular imports
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from tradingagents.default_config import DEFAULT_CONFIG

    config = DEFAULT_CONFIG.copy()
    config["output_language"] = "English"

    graph = TradingAgentsGraph(
        selected_analyst_keys=["market", "social", "news", "fundamentals"],
        config=config,
        debug=True
    )

    init_agent_state = graph.propagator.create_initial_state(ticker.upper(), date)
    args = graph.propagator.get_graph_args()

    for chunk in graph.graph.stream(init_agent_state, **args):
        pass  # Stream chunks, display handled by the graph

    console.print(f"[green]Analysis complete for {ticker.upper()}[/green]")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_cli_portfolio.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add cli/main.py
git commit -m "feat: add portfolio CLI commands (portfolio, add, remove, analyze)"
```

---

## Task 3: Gmail Integration

**Files:**
- Create: `scheduler/gmail_pusher.py`
- Create: `scheduler/__init__.py`
- Modify: `cli/main.py` (add email config)
- Test: `tests/test_gmail_pusher.py`

- [ ] **Step 1: Write failing test for GmailPusher**

```python
import pytest
from unittest.mock import Mock, patch
from scheduler.gmail_pusher import GmailPusher, EmailMessage

@pytest.fixture
def gmail_pusher():
    return GmailPusher(
        sender_email="test@gmail.com",
        recipient_email="user@gmail.com"
    )

def test_email_message_creation():
    """Test email message structure."""
    msg = EmailMessage(
        subject="Test Subject",
        body="Test Body",
        to_email="user@gmail.com"
    )
    assert msg.subject == "Test Subject"
    assert msg.body == "Test Body"

def test_gmail_pusher_initialization(gmail_pusher):
    """Test GmailPusher initialization."""
    assert gmail_pusher.sender_email == "test@gmail.com"
    assert gmail_pusher.recipient_email == "user@gmail.com"

def test_format_premarket_briefing(gmail_pusher):
    """Test premarket briefing email formatting."""
    report = {
        "positions": [{"ticker": "AMZN", "shares": 2, "entry_price": 258.5}],
        "sentiment": "bullish",
        "events": ["Earnings tomorrow"]
    }
    email = gmail_pusher.format_premarket_briefing(report)
    assert "Pre-market" in email.subject
    assert "AMZN" in email.body

def test_format_weekly_report(gmail_pusher):
    """Test weekly report email formatting."""
    report = {
        "portfolio_value": 3000,
        "gain_loss": 500,
        "positions": [],
        "recommendations": ["Hold AMZN"]
    }
    email = gmail_pusher.format_weekly_report(report)
    assert "Weekly" in email.subject
    assert "3000" in email.body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_gmail_pusher.py -v`
Expected: FAIL - No module named 'scheduler'

- [ ] **Step 3: Create scheduler/__init__.py**

```python
from .gmail_pusher import GmailPusher, EmailMessage
from .service import SchedulerService

__all__ = ["GmailPusher", "EmailMessage", "SchedulerService"]
```

- [ ] **Step 4: Create scheduler/gmail_pusher.py**

```python
"""Gmail Pusher - sends analysis reports via Gmail."""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass
from typing import Optional


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
                 smtp_port: int = 587):
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
        """Send an email via Gmail SMTP."""
        try:
            email_user, email_pass = self._get_credentials()

            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = message.to_email
            if message.cc_email:
                msg['Cc'] = message.cc_email
            msg['Subject'] = message.subject

            msg.attach(MIMEText(message.body, 'html'))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(email_user, email_pass)
                server.send_message(msg)

            return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False

    def send_with_retry(self, message: EmailMessage, max_retries: int = 3) -> bool:
        """Send email with retry logic."""
        import time

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

        body = f"""
        <h2>Pre-market Briefing</h2>
        <h3>Portfolio Positions</h3>
        <table border="1" cellpadding="5" cellspacing="0">
            <tr><th>Ticker</th><th>Shares</th><th>Entry Price</th></tr>
            {''.join(f"<tr><td>{p['ticker']}</td><td>{p['shares']}</td><td>${p['entry_price']:.2f}</td></tr>" for p in positions)}
        </table>

        <h3>Market Sentiment</h3>
        <p>{sentiment.upper()}</p>

        <h3>Key Events Today</h3>
        <ul>
            {''.join(f"<li>{e}</li>" for e in events)}
        </ul>

        <p><em>Generated by TradingAgents</em></p>
        """

        return EmailMessage(
            subject=f"Pre-market Briefing - {report.get('date', 'Today')}",
            body=body,
            to_email=self.recipient_email
        )

    def format_afterhours_report(self, report: dict) -> EmailMessage:
        """Format after-hours report email."""
        positions = report.get("positions", [])
        analysis = report.get("analysis", "")

        body = f"""
        <h2>After-hours Report</h2>
        <h3>Portfolio Performance</h3>
        <table border="1" cellpadding="5" cellspacing="0">
            <tr><th>Ticker</th><th>Shares</th><th>Current/Pivot</th><th>Action</th></tr>
            {''.join(f"<tr><td>{p['ticker']}</td><td>{p['shares']}</td><td>{p.get('current_price', 'N/A')}</td><td>{p.get('action', 'Hold')}</td></tr>" for p in positions)}
        </table>

        <h3>Analysis Summary</h3>
        <p>{analysis}</p>

        <p><em>Generated by TradingAgents</em></p>
        """

        return EmailMessage(
            subject=f"After-hours Report - {report.get('date', 'Today')}",
            body=body,
            to_email=self.recipient_email
        )

    def format_weekly_report(self, report: dict) -> EmailMessage:
        """Format weekly comprehensive report."""
        portfolio_value = report.get("portfolio_value", 0)
        gain_loss = report.get("gain_loss", 0)
        positions = report.get("positions", [])
        recommendations = report.get("recommendations", [])

        body = f"""
        <h2>Weekly Portfolio Report</h2>

        <h3>Portfolio Summary</h3>
        <p>Total Value: <strong>${portfolio_value:,.2f}</strong></p>
        <p>Gain/Loss: <strong style="color: {'green' if gain_loss >= 0 else 'red'}">${gain_loss:,.2f}</strong></p>

        <h3>Current Positions</h3>
        <table border="1" cellpadding="5" cellspacing="0">
            <tr><th>Ticker</th><th>Shares</th><th>Entry</th><th>Current</th><th>P/L</th><th>Action</th></tr>
            {''.join(f"<tr><td>{p['ticker']}</td><td>{p['shares']}</td><td>${p['entry_price']:.2f}</td><td>${p.get('current_price', 'N/A')}</td><td style='color: {'green' if p.get('pnl', 0) >= 0 else 'red'}'>${p.get('pnl', 0):.2f}</td><td>{p.get('recommendation', 'Hold')}</td></tr>" for p in positions)}
        </table>

        <h3>Recommendations</h3>
        <ul>
            {''.join(f"<li>{r}</li>" for r in recommendations)}
        </ul>

        <h3>Market Outlook</h3>
        <p>{report.get('market_outlook', 'No data available')}</p>

        <p><em>Generated by TradingAgents - Weekly Analysis</em></p>
        """

        return EmailMessage(
            subject=f"Weekly Portfolio Report - {report.get('week', 'This Week')}",
            body=body,
            to_email=self.recipient_email
        )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_gmail_pusher.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add scheduler/ tests/test_gmail_pusher.py
git commit -m "feat: add Gmail pusher for email reports"
```

---

## Task 4: Scheduler Service

**Files:**
- Create: `scheduler/service.py`
- Create: `logs/.gitkeep`
- Create: `data/task_queue.json`
- Test: `tests/test_scheduler_service.py`

- [ ] **Step 1: Write failing test for SchedulerService**

```python
import pytest
from unittest.mock import Mock, patch
from scheduler.service import SchedulerService

@pytest.fixture
def scheduler():
    return SchedulerService()

def test_scheduler_initialization(scheduler):
    """Test scheduler initializes correctly."""
    assert scheduler is not None
    assert scheduler.tasks == []

def test_add_daily_task(scheduler):
    """Test adding a daily task."""
    scheduler.add_daily_task("premarket", "08:30", lambda: True)
    assert len(scheduler.tasks) == 1

def test_add_weekly_task(scheduler):
    """Test adding a weekly task."""
    scheduler.add_weekly_task("weekly_report", "09:00", "Monday", lambda: True)
    assert len(scheduler.tasks) == 1

def test_task_queue_persistence(tmp_path):
    """Test task queue saves to disk."""
    queue_file = str(tmp_path / "task_queue.json")
    service = SchedulerService(task_queue_file=queue_file)
    service.add_daily_task("test", "08:30", lambda: True)
    service.save_queue()

    # Load new instance
    service2 = SchedulerService(task_queue_file=queue_file)
    assert len(service2.tasks) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_scheduler_service.py -v`
Expected: FAIL - No module named 'scheduler'

- [ ] **Step 3: Create scheduler/service.py**

```python
"""Scheduler Service - manages automated task scheduling."""

import json
import os
import time
import threading
from datetime import datetime, timedelta
from typing import Callable, Optional
from dataclasses import asdict


class Task:
    """Represents a scheduled task."""

    def __init__(self, name: str, task_type: str, time_str: str,
                 days: Optional[list] = None, callback: Optional[Callable] = None):
        self.name = name
        self.task_type = task_type  # "daily" or "weekly"
        self.time_str = time_str  # "HH:MM" format
        self.days = days or []  # For weekly tasks: ["Monday", etc.]
        self.callback = callback
        self.last_run: Optional[str] = None
        self.enabled = True

    def should_run_today(self) -> bool:
        """Check if this task should run today."""
        if not self.enabled:
            return False

        if self.task_type == "daily":
            return True

        if self.task_type == "weekly":
            today = datetime.now().strftime("%A")
            return today in self.days

        return False

    def is_time_to_run(self) -> bool:
        """Check if it's time to run this task."""
        if not self.should_run_today():
            return False

        now = datetime.now()
        target_time = datetime.strptime(self.time_str, "%H:%M")

        # For daily tasks, check if we're within 1 minute of target time
        if self.task_type == "daily":
            current_minutes = now.hour * 60 + now.minute
            target_minutes = target_time.hour * 60 + target_time.minute
            return abs(current_minutes - target_minutes) <= 1

        # For weekly, also check day
        return True

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "task_type": self.task_type,
            "time_str": self.time_str,
            "days": self.days,
            "last_run": self.last_run,
            "enabled": self.enabled
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Create Task from dictionary."""
        task = cls(
            name=data["name"],
            task_type=data["task_type"],
            time_str=data["time_str"],
            days=data.get("days", [])
        )
        task.last_run = data.get("last_run")
        task.enabled = data.get("enabled", True)
        return task


class SchedulerService:
    """Manages scheduled tasks for automated analysis and reports."""

    def __init__(self, task_queue_file: str = "data/task_queue.json",
                 log_file: str = "logs/scheduler.log"):
        self.task_queue_file = task_queue_file
        self.log_file = log_file
        self.tasks: list[Task] = []
        self._ensure_directories()
        self._load_queue()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def _ensure_directories(self):
        """Ensure required directories exist."""
        for dir_path in [os.path.dirname(self.task_queue_file), os.path.dirname(self.log_file)]:
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)

    def _load_queue(self):
        """Load task queue from disk."""
        if os.path.exists(self.task_queue_file):
            try:
                with open(self.task_queue_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.tasks = [Task.from_dict(t) for t in data.get("tasks", [])]
            except (json.JSONDecodeError, IOError):
                self.tasks = []
        else:
            self.tasks = []

    def save_queue(self):
        """Save task queue to disk."""
        data = {"tasks": [t.to_dict() for t in self.tasks]}
        with open(self.task_queue_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def add_daily_task(self, name: str, time_str: str, callback: Callable) -> None:
        """Add a daily recurring task."""
        task = Task(name=name, task_type="daily", time_str=time_str, callback=callback)
        self.tasks.append(task)
        self.save_queue()

    def add_weekly_task(self, name: str, time_str: str, days: list,
                        callback: Callable) -> None:
        """Add a weekly recurring task."""
        task = Task(name=name, task_type="weekly", time_str=time_str,
                    days=days, callback=callback)
        self.tasks.append(task)
        self.save_queue()

    def remove_task(self, name: str) -> bool:
        """Remove a task by name."""
        original_len = len(self.tasks)
        self.tasks = [t for t in self.tasks if t.name != name]
        if len(self.tasks) < original_len:
            self.save_queue()
            return True
        return False

    def _log(self, message: str) -> None:
        """Write to scheduler log."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}\n"
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_line)

    def _run_task(self, task: Task) -> None:
        """Execute a task and log result."""
        try:
            self._log(f"Starting task: {task.name}")
            if task.callback:
                task.callback()
            task.last_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._log(f"Completed task: {task.name}")
        except Exception as e:
            self._log(f"Error in task {task.name}: {e}")

    def _scheduler_loop(self) -> None:
        """Main scheduler loop running in background thread."""
        while self._running:
            now = datetime.now()

            for task in self.tasks:
                if task.should_run_today() and task.is_time_to_run():
                    # Check if we already ran this task recently (within 5 min)
                    if task.last_run:
                        last_run_time = datetime.strptime(task.last_run, "%Y-%m-%d %H:%M:%S")
                        if (now - last_run_time).total_seconds() < 300:
                            continue

                    self._run_task(task)

            time.sleep(60)  # Check every minute

    def start(self) -> None:
        """Start the scheduler in a background thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._thread.start()
        self._log("Scheduler started")

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        self._log("Scheduler stopped")

    def run_now(self, task_name: str) -> bool:
        """Manually trigger a task to run immediately."""
        for task in self.tasks:
            if task.name == task_name:
                self._run_task(task)
                return True
        return False

    def list_tasks(self) -> list[dict]:
        """List all scheduled tasks."""
        return [t.to_dict() for t in self.tasks]
```

- [ ] **Step 3: Run test to verify it passes**

Run: `pytest tests/test_scheduler_service.py -v`
Expected: PASS

- [ ] **Step 4: Create data/task_queue.json with default tasks**

```json
{
  "tasks": [
    {
      "name": "premarket_briefing",
      "task_type": "daily",
      "time_str": "08:30",
      "days": [],
      "last_run": null,
      "enabled": true
    },
    {
      "name": "afterhours_report",
      "task_type": "daily",
      "time_str": "16:00",
      "days": [],
      "last_run": null,
      "enabled": true
    },
    {
      "name": "weekly_analysis",
      "task_type": "weekly",
      "time_str": "09:00",
      "days": ["Monday"],
      "last_run": null,
      "enabled": true
    }
  ]
}
```

- [ ] **Step 5: Create logs/.gitkeep**

```text
# This file ensures the logs directory exists in git
```

- [ ] **Step 6: Commit**

```bash
git add scheduler/service.py data/task_queue.json logs/.gitkeep
git commit -m "feat: add scheduler service for automated tasks"
```

---

## Task 5: Integration and Documentation

**Files:**
- Modify: `cli/main.py` (add scheduler trigger)
- Create: `docs/superpowers/plans/README.md`
- Update: `docs/superpowers/specs/2026-05-01-us-stock-analysis-design.md` (add implementation notes)

- [ ] **Step 1: Add environment variable documentation to .env.example**

Add to `.env.example`:
```bash
# Gmail Configuration for email reports
GMAIL_EMAIL=your-email@gmail.com
GMAIL_APP_PASSWORD=your-app-password

# Portfolio file location
PORTFOLIO_FILE=data/portfolio.json

# Scheduler log location
SCHEDULER_LOG=logs/scheduler.log
```

- [ ] **Step 2: Create docs/superpowers/plans/README.md**

```markdown
# Implementation Plan

## Project Overview
This plan implements a hybrid investment analysis system combining:
- TradingAgents CLI for interactive stock analysis
- Background scheduler for automated daily/weekly Gmail reports
- Local portfolio manager for position tracking

## Phases

### Phase 1: Portfolio Manager (COMPLETED)
- Local JSON storage for positions
- CLI commands for portfolio view, add, remove
- Tests passing

### Phase 2: Gmail Integration (COMPLETED)
- SMTP-based email sender
- Pre-market, after-hours, weekly email formats
- Retry logic for failed sends

### Phase 3: Scheduler Service (COMPLETED)
- Daily/weekly task scheduling
- Background daemon mode
- Task persistence to disk

### Phase 4: CLI Integration (IN PROGRESS)
- Connect scheduler to Gmail pusher
- Connect analyze command to TradingAgents
- Natural language position updates

## Setup Instructions

1. Copy `.env.example` to `.env` and fill in Gmail credentials
2. Ensure `data/portfolio.json` exists with your positions
3. Run `python -m cli.main portfolio` to verify setup
4. Run `python -m cli.main analyze AMZN` to test analysis

## Running the Scheduler

```bash
# Start scheduler in background
python -c "from scheduler.service import SchedulerService; s = SchedulerService(); s.start(); import time; time.sleep(3600)"

# Or use the CLI to trigger reports manually
python -m cli.main report
```

## Gmail Setup

1. Enable 2-factor authentication on your Gmail account
2. Generate an App Password: https://myaccount.google.com/security
3. Set environment variables:
   - `GMAIL_EMAIL`: your-email@gmail.com
   - `GMAIL_APP_PASSWORD`: xxxxxxx (16-char app password)
```

- [ ] **Step 3: Commit**

```bash
git add .env.example docs/superpowers/plans/README.md
git commit -m "docs: add setup instructions and integration documentation"
```

---

## Self-Review Checklist

### Spec Coverage
- [x] Portfolio Manager - Task 1
- [x] CLI Commands (/analyze, /portfolio, /add, /remove) - Task 2
- [x] Gmail Integration - Task 3
- [x] Scheduler Service (daily/weekly) - Task 4
- [x] Documentation - Task 5

### Placeholder Scan
- No "TBD", "TODO", or incomplete sections
- All code blocks contain actual implementation
- All test code is complete and runnable

### Type Consistency
- Task names match: "premarket_briefing", "afterhours_report", "weekly_analysis"
- Email formatting methods: `format_premarket_briefing`, `format_afterhours_report`, `format_weekly_report`
- All tasks use consistent Task class interface

---

## Execution Options

**Plan complete and saved to `docs/superpowers/plans/2026-05-01-us-stock-analysis-plan.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**