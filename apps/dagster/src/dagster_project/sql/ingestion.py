# The homelab source schema is populated by the Django/API services. Ingestion
# assets read from it rather than mutating it.
COUNT_REMINDERS = "SELECT count(*) FROM source.reminders"

LATEST_REMINDER_TS = "SELECT max(created_at) FROM source.reminders"

# Cancels rows in the fetch window not seen in the latest successful Google
# Calendar pull for an account/calendar, instead of hard-deleting them.
MARK_STALE_GOOGLE_CALENDAR_EVENTS = """
UPDATE source.events_google_calendar
SET
    status = 'cancelled',
    modified_at = %s
WHERE
    account_email = %s
    AND calendar_id = %s
    AND event_start >= %s
    AND event_start <= %s
    AND last_seen_at < %s
    AND status <> 'cancelled'
"""
