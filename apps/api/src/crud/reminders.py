from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_session
from database_models.reminder import Reminder, ReminderCreate, ReminderRow

UPDATE_FIELDS = {
    "reminder_type",
    "reminder_message",
    "reminder_start_date",
    "reminder_end_date",
    "is_completed",
    "completed_at",
}


def list_reminders(
    *,
    include_completed: bool = False,
    limit: int = 100,
    offset: int = 0,
    session: Session | None = None,
) -> list[Reminder]:
    if session is None:
        with get_session() as managed_session:
            return list_reminders(
                include_completed=include_completed,
                limit=limit,
                offset=offset,
                session=managed_session,
            )

    statement = select(ReminderRow).order_by(
        ReminderRow.reminder_start_date.asc(),
        ReminderRow.id.asc(),
    )
    if not include_completed:
        statement = statement.where(ReminderRow.is_completed.is_(False))

    rows = session.scalars(statement.limit(limit).offset(offset)).all()
    return [Reminder.model_validate(row) for row in rows]


def get_reminder(
    reminder_id: int,
    *,
    session: Session | None = None,
) -> Reminder | None:
    if session is None:
        with get_session() as managed_session:
            return get_reminder(reminder_id, session=managed_session)

    row = session.get(ReminderRow, reminder_id)
    return Reminder.model_validate(row) if row else None


def create_reminder(
    reminder: ReminderCreate,
    *,
    session: Session | None = None,
) -> Reminder:
    if session is None:
        with get_session() as managed_session:
            created_reminder = create_reminder(reminder, session=managed_session)
            managed_session.commit()
            return created_reminder

    row = ReminderRow(**reminder.model_dump())
    session.add(row)
    session.flush()
    session.refresh(row)
    return Reminder.model_validate(row)


def update_reminder(
    reminder_id: int,
    changes: Mapping[str, Any],
    *,
    session: Session | None = None,
) -> Reminder | None:
    if session is None:
        with get_session() as managed_session:
            updated_reminder = update_reminder(
                reminder_id,
                changes,
                session=managed_session,
            )
            managed_session.commit()
            return updated_reminder

    update_values = {
        key: value for key, value in changes.items() if key in UPDATE_FIELDS
    }
    if not update_values:
        return get_reminder(reminder_id, session=session)

    row = session.get(ReminderRow, reminder_id)
    if row is None:
        return None

    if (
        update_values.get("is_completed") is True
        and "completed_at" not in update_values
    ):
        update_values["completed_at"] = datetime.now(timezone.utc)
    elif (
        update_values.get("is_completed") is False
        and "completed_at" not in update_values
    ):
        update_values["completed_at"] = None

    for field, value in update_values.items():
        setattr(row, field, value)

    session.flush()
    session.refresh(row)
    return Reminder.model_validate(row)
