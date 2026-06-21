# Maintain a small analytics summary table in the source database. Created on
# demand so the export asset is self-contained for a fresh environment.
CREATE_REMINDERS_SUMMARY = """
CREATE TABLE IF NOT EXISTS source.reminders_summary (
    snapshot_date date PRIMARY KEY,
    reminder_count integer NOT NULL,
    refreshed_at timestamptz NOT NULL DEFAULT now()
)
"""

UPSERT_REMINDERS_SUMMARY = """
INSERT INTO source.reminders_summary (snapshot_date, reminder_count)
VALUES (current_date, %s)
ON CONFLICT (snapshot_date)
DO UPDATE SET reminder_count = excluded.reminder_count, refreshed_at = now()
"""
