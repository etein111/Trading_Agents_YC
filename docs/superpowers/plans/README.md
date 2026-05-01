# US Stock Analysis System - Setup Instructions

## Overview

This system combines TradingAgents CLI for interactive stock analysis with a background scheduler for automated daily/weekly Gmail reports.

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# LLM Provider (required)
OPENAI_API_KEY=your-openai-key

# Gmail Configuration for email reports
GMAIL_EMAIL=your-email@gmail.com
GMAIL_APP_PASSWORD=your-app-password

# Portfolio file location
PORTFOLIO_FILE=data/portfolio.json

# Scheduler log location
SCHEDULER_LOG=logs/scheduler.log
```

## Gmail Setup

1. Enable 2-factor authentication on your Gmail account
2. Generate an App Password:
   - Go to: https://myaccount.google.com/security
   - Select "App passwords" under "Signing in to Google"
   - Create a new app password for "Mail"
3. Set `GMAIL_EMAIL` and `GMAIL_APP_PASSWORD` in your `.env` file

## Portfolio Commands

```bash
# View current portfolio
python -m cli.main portfolio

# Add a position
python -m cli.main add-position AMZN 2 258.5 --date 2026-04-29 --broker Trade25

# Remove a position
python -m cli.main remove-position AMZN

# Analyze a stock
python -m cli.main analyze AMZN --date 2026-05-01

# Generate a report
python -m cli.main report

# Trigger weekly analysis
python -m cli.main weekly
```

## Starting the Scheduler

```bash
# Start the scheduler in background
python -c "from scheduler.service import SchedulerService; s = SchedulerService(); s.start(); import time; time.sleep(86400)"

# Or run indefinitely
python -c "from scheduler.service import SchedulerService; import time; s = SchedulerService(); s.start(); time.sleep(3600 * 24 * 7)"  # 1 week
```

## File Locations

- Portfolio data: `data/portfolio.json`
- Scheduler log: `logs/scheduler.log`
- Task queue: `data/task_queue.json`
- Reports: `reports/{ticker}/{date}/`