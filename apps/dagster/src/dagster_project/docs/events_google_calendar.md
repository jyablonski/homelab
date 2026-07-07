### Google Calendar Sync

Pulls upcoming events for each configured Google account/calendar into `source.events_google_calendar`. Runs on the `calendar_sync` schedule (every 6 hours, `America/Los_Angeles`) and can be manually materialized at any time.

Kept in its own job, separate from `daily_events`, so a Google auth failure never makes the sports event syncs look failed, and a failure on one account never blocks the other account's sync.

#### Fetch window

- `timeMin = now - CALENDAR_LOOKBACK_DAYS` (default `1` day)
- `timeMax = now + CALENDAR_FORWARD_WINDOW_DAYS` (default `14` days)
- Recurring events are expanded (`singleEvents=true`); cancelled instances are kept with `status=cancelled` rather than dropped.
- Rows inside the fetch window that were not seen in the latest successful pull for an account/calendar are marked `cancelled` (soft-delete), never hard-deleted.

#### Config (`secrets.sops.yaml`)

- `GOOGLE_CALENDAR_CLIENT_ID` / `GOOGLE_CALENDAR_CLIENT_SECRET` — the shared OAuth client. One Google Cloud project/OAuth client covers every account; each account still grants access separately.
- `GOOGLE_CALENDAR_ACCOUNTS_JSON` — a JSON array of `{"email", "refresh_token", "calendar_id", "label"}` objects, one per authorized account.

`CALENDAR_LOOKBACK_DAYS` / `CALENDAR_FORWARD_WINDOW_DAYS` are non-secret and live in `values-common.yaml`.

#### Authorizing an account (one-time, per account)

```bash
UV_CACHE_DIR=/tmp/uv-cache /home/jacob/.local/bin/uv run --directory apps/dagster \
  python scripts/authorize_google_calendar.py \
  --client-id "<oauth client id>" \
  --client-secret "<oauth client secret>" \
  --email jyablonski9@gmail.com \
  --label personal
```

Opens a browser for the read-only Calendar consent screen and prints the account's JSON entry — it never writes the token to disk. Copy that entry into the `GOOGLE_CALENDAR_ACCOUNTS_JSON` array via `sops apps/dagster/secrets.sops.yaml`. Repeat once per account; if Workspace policy blocks the work account, the personal calendar still syncs on its own.

#### Re-auth / troubleshooting

Refresh tokens can be revoked or expire (7-day expiry is common while the OAuth app is in Google's "testing" publishing status). A failed account shows up as `google_calendar fetch failed for <email> ...` in this run's logs, and the run's metadata reports `accounts_failed`. Re-run the helper above for the affected account and update its entry in `GOOGLE_CALENDAR_ACCOUNTS_JSON`.

#### Non-goals

No write access to Google Calendar, no RSVP handling, no attendee ingestion, no push-notification webhook. See `notes/ideas/calendar-sync-dagster-pipeline.md` for the full design.
