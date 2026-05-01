import pytest
from scheduler.service import SchedulerService

@pytest.fixture
def scheduler(tmp_path):
    queue_file = str(tmp_path / "task_queue.json")
    return SchedulerService(task_queue_file=queue_file)

def test_scheduler_initialization(scheduler):
    """Test scheduler initializes correctly."""
    assert scheduler is not None
    assert scheduler.tasks == []

def test_add_daily_task(scheduler):
    """Test adding a daily task."""
    scheduler.add_daily_task("premarket", "08:30", lambda: True)
    assert len(scheduler.tasks) == 1

def test_add_weekly_task(scheduler):
    """Test adding a weekly task."""
    scheduler.add_weekly_task("weekly_report", "09:00", "Monday", lambda: True)
    assert len(scheduler.tasks) == 1

def test_task_queue_persistence(tmp_path):
    """Test task queue saves to disk."""
    queue_file = str(tmp_path / "task_queue.json")
    service = SchedulerService(task_queue_file=queue_file)
    service.add_daily_task("test", "08:30", lambda: True)
    service.save_queue()

    # Load new instance
    service2 = SchedulerService(task_queue_file=queue_file)
    assert len(service2.tasks) == 1