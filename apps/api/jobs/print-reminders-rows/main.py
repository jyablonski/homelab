from sqlalchemy import func, select

from database import get_session
from database_models.reminder import ReminderRow


def count_reminder_rows() -> int:
    with get_session() as session:
        statement = select(func.count()).select_from(ReminderRow)
        return session.execute(statement).scalar_one()


def main() -> None:
    print("print-reminders-rows: starting")
    row_count = count_reminder_rows()
    print(f"print-reminders-rows: counted {row_count} row(s) in personal_reminders")
    print("print-reminders-rows: finished")


if __name__ == "__main__":
    main()
