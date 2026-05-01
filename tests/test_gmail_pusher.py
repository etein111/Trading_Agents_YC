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
    assert "$3,000.00" in email.body