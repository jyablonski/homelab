from django.db import models


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
        return f"{self.reminder_type}: {self.reminder_message[:64]}"
