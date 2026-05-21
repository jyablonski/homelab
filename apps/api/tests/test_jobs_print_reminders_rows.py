import importlib.util
from datetime import date
from pathlib import Path

from database import get_session
from database_models.reminder import ReminderRow


def test_count_reminder_rows(api_database_env, reminders_table):
    job = _load_job_module()

    assert job.count_reminder_rows() == 0

    with get_session() as session:
        session.add_all(
            [
                ReminderRow(
                    reminder_type="test",
                    reminder_message="First reminder",
                    reminder_start_date=date(2026, 1, 1),
                ),
                ReminderRow(
                    reminder_type="test",
                    reminder_message="Second reminder",
                    reminder_start_date=date(2026, 1, 2),
                ),
            ]
        )
        session.commit()

    assert job.count_reminder_rows() == 2


def _load_job_module():
    job_path = (
        Path(__file__).resolve().parents[1]
        / "jobs"
        / "print-reminders-rows"
        / "main.py"
    )
    spec = importlib.util.spec_from_file_location(
        "print_reminders_rows_job",
        job_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
