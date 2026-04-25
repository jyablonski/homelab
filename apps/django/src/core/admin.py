from django.contrib import admin

from .models import Reminder


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "reminder_type",
        "reminder_message",
        "reminder_start_date",
        "reminder_end_date",
        "is_completed",
        "updated_at",
    )
    list_filter = ("is_completed", "reminder_type", "reminder_start_date")
    search_fields = ("reminder_message", "reminder_type")
