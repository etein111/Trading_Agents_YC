@echo off
schtasks /create /tn "TradingAgents Scheduler" /tr "\"D:\yechuan\work\My_project\TradingAgents\scripts\start_scheduler.bat\"" /sc onlogon /rl highest /f
echo.
schtasks /query /tn "TradingAgents Scheduler"
