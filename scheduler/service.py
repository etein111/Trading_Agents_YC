"""Scheduler Service - manages automated task scheduling."""

import json
import os
import time
import threading
from datetime import datetime
from typing import Callable, Optional


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

        # For weekly, also check time (same logic as daily)
        if self.task_type == "weekly":
            current_minutes = now.hour * 60 + now.minute
            target_minutes = target_time.hour * 60 + target_time.minute
            return abs(current_minutes - target_minutes) <= 1

        return False

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
        self._lock = threading.Lock()
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
        from scheduler.tasks import TASK_CALLBACKS
        if os.path.exists(self.task_queue_file):
            try:
                with open(self.task_queue_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    with self._lock:
                        self.tasks = [Task.from_dict(t) for t in data.get("tasks", [])]
                        for task in self.tasks:
                            task.callback = TASK_CALLBACKS.get(task.name)
            except (json.JSONDecodeError, IOError, KeyError, TypeError):
                with self._lock:
                    self.tasks = []
        else:
            with self._lock:
                self.tasks = []

    def save_queue(self):
        """Save task queue to disk."""
        with self._lock:
            data = {"tasks": [t.to_dict() for t in self.tasks]}
        with open(self.task_queue_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def add_daily_task(self, name: str, time_str: str, callback: Callable) -> None:
        """Add a daily recurring task."""
        task = Task(name=name, task_type="daily", time_str=time_str, callback=callback)
        with self._lock:
            self.tasks.append(task)
        self.save_queue()

    def add_weekly_task(self, name: str, time_str: str, days: list,
                        callback: Callable) -> None:
        """Add a weekly recurring task."""
        task = Task(name=name, task_type="weekly", time_str=time_str,
                    days=days, callback=callback)
        with self._lock:
            self.tasks.append(task)
        self.save_queue()

    def remove_task(self, name: str) -> bool:
        """Remove a task by name."""
        with self._lock:
            original_len = len(self.tasks)
            self.tasks = [t for t in self.tasks if t.name != name]
            removed = len(self.tasks) < original_len
        if removed:
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