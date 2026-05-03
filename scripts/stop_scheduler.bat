@echo off
powershell -Command "Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowTitle -like '*scheduler*' -or $_.ProcessName -eq 'python'} | Stop-Process -Force"
echo Scheduler stopped
