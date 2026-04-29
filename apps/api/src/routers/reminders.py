import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from crud import reminders
from dependencies import DatabaseSession
from database_models.reminder import Reminder, ReminderCreate, ReminderUpdate

router = APIRouter(prefix="/reminders", tags=["reminders"])
logger = logging.getLogger(__name__)


@router.get("", response_model=list[Reminder])
def list_reminders(
    session: DatabaseSession,
    include_completed: bool = False,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Reminder]:
    return reminders.list_reminders(
        include_completed=include_completed,
        limit=limit,
        offset=offset,
        session=session,
    )


@router.get("/{reminder_id}", response_model=Reminder)
def get_reminder(reminder_id: int, session: DatabaseSession) -> Reminder:
    reminder = reminders.get_reminder(reminder_id, session=session)
    if reminder is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="reminder not found",
        )
    return reminder


@router.post("", response_model=Reminder, status_code=status.HTTP_201_CREATED)
def create_reminder(reminder: ReminderCreate, session: DatabaseSession) -> Reminder:
    created_reminder = reminders.create_reminder(reminder, session=session)
    session.commit()
    logger.info(
        "reminder created",
        extra={
            "reminder_id": created_reminder.id,
            "reminder_type": created_reminder.reminder_type,
        },
    )
    return created_reminder


@router.patch("/{reminder_id}", response_model=Reminder)
def update_reminder(
    reminder_id: int,
    reminder: ReminderUpdate,
    session: DatabaseSession,
) -> Reminder:
    changes = reminder.model_dump(exclude_unset=True)
    updated_reminder = reminders.update_reminder(
        reminder_id,
        changes,
        session=session,
    )
    if updated_reminder is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="reminder not found",
        )
    session.commit()
    logger.info(
        "reminder updated",
        extra={
            "reminder_id": updated_reminder.id,
            "changed_fields": sorted(changes),
            "is_completed": updated_reminder.is_completed,
        },
    )
    return updated_reminder
