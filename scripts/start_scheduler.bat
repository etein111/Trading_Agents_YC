@echo off
cd /d D:\yechuan\work\My_project\TradingAgents
D:\yechuan\work\My_project\TradingAgents\.venv\Scripts\python.exe -c "
import time, threading
from scheduler.service import SchedulerService

s = SchedulerService()
s.start()

# Keep running
while True:
    time.sleep(60)
" > logs/scheduler.log 2>&1