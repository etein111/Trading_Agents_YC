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