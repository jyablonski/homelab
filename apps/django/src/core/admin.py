from django.contrib import admin

from .models import FeatureFlag, Reminder


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = (
        "flag_name",
        "is_enabled",
        "rollout_percentage",
        "expires_at",
        "last_modified_by",
        "updated_at",
    )
    list_editable = ("is_enabled", "rollout_percentage")
    search_fields = ("flag_name",)
    list_filter = ("is_enabled",)
    readonly_fields = ("created_at", "updated_at", "last_modified_by")

    def save_model(self, request, obj, form, change):
        if request.user.is_authenticated:
            obj.last_modified_by = request.user
        super().save_model(request, obj, form, change)


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
