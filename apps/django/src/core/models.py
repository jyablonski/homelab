from django.conf import settings
from django.core.validators import MaxValueValidator, RegexValidator
from django.db import models
from django.db.models.functions import Now

_FLAG_NAME_VALIDATOR = RegexValidator(
    regex=r"^[a-z][a-z0-9_]*$",
    message="Flag name must be snake_case (lowercase letters, digits, underscores).",
)


class FeatureFlag(models.Model):
    """Schema for `feature_flags`; non-Django services read this table via SQL."""

    flag_name = models.CharField(
        max_length=100,
        primary_key=True,
        validators=[_FLAG_NAME_VALIDATOR],
    )
    is_enabled = models.BooleanField(default=False)
    rollout_percentage = models.PositiveSmallIntegerField(
        default=100,
        validators=[MaxValueValidator(100)],
    )
    description = models.TextField(blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="modified_flags",
    )

    class Meta:
        db_table = "feature_flags"
        ordering = ["flag_name"]

    def __str__(self) -> str:
        return str(self.flag_name)


class Reminder(models.Model):
    reminder_type = models.TextField()
    reminder_message = models.TextField()
    reminder_start_date = models.DateField()
    reminder_end_date = models.DateField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "personal_reminders"
        indexes = [
            models.Index(
                fields=["is_completed", "reminder_start_date", "reminder_end_date"],
                name="idx_personal_reminders_active",
            ),
            models.Index(fields=["reminder_type"], name="idx_personal_reminders_type"),
        ]

    def __str__(self) -> str:
        reminder_type = str(self.reminder_type)
        reminder_message = str(self.reminder_message)
        return f"{reminder_type}: {reminder_message[:64]}"


class EventsNba(models.Model):
    """Landing table for upcoming NBA games (written by Dagster)."""

    source_event_id = models.TextField(unique=True)
    league = models.TextField()
    event_name = models.TextField()
    event_start = models.DateTimeField()
    status = models.TextField(blank=True, null=True)
    home_team = models.TextField(blank=True, null=True)
    away_team = models.TextField(blank=True, null=True)
    venue = models.TextField(blank=True, null=True)
    source = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_default=Now())
    modified_at = models.DateTimeField()

    class Meta:
        db_table = "events_nba"

    def __str__(self) -> str:
        return str(self.event_name)


class EventsCs(models.Model):
    """Landing table for upcoming CS2 matches (written by Dagster)."""

    source_event_id = models.TextField(unique=True)
    league = models.TextField()
    event_name = models.TextField()
    event_start = models.DateTimeField()
    status = models.TextField(blank=True, null=True)
    team1 = models.TextField(blank=True, null=True)
    team2 = models.TextField(blank=True, null=True)
    tournament = models.TextField(blank=True, null=True)
    maps = models.TextField(blank=True, null=True)
    rating = models.IntegerField(blank=True, null=True)
    source = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_default=Now())
    modified_at = models.DateTimeField()

    class Meta:
        db_table = "events_cs"

    def __str__(self) -> str:
        return str(self.event_name)


class EventsUfc(models.Model):
    """Landing table for upcoming UFC cards (written by Dagster)."""

    source_event_id = models.TextField(unique=True)
    league = models.TextField()
    event_name = models.TextField()
    event_start = models.DateTimeField()
    location = models.TextField(blank=True, null=True)
    source_url = models.TextField(blank=True, null=True)
    source = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_default=Now())
    modified_at = models.DateTimeField()

    class Meta:
        db_table = "events_ufc"

    def __str__(self) -> str:
        return str(self.event_name)


class EventsUfcFighter(models.Model):
    """Fighter rows for upcoming UFC cards (written by Dagster)."""

    source_event_id = models.TextField()
    fighter_id = models.TextField()
    fighter_name = models.TextField()
    bout_id = models.TextField(blank=True, null=True)
    corner = models.TextField(blank=True, null=True)
    outcome = models.TextField(blank=True, null=True)
    source = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_default=Now())
    modified_at = models.DateTimeField()

    class Meta:
        db_table = "events_ufc_fighters"
        constraints = [
            models.UniqueConstraint(
                fields=["source_event_id", "fighter_id"],
                name="uniq_events_ufc_fighters_event_fighter",
            )
        ]

    def __str__(self) -> str:
        return str(self.fighter_name)
