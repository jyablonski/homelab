from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from crud import reminders
from database import get_db_session
from database_models.reminder import Reminder, ReminderCreate, ReminderUpdate

router = APIRouter(prefix="/reminders", tags=["reminders"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]


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
    return created_reminder


@router.patch("/{reminder_id}", response_model=Reminder)
def update_reminder(
    reminder_id: int,
    reminder: ReminderUpdate,
    session: DatabaseSession,
) -> Reminder:
    updated_reminder = reminders.update_reminder(
        reminder_id,
        reminder.model_dump(exclude_unset=True),
        session=session,
    )
    if updated_reminder is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="reminder not found",
        )
    session.commit()
    return updated_reminder
