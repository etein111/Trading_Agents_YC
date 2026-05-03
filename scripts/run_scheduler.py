import time, threading, os, sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env so Gmail credentials are available in the scheduler process
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(Path(__file__).parent.parent / ".env")

from scheduler.service import SchedulerService

s = SchedulerService()
s.start()

while True:
    time.sleep(60)