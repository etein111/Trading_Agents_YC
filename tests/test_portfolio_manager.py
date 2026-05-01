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