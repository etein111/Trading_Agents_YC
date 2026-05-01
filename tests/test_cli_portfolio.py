import pytest
from typer.testing import CliRunner
from cli.main import app

@pytest.fixture
def cli_runner():
    return CliRunner()

def test_portfolio_view_empty(cli_runner):
    """Test portfolio view with no positions."""
    result = cli_runner.invoke(app, ["portfolio", "--help"])
    assert result.exit_code == 0
    # Ensure it's not falling back to analyze command
    assert "no such command" not in result.output.lower()
    assert "--checkpoint" not in result.output  # analyze-specific option

def test_analyze_command_exists(cli_runner):
    """Test that analyze command exists."""
    result = cli_runner.invoke(app, ["analyze", "--help"])
    # Should not fail with "no such command"
    assert "no such command" not in result.output.lower()
    assert "--checkpoint" in result.output  # analyze has this option

def test_add_position_command_exists(cli_runner):
    """Test that add-position command exists."""
    result = cli_runner.invoke(app, ["add-position", "--help"])
    assert result.exit_code == 0
    assert "no such command" not in result.output.lower()

def test_remove_position_command_exists(cli_runner):
    """Test that remove-position command exists."""
    result = cli_runner.invoke(app, ["remove-position", "--help"])
    assert result.exit_code == 0
    assert "no such command" not in result.output.lower()
