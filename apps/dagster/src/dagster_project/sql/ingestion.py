# The homelab source schema is populated by the Django/API services. Ingestion
# assets read from it rather than mutating it.
COUNT_REMINDERS = "SELECT count(*) FROM source.reminders"

LATEST_REMINDER_TS = "SELECT max(created_at) FROM source.reminders"
