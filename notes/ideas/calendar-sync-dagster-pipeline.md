# Calendar Sync Dagster Pipeline

## Goal

Pull upcoming Google Calendar events from:

- Personal Google account: `jyablonski9@gmail.com`
- Work Google Workspace account: `jacob.yablonski@axios.com`

Land the events in PostgreSQL through Dagster so the existing FastAPI agenda endpoint can show them in `apps/agenda` alongside reminders and sports events.

The smallest useful version should answer: "What is on my calendar today and over the next couple of weeks?" without making the frontend talk to Google or PostgreSQL directly.

## Assumptions

- V1 is read-only. The homelab should not create, update, RSVP to, or delete Google Calendar events.
- V1 only needs event summaries, start/end times, calendar/account labels, status, and enough metadata for debugging. It should not ingest attachments, Meet links, attendee lists, or full descriptions unless there is a clear agenda need.
- `apps/dagster` remains the owner of scheduled external data ingestion.
- Django remains the owner of PostgreSQL migrations for app-visible tables.
- FastAPI remains the owner of agenda/event response contracts consumed by `apps/agenda`.
- `America/Los_Angeles` remains the user-facing agenda timezone.

## Current behavior

`apps/dagster` already has scheduled event ingestion for NBA, CS2, and UFC data. Those assets land rows into `source.events_*` tables through `PostgresResource.merge_polars`.

`apps/api` already exposes:

- `GET /v1/events/upcoming`
- `GET /v1/agenda/today`

The API response shape already has a generic `AgendaEvent` model, but `apps/api/src/crud/agenda.py` still uses dummy events until a real normalized event query exists.

## Desired behavior

Dagster should periodically fetch upcoming Google Calendar events for both configured accounts, upsert them into PostgreSQL, and record enough freshness metadata for the agenda UI/API to show stale or failed sync state.

FastAPI should merge calendar rows with the other event sources behind the existing agenda/event endpoints. `apps/agenda` should keep calling FastAPI and should not learn about Google auth, calendar IDs, or storage details.

## Recommended approach

Start with a simple windowed pull, not push notifications:

- Run a Dagster schedule every 4-6 hours, plus allow manual materialization.
- Fetch from `now - 1 day` through `now + 14 days` or `now + 21 days`.
- Use `singleEvents=true` so recurring events are expanded into concrete instances.
- Use a per-run `sync_run_id` or `seen_at` timestamp and soft-delete/mark stale rows in the fetched window that were not seen in the latest successful pull.
- Keep raw payload snippets in a `jsonb` column for debugging, but expose only sanitized fields in API responses.

A once-daily pull of the next 2 weeks is enough for a first personal dashboard if stale data for same-day meeting edits is acceptable. For a daily agenda, 4-6-hour refreshes are a better default because calendar changes often happen the morning of. Push notifications are not worth the extra public webhook, channel renewal, and ingress exposure for V1.

## Auth mechanism

Use Google OAuth 2.0 user consent with offline access and read-only Calendar API scopes. The key model is: one Google Cloud project/OAuth client identifies the homelab app, then each Google account grants that app delegated read access separately. The app does not receive blanket calendar access by existing in Google Cloud; it only receives access for accounts that complete the consent flow.

Recommended Google Cloud setup:

1. Create one Google Cloud project for the homelab calendar sync app.
2. Enable the Google Calendar API in that project.
3. Configure the OAuth consent screen.
4. Use an external audience if the same app needs to authorize both the personal Gmail account and the Axios Workspace account.
5. Create one OAuth client for the local one-time helper. A Desktop app client is probably the simplest fit because the helper runs locally and only needs to capture an authorization response once per account.
6. Publish the OAuth app when feasible instead of leaving it in testing mode long-term, because testing-mode external apps can receive short-lived refresh tokens for non-profile scopes.

One-time authorization flow:

1. Run the local helper and sign in as `jyablonski9@gmail.com`.
2. Google shows a consent screen saying the homelab app wants read-only access to calendar events.
3. Approve the requested scope.
4. The helper receives an account-specific refresh token for `jyablonski9@gmail.com`.
5. Store that refresh token, plus the shared OAuth client ID/client secret, in `apps/dagster/secrets.sops.yaml`.
6. Run the same helper again and sign in as `jacob.yablonski@axios.com`.
7. If Axios Workspace policy allows this OAuth client/scope, Google issues a second refresh token for the work account.
8. If Axios blocks it, the helper should fail with a Google admin/policy error and the personal calendar sync can still ship independently.

Scheduled Dagster flow:

1. Dagster reads the OAuth client ID, OAuth client secret, and one refresh token per configured account from Kubernetes secrets generated from `apps/dagster/secrets.sops.yaml`.
2. For each account, Dagster exchanges that account's refresh token for a short-lived access token.
3. Dagster calls Google Calendar API `events.list` for the configured calendars, usually `primary` for each account in V1.
4. Dagster writes normalized calendar rows into PostgreSQL.
5. FastAPI reads PostgreSQL and serves the existing agenda/event API contracts to `apps/agenda`.

The permission model should look like:

```text
Google Cloud project / OAuth client
  |
  +-- jyablonski9@gmail.com grants calendar.events.readonly
  |     -> refresh token A
  |
  +-- jacob.yablonski@axios.com grants calendar.events.readonly, if Axios policy allows
        -> refresh token B

Dagster stores and uses refresh token A/B to pull calendar events.
```

Preferred scope:

```text
https://www.googleapis.com/auth/calendar.events.readonly
```

Fallback scope if calendar list discovery is needed:

```text
https://www.googleapis.com/auth/calendar.readonly
```

For a private homelab app, publishing the OAuth app matters. A Google Cloud project with an external OAuth app left in testing mode can issue refresh tokens that expire after 7 days for non-profile scopes. Put the app into production if Google allows it for this use, or expect periodic re-auth. If the Axios account is blocked from authorizing the app, an Axios Workspace admin would need to trust or allow the OAuth client.

Do not use a service account for the personal Gmail calendar. Service accounts do not naturally have access to consumer Gmail calendar data. Domain-wide delegation can work for Google Workspace domains only when the Workspace admin configures it, which is unlikely to be appropriate for a personal homelab reading an Axios work calendar.

## Potential blockers

- Axios Workspace app access controls may block `jacob.yablonski@axios.com` from granting a personal Google Cloud OAuth client access to Calendar data.
- OAuth app testing mode can make refresh tokens expire after 7 days.
- Calendar scopes are sensitive enough that Google may show an unverified-app warning unless the OAuth app is properly configured or published.
- Work calendar policy could require periodic re-auth or block third-party apps via `admin_policy_enforced`.
- Some event data may be too private for homelab storage. Avoid descriptions, attendees, attachments, conference links, and location details in V1 unless explicitly needed.
- Recurring events and cancelled instances need careful handling. Fetch expanded single events and support `status=cancelled` instead of assuming every returned row is active.
- Full incremental sync tokens are useful later, but they do not combine cleanly with `timeMin`/`timeMax` window filters. A bounded refetch is simpler and safer for V1.
- API quota should be fine for two calendars and low-frequency polling, but the implementation should still use pagination and backoff.

## Likely files / areas touched

- `apps/dagster/pyproject.toml` - add Google client dependencies, likely `google-api-python-client`, `google-auth`, and `google-auth-oauthlib`.
- `apps/dagster/src/dagster_project/resources/google_calendar.py` - new resource that builds authorized Calendar API clients from SOPS-backed refresh token config.
- `apps/dagster/src/dagster_project/defs/assets/ingestion/events_google_calendar.py` - new asset that fetches configured calendars and lands rows into Postgres.
- `apps/dagster/src/dagster_project/defs/jobs/events.py` - include the new calendar asset group in the scheduled event refresh or add a separate `daily_calendar`/`calendar_sync` job.
- `apps/dagster/src/dagster_project/common/config.py` - add sync window and refresh cadence settings if they should be environment-configurable.
- `apps/dagster/secrets.sops.yaml` - add OAuth client and per-account refresh token values.
- `apps/django/src/core/models.py` - add a calendar event landing model and, optionally, sync state/freshness model.
- `apps/django/src/core/migrations/` - create the tables and indexes.
- `apps/api/src/api_models/agenda.py` - extend `AgendaEvent` only if calendar display needs fields that do not fit the current contract.
- `apps/api/src/crud/agenda.py` - replace dummy events with a real query that unions calendar events with existing event source tables or a future gold view.
- `apps/api/tests/test_agenda.py` - cover calendar rows in `/agenda/today`.
- `apps/dagster/tests/unit/test_event_pipeline.py` or a new `test_google_calendar_pipeline.py` - parser, pagination, auth config, and landing behavior.
- `notes/ideas/frontend-app.md` - optionally update the existing frontend plan once calendar sync is accepted.

## Data model

Use a narrow landing table first:

```text
source.events_google_calendar
```

Suggested columns:

- `id bigserial primary key`
- `account_email text not null`
- `calendar_id text not null`
- `calendar_summary text null`
- `source_event_id text not null`
- `source_instance_id text not null`
- `event_name text not null`
- `event_start timestamptz not null`
- `event_end timestamptz null`
- `is_all_day boolean not null default false`
- `status text not null`
- `transparency text null`
- `visibility text null`
- `location text null`
- `html_link text null`
- `raw jsonb not null default '{}'::jsonb`
- `source text not null default 'google_calendar'`
- `last_seen_at timestamptz not null`
- `created_at timestamptz not null default now()`
- `modified_at timestamptz not null`

Suggested constraints and indexes:

- Unique key on `(account_email, calendar_id, source_instance_id)`.
- Index on `(event_start, event_end)`.
- Index on `(account_email, calendar_id, last_seen_at)`.
- Optional index on `status`.

For recurring events, prefer a stable `source_instance_id` based on Google's returned event `id` for expanded instances. Also retain the original event ID or `recurringEventId` in `raw` for debugging.

If sync/freshness becomes useful beyond Dagster metadata, add:

```text
source.event_source_freshness
```

Suggested columns:

- `source text not null`
- `source_key text not null`
- `last_success_at timestamptz null`
- `last_attempt_at timestamptz null`
- `status text not null`
- `message text null`
- `metadata jsonb not null default '{}'::jsonb`
- primary key on `(source, source_key)`

For calendar sync, `source_key` can be `google_calendar:jyablonski9@gmail.com` and `google_calendar:jacob.yablonski@axios.com`.

## Implementation plan

1. Add PostgreSQL tables through Django migrations.
   - Create `EventsGoogleCalendar`.
   - Add freshness table only if the first API integration needs stale/failure indicators immediately.
   - Keep storage in the existing `source,public` search path conventions.

2. Add Google Calendar OAuth config.
   - Add encrypted fields to `apps/dagster/secrets.sops.yaml`.
   - Store one refresh token per account.
   - Store calendar IDs explicitly instead of discovering every subscribed calendar by default.
   - Suggested config shape:

```yaml
googleCalendar:
  clientId: ENC[...]
  clientSecret: ENC[...]
  accounts:
    - email: jyablonski9@gmail.com
      refreshToken: ENC[...]
      calendars:
        - id: primary
          label: personal
    - email: jacob.yablonski@axios.com
      refreshToken: ENC[...]
      calendars:
        - id: primary
          label: work
```

3. Add a one-time local auth helper.
   - Put it under `apps/dagster/scripts/authorize_google_calendar.py` or `scripts/authorize-google-calendar.py`.
   - It should print only the fields that need to be copied into SOPS.
   - It should request `access_type=offline`, `prompt=consent` when refreshing a missing refresh token, and the read-only calendar-events scope.
   - It should never write plaintext tokens into tracked files.

4. Add a Google Calendar resource in Dagster.
   - Build `google.oauth2.credentials.Credentials` from refresh token settings.
   - Use the Calendar API `events.list` endpoint with pagination.
   - Keep the resource thin; parsing and row shaping should live near the asset.

5. Add the calendar ingestion asset.
   - Group name: `calendar` or `google_calendar`.
   - Fetch all configured account/calendar pairs.
   - Request:
     - `timeMin = now - 1 day`
     - `timeMax = now + EVENT_FORWARD_WINDOW_DAYS`
     - `singleEvents = true`
     - `orderBy = startTime`
     - `showDeleted = true`
   - Parse timed and all-day events.
   - Skip events with no usable start.
   - Mark cancelled events rather than dropping them immediately.
   - Upsert rows with `PostgresResource.merge_polars`.
   - After a successful fetch for a calendar, mark rows in that window that were not seen in the run as stale/cancelled or delete them if hard deletion is preferred.

6. Add Dagster schedule coverage.
   - Option A: include the calendar group in `daily_events_job` and raise its schedule to every 4-6 hours.
   - Option B: create a separate `calendar_sync_job` with schedule `0 */6 * * *` in `America/Los_Angeles`.
   - Prefer Option B if Google auth failures should not make sports event syncs look failed.

7. Replace API dummy events.
   - Query calendar rows where `event_start < window.end` and `coalesce(event_end, event_start) >= window.start`.
   - Exclude cancelled events by default, or include them with `status="cancelled"` only if the UI will render them intentionally.
   - Map to existing `AgendaEvent` shape:

```json
{
  "id": "google_calendar:work:<source_instance_id>",
  "source": "google_calendar",
  "category": "calendar",
  "league": "Calendar",
  "title": "Team planning",
  "start_at": "2026-07-03T10:00:00-07:00",
  "status": "confirmed",
  "metadata": {
    "account": "jacob.yablonski@axios.com",
    "calendar": "work",
    "is_all_day": false
  }
}
```

The existing `league` field is sports-shaped. For V1, either set it to `Calendar` for calendar events or rename it in the API contract if the frontend can tolerate the change.

8. Add UI grouping only if needed.
   - `apps/agenda` can already render generic events.
   - Add source/category labels or icons only after the API returns real calendar rows.

9. Document operational setup.
   - Add a short `apps/dagster/README.md` section for Google Calendar auth.
   - Include the re-auth command, SOPS edit path, and how to manually materialize the asset from Dagster UI.

## Incremental sync later

Google Calendar supports incremental sync with `nextSyncToken`, but the incremental request has strict query compatibility rules and cannot be mixed with `timeMin`, `timeMax`, or `updatedMin` in the way a rolling 2-week agenda window wants.

Use bounded refetch for V1. Consider sync tokens later if:

- API quota becomes a problem.
- More calendars are added.
- The homelab starts storing long event history.
- Near-real-time updates matter.

If sync tokens are added later, store one token per `(account_email, calendar_id)` and handle `410 Gone` by wiping that calendar's local state and doing a new full sync.

## Tests

- Unit test Google event parsing:
  - timed event
  - all-day event
  - recurring expanded instance
  - cancelled event
  - missing summary
  - missing/invalid start
  - work and personal account labels
- Unit test pagination handling for `events.list`.
- Unit test that token/config loading never logs secrets.
- Unit test `PostgresResource.merge_polars` call inputs for conflict keys and update columns.
- Integration test migration/table shape if adding models in Django.
- API tests for `/events/upcoming` and `/agenda/today` with calendar rows in the requested window.
- API tests that events outside the window and cancelled events are handled intentionally.
- Run:

```bash
UV_CACHE_DIR=/tmp/uv-cache /home/jacob/.local/bin/uv run --directory apps/dagster pytest
UV_CACHE_DIR=/tmp/uv-cache /home/jacob/.local/bin/uv run --directory apps/api pytest
UV_CACHE_DIR=/tmp/uv-cache /home/jacob/.local/bin/uv run --directory apps/django pytest
make validate
```

## Risks / edge cases

- A meeting moved from inside the fetch window to outside it will disappear from the current agenda. That is fine, but the sync should not leave an old in-window copy behind.
- All-day events use `date` rather than `dateTime`; store them as LA-local all-day rows and set `is_all_day=true`.
- Private events may have limited fields. Use `"Busy"` or Google's summary if available, and do not treat missing location/description as a failure.
- Multiple calendars can expose duplicate events. V1 should only sync explicitly configured calendars, probably `primary` for each account, to avoid duplicate subscribed calendars.
- Timezone conversion must be deterministic. Store UTC/timestamptz, render in `America/Los_Angeles`.
- Refresh tokens can be revoked or expire. Surface this as freshness `fetch_failed` with a clear re-auth message, not as an empty agenda.
- If Axios blocks OAuth, the personal calendar can still ship first. Keep account configs independent so one failed account does not prevent the other from syncing.

## Non-goals

- No write access to Google Calendar.
- No RSVP handling.
- No attendee ingestion.
- No email/Gmail access.
- No push-notification webhook in V1.
- No frontend direct calls to Google APIs.
- No historical calendar warehouse beyond the rolling agenda window.
- No service-account/domain-wide-delegation path unless Axios explicitly supports it.

## Definition of done

- A Dagster asset can sync the personal calendar into PostgreSQL using encrypted OAuth refresh-token config.
- The work calendar either syncs successfully or is documented as blocked by Axios Workspace policy with a clear fallback.
- Calendar events appear in `GET /v1/events/upcoming` and `GET /v1/agenda/today`.
- `apps/agenda` shows calendar events without direct storage or Google API access.
- Sync failures show up as freshness metadata rather than silent empty results.
- Unit and API tests cover parsing, storage mapping, and agenda responses.
- The setup docs explain OAuth consent, SOPS token storage, re-auth, and the chosen polling cadence.

## Reference docs checked

- Google Calendar API scopes: <https://developers.google.com/workspace/calendar/api/auth>
- Google Calendar `events.list` parameters: <https://developers.google.com/workspace/calendar/api/v3/reference/events/list>
- Google Calendar incremental synchronization: <https://developers.google.com/workspace/calendar/api/guides/sync>
- Google OAuth 2.0 offline access and refresh tokens: <https://developers.google.com/identity/protocols/oauth2/web-server>
- Google OAuth refresh-token expiration behavior: <https://developers.google.com/identity/protocols/oauth2>
- Google Workspace app access controls: <https://support.google.com/a/answer/7281227>
