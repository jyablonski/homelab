from datetime import date, datetime, timezone

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Boolean, Date, DateTime, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ReminderRow(Base):
    __tablename__ = "personal_reminders"
    __table_args__ = (
        Index(
            "idx_personal_reminders_active",
            "is_completed",
            "reminder_start_date",
            "reminder_end_date",
        ),
        Index("idx_personal_reminders_type", "reminder_type"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    reminder_type: Mapped[str] = mapped_column(Text)
    reminder_message: Mapped[str] = mapped_column(Text)
    reminder_start_date: Mapped[date] = mapped_column(Date)
    reminder_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        onupdate=_utc_now,
    )


class ReminderBase(BaseModel):
    reminder_type: str = Field(min_length=1)
    reminder_message: str = Field(min_length=1)
    reminder_start_date: date
    reminder_end_date: date | None = None


class ReminderCreate(ReminderBase):
    pass


class ReminderUpdate(BaseModel):
    reminder_type: str | None = Field(default=None, min_length=1)
    reminder_message: str | None = Field(default=None, min_length=1)
    reminder_start_date: date | None = None
    reminder_end_date: date | None = None
    is_completed: bool | None = None
    completed_at: datetime | None = None


class Reminder(ReminderBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_completed: bool
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
