# Personal Reminders Service for Homelab

## Goal

Build a self-hosted reminders system backed by PostgreSQL with a basic frontend for managing reminders and Home Assistant integration for displaying active reminders on dashboards.

## Motivation

Home Assistant works well as a dashboard and automation layer, but it shouldn't own all personal data directly. A dedicated reminders service gives the homelab a structured place to store personal reminders while letting Home Assistant query and display them.

The architecture stays simple:

```text
Frontend App → Reminders API → PostgreSQL
                                    ↓
                          Home Assistant SQL Sensor
                                    ↓
                          Home Assistant Dashboard
```

## Scope

V1 supports:

- Creating, viewing, and editing reminders
- Marking reminders complete
- Optional reminder end dates
- Basic reminder categories
- Displaying active reminders in Home Assistant

Out of scope for v1: user accounts, push notifications, recurring reminders, calendar integrations, mobile app, multi-user permissions.

## Data Model

```sql
create table personal_reminders (
    id serial primary key,
    reminder_type text not null,
    reminder_message text not null,
    reminder_start_date date not null,
    reminder_end_date date,
    is_completed boolean not null default false,
    completed_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index idx_personal_reminders_active
on personal_reminders (is_completed, reminder_start_date, reminder_end_date);

create index idx_personal_reminders_type
on personal_reminders (reminder_type);
```

## Reminder Semantics

A reminder is active when:

```sql
is_completed = false
and current_date >= reminder_start_date
and (
    reminder_end_date is null
    or current_date <= reminder_end_date
)
```

- `reminder_end_date`: stop showing after this date
- `is_completed`: explicitly handled
- `completed_at`: when it was completed

## Reminder Types

Free-text initially, with these starting values: `general`, `maintenance`, `bill`, `health`, `house`, `car`, `homelab`. Can promote to an enum later if the set stabilizes.

## Backend API

```text
GET    /api/reminders
GET    /api/reminders/active
POST   /api/reminders
PATCH  /api/reminders/{id}
POST   /api/reminders/{id}/complete
DELETE /api/reminders/{id}
```

Create payload:

```json
{
  "reminder_type": "maintenance",
  "reminder_message": "Replace HVAC filter",
  "reminder_start_date": "2026-05-01",
  "reminder_end_date": "2026-05-07"
}
```

Active response:

```json
[
  {
    "id": 1,
    "reminder_type": "maintenance",
    "reminder_message": "Replace HVAC filter",
    "reminder_start_date": "2026-05-01",
    "reminder_end_date": "2026-05-07",
    "is_completed": false
  }
]
```

## Frontend

Simple web UI with screens for active reminders, all reminders, and create/edit forms. Actions: add, edit, complete, delete. Filters: active, upcoming, completed, type.

Stack is open: Next.js, SvelteKit, or plain HTML all work.

## Home Assistant Integration

Use the SQL integration to query active reminders:

```sql
select
    count(*) as active_reminder_count,
    string_agg(reminder_message, E'\n- ' order by reminder_start_date) as active_reminders
from personal_reminders
where is_completed = false
  and current_date >= reminder_start_date
  and (
    reminder_end_date is null
    or current_date <= reminder_end_date
  );
```

The sensor exposes the active count as state and the formatted list as an attribute. A Markdown card renders the list on the dashboard.

## Deployment

Three services:

```text
reminders-frontend
reminders-api
postgres
```

Docker Compose for v1, Kubernetes manifests later. Env:

```text
DATABASE_URL=postgresql://user:password@postgres:5432/reminders
API_PORT=8080
```

## Future Enhancements

Recurring reminders, separate due dates vs display windows, priority, tags, notes, audit history, HA actions to complete reminders, HA notifications, calendar export, auth, admin dashboard, full-text search.

## Success Criteria

- Create reminders from a web UI
- Reminders persist in PostgreSQL
- Completed reminders stop appearing as active
- Date-bounded reminders only appear within their window
- Home Assistant displays active reminders on a dashboard
- Simple enough to maintain alongside the rest of the homelab
