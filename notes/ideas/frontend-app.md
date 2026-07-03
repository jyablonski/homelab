# Reminders and Agenda Frontend App

## Goal

Build a personal frontend app for creating reminders and viewing a daily agenda.

The immediate use case is manual reminders like:

- Oil change completed on June 1, 2025; remind me on June 1, 2026 to get it done soon.
- Keurig water filters changed on June 1, 2025; remind me on September 1, 2025 to change them again.

The same app should show useful upcoming information for the next day: personal reminders, social events, NBA games, UFC cards, and other data fetched by homelab pipelines.

This builds on `notes/ideas/reminders-service.md` rather than replacing it.

## Current Repo Shape

The repo already has most of the backend pieces for this idea:

- `apps/api`: FastAPI service with reminder CRUD endpoints backed by PostgreSQL.
- `apps/django`: Django admin, migrations, Authentik SSO, `personal_reminders`, and current event landing table models.
- `apps/dagster`: scheduled pipelines for reminder summaries and upcoming NBA, CS2, and UFC events; dbt integration exists but no dbt project or silver/gold event models are present yet.
- `charts/workload`: reusable Helm chart that can deploy a frontend app with ingress, probes, homepage annotations, and app-owned image defaults.
- `services/home-assistant`: useful future display/automation layer, but not the best owner for reminder data.

There is no JavaScript frontend stack in the repo today, so adding this app also introduces the first Node-based app architecture.

## Recommendation

Create a new Next.js app under `apps/agenda`, deployed at `http://agenda.home`.

Use server-side rendering and server-side route handlers where they help:

- SSR can render the daily dashboard with fresh reminders/events on first load.
- Next.js route handlers can act as a small backend-for-frontend that talks to internal services without exposing every internal service detail to the browser.
- Authentik/OIDC integration will be easier to centralize at the app boundary when this moves beyond a trusted LAN-only tool.
- Agenda views can aggregate reminders and events through FastAPI-owned API endpoints without forcing the browser to coordinate multiple services or query storage directly.
- A Node runtime is acceptable in this repo because the app is personal, low-traffic, and the user already has Next.js experience.

The static SPA option is still simpler operationally, but it is less attractive once auth, backend-owned event aggregation, and personalized dashboard rendering enter the roadmap.

## Architecture

```text
Browser
  |
  v
agenda.home / apps/agenda (Next.js)
  |
  +--> FastAPI reminders, events, and agenda APIs
  |
  +--> Authentik/OIDC session handling

PostgreSQL
  ^
  |
  +-- Django migrations/admin
  +-- Dagster scheduled event pipelines
```

Use PostgreSQL as the source of truth. Use Django for migrations and admin fallbacks. Use FastAPI for application-facing data APIs. Use Dagster for scheduled ingestion and refreshes. Use Home Assistant as a display or automation surface, not as the reminder database.

Data ownership rule: Django owns reminder source/bronze schema and admin fallback, Dagster currently lands raw event source tables, future dbt models should own silver/gold event normalization and enrichment, and FastAPI should own the backend contracts consumed by the frontend.

Frontend rule: `apps/agenda` should not query PostgreSQL directly. Next.js can use SSR and route handlers for UI/session behavior, but reminders, events, and agenda data should come from FastAPI-owned domain endpoints.

Service auth rule: browser requests terminate at `apps/agenda`; server-side Next.js calls to `apps/api` should include a shared API key so reminder/event APIs are not anonymously callable from other clients by default.

User auth rule: add Authentik SSO to `apps/agenda`, but do it as the final implementation step after the app, backend contracts, and service-to-service API key path are working.

## App Scope

V1 should include manual reminders, daily view, and events:

- Require Authentik SSO before showing the agenda UI.
- Show active reminders for today.
- Show reminders due soon, defined as incomplete reminders starting within the next 7 days.
- Show events in the next 24 hours.
- Show stale or fetch-failed indicators for event data when upstream refresh metadata indicates a problem.
- Show upcoming reminders grouped by date.
- Show completed reminders separately.
- Group agenda items by date and source.
- Create reminders with category, message, reminder date, and optional end date.
- Edit existing reminders.
- Complete, reopen, archive, or unarchive reminders.
- Handle empty states and API errors gracefully.

Out of scope for V1:

- Mobile push notifications.
- Multi-user sharing.
- Complex recurrence rules.
- Calendar sync.
- Home Assistant actions to create/edit reminders.
- Event preferences such as followed teams, leagues, fighters, or calendars.

## Backend Changes

Keep the existing reminder data model for now:

- `reminder_type`
- `reminder_message`
- `reminder_start_date`
- `reminder_end_date`
- `is_completed`
- `completed_at`
- `is_archived`
- `archived_at`
- timestamps

Use `America/Los_Angeles` for user-facing date windows such as today, due soon, and next 24 hours.

Add or clarify API behavior around reminder visibility:

- Active: incomplete and `reminder_start_date <= current_date`, with `reminder_end_date` unset or not yet passed.
- Upcoming: incomplete and `reminder_start_date > current_date`.
- Due soon: incomplete and `reminder_start_date` between today and today plus 7 days.
- Completed: `is_completed = true`.
- Archived: `is_archived = true`, hidden from default active/upcoming/completed lists unless explicitly requested.

Useful API additions:

```text
GET  /reminders?status=active|upcoming|completed|all
GET  /reminders/due-soon?days=7
POST /reminders/{id}/complete
POST /reminders/{id}/reopen
POST /reminders/{id}/archive
POST /reminders/{id}/unarchive
```

The existing `PATCH /reminders/{id}` endpoint can still power complete/reopen in the first implementation if adding dedicated actions feels premature.

For event display, add a normalized API instead of having the frontend query each landing table directly:

```text
GET /events/upcoming?hours=24
```

That endpoint can merge `events_nba`, `events_cs`, and `events_ufc` into one common agenda item shape.

Implement the first version of event APIs against the current source/landing tables if needed, but keep the response contract stable so the backing query can move to dbt-owned silver/gold views once the dbt project exists.

Future dbt work should normalize and enrich event data into final gold-layer views that FastAPI can read directly; until then, FastAPI may do only the minimum mapping needed for the V1 agenda contract.

Add a backend-composed agenda endpoint for the Next.js daily dashboard:

```text
GET /agenda/today?hours=24
```

That endpoint should return active reminders, due-soon reminders, and upcoming events in one response so the SSR path has one stable backend contract.

Recommended V1 response shape:

```json
{
  "generated_at": "2026-07-03T15:00:00-07:00",
  "timezone": "America/Los_Angeles",
  "window": {
    "start": "2026-07-03T15:00:00-07:00",
    "end": "2026-07-04T15:00:00-07:00",
    "due_soon_days": 7
  },
  "reminders": {
    "active": [
      {
        "id": 1,
        "type": "car",
        "message": "Get oil changed soon",
        "start_date": "2026-06-01",
        "end_date": null,
        "is_completed": false,
        "is_archived": false
      }
    ],
    "due_soon": [],
    "completed": []
  },
  "events": [
    {
      "id": "nba:0022600001",
      "source": "nba",
      "category": "sports",
      "league": "NBA",
      "title": "Los Angeles Lakers at Golden State Warriors",
      "start_at": "2026-07-03T19:30:00-07:00",
      "status": "scheduled",
      "metadata": {
        "home_team": "Golden State Warriors",
        "away_team": "Los Angeles Lakers",
        "venue": "Chase Center"
      }
    }
  ],
  "freshness": [
    {
      "source": "nba",
      "last_success_at": "2026-07-03T06:05:00-07:00",
      "status": "fresh",
      "message": null
    }
  ]
}
```

Keep the response shape intentionally boring: stable IDs, source/category labels, LA-local timestamps for display, raw-ish metadata for source-specific details, and a separate freshness array for stale/fetch-failed indicators.

Resolve the current reminder table naming drift before relying on reminder summaries: Django/API use `personal_reminders` through the `source,public` search path, while the Dagster reminders pipeline currently reads `source.reminders`.

Add API key auth between `apps/agenda` and `apps/api`: store the backend copy in `apps/api/secrets.sops.yaml`, store the frontend copy in a new `apps/agenda/secrets.sops.yaml`, inject both through `secretEnv`, and have Next.js send the key only from server-side code when calling FastAPI.

Use a single internal auth header for V1, preferably `Authorization: Bearer <key>` or `X-Homelab-Api-Key: <key>`, and require it on reminders, events, and agenda endpoints. Leave `/healthz`, `/readyz`, and `/metrics` usable for Kubernetes and Prometheus; decide whether `/docs` is disabled or protected in production.

Keep `api.home` reachable for docs and debugging while V1 is being built. If API key auth makes browser debugging awkward later, prefer preserving good dev ergonomics through protected docs, Tilt links, or port-forward guidance rather than forcing the frontend to bypass FastAPI.

## Frontend Design

Use a work-focused interface, closer to a personal operations dashboard than a marketing page.

Primary views:

- Today: active reminders and upcoming agenda items.
- Due soon: reminders starting within the next 7 days.
- Upcoming: future reminders grouped by date.
- Completed: completed reminder history.
- Archived: lower-priority history view for hidden reminders.
- Editor: create/edit reminder form.

Useful fields in the UI:

- Category: `car`, `house`, `health`, `bill`, `homelab`, `general`.
- Message.
- Reminder date.
- Optional end date.
- Completion state.

The reminder examples above should be supported directly without recurrence: the user records what happened and chooses the next reminder date.

## Next.js App Structure

Use the current Next.js App Router layout with `src/app` for routes, `src/components` for shared UI, `src/features` for domain-specific UI, and `src/lib` for server-only clients, auth helpers, schemas, dates, and utility code.

Recommended `apps/agenda` layout:

```text
apps/agenda/
├── Dockerfile
├── next.config.ts
├── package.json
├── postcss.config.mjs
├── tsconfig.json
├── values.yaml
├── values-dev.yaml.gotmpl
├── secrets.sops.yaml
└── src/
    ├── app/
    │   ├── layout.tsx
    │   ├── globals.css
    │   ├── page.tsx
    │   ├── loading.tsx
    │   ├── error.tsx
    │   ├── not-found.tsx
    │   ├── upcoming/page.tsx
    │   ├── completed/page.tsx
    │   ├── reminders/new/page.tsx
    │   ├── reminders/[id]/edit/page.tsx
    │   ├── auth/callback/route.ts
    │   ├── auth/logout/route.ts
    │   └── healthz/route.ts
    ├── components/
    │   ├── app-shell.tsx
    │   ├── button.tsx
    │   ├── empty-state.tsx
    │   ├── field.tsx
    │   ├── icon-button.tsx
    │   └── status-pill.tsx
    ├── features/
    │   ├── agenda/
    │   │   ├── agenda-list.tsx
    │   │   ├── agenda-section.tsx
    │   │   └── types.ts
    │   ├── events/
    │   │   ├── event-card.tsx
    │   │   └── types.ts
    │   └── reminders/
    │       ├── reminder-card.tsx
    │       ├── reminder-form.tsx
    │       ├── reminder-actions.ts
    │       ├── reminder-list.tsx
    │       └── types.ts
    ├── lib/
    │   ├── api/
    │   │   ├── agenda.ts
    │   │   ├── client.ts
    │   │   ├── events.ts
    │   │   └── reminders.ts
    │   ├── auth/
    │   │   ├── session.ts
    │   │   └── oidc.ts
    │   ├── config.ts
    │   ├── dates.ts
    │   └── schemas.ts
    └── test/
        ├── factories.ts
        └── setup.ts
```

Pages should live only under `src/app` and should stay thin: fetch data, call auth/session helpers, choose layout composition, and delegate real UI to `src/features/*` or `src/components/*`.

Use Server Components by default for pages and read-only dashboard/list components, because the official guidance is that layouts and pages are Server Components unless interactivity or browser APIs are needed.

Use Client Components only for interactive islands: reminder forms, complete/reopen buttons, tabs or filters that update without navigation, menus, modals, optimistic UI, and anything needing `useState`, event handlers, `useEffect`, or browser APIs.

Keep backend API calls in `src/lib/api/*`, not inside random components. These helpers should run server-side, read `AGENDA_API_BASE_URL` and `AGENDA_API_KEY`, add the internal auth header, parse/validate responses, and normalize API errors for the UI.

Do not expose the internal API key through `NEXT_PUBLIC_*` variables, client components, browser route handlers, or rendered props.

Use Next.js route handlers only for agenda-owned concerns: `auth/callback`, `auth/logout`, `healthz`, and any browser-facing form/action endpoint that needs to translate a user session into a server-side FastAPI call.

Use FastAPI for domain APIs and persistence-facing logic: reminders, events, agenda aggregation, completion/reopen actions, and filtering semantics.

For styling, use Tailwind CSS for most component layout and visual styling, `src/app/globals.css` for Tailwind import plus app-wide CSS variables/base rules, and CSS Modules only when a component needs scoped CSS that is awkward or noisy with utilities.

Avoid a large UI framework for V1; use small local primitives in `src/components` plus `lucide-react` icons so the app stays easy to inspect and theme.

Use route groups only if the app gains clearly different shells later, such as `(app)` for authenticated pages and `(public)` for sign-in/status pages; do not add route groups until they reduce actual routing or layout noise.

Use private folders like `_components` or `_lib` only when colocating implementation details inside a route segment; otherwise prefer the top-level `src/components`, `src/features`, and `src/lib` structure above.

References checked: Next.js project structure, Server and Client Components, fetching data, Backend for Frontend, and CSS docs for latest App Router guidance.

## Implementation Order

1. Build the FastAPI domain contracts first: reminder filters, due-soon reminders, normalized upcoming events, and `/agenda/today`.
2. Add service-to-service API key auth between `apps/agenda` and `apps/api`, with protected domain endpoints, reachable docs/debugging at `api.home`, and unprotected health/readiness/metrics.
3. Build `apps/agenda` as the Next.js SSR frontend against those FastAPI contracts, keeping all API-key usage server-side.
4. Wire deployment and local development: Helmfile release, workload values, SOPS secrets, Tilt, ingress host setup, homepage annotations, and validation.
5. Add Authentik SSO for the frontend last: create an `agenda` OIDC app through Terraform, write `agenda-oauth-secret` in the `apps` namespace, wire OIDC/session env through `secretEnv`, protect all agenda UI routes, and keep health checks public.

## Deployment Plan

Add `apps/agenda` with:

- `package.json`
- `next.config.*`
- `src/` or `app/`
- `Dockerfile`
- `values.yaml`
- `secrets.sops.yaml`
- optional `values-dev.yaml.gotmpl`

Deploy through `charts/workload`:

- release name: `agenda`
- namespace: `apps`
- host: `agenda.home`
- service port: `3000`
- dependencies: `registry/registry`, `apps/api`, and optionally `monitoring/prometheus-operator`
- homepage annotations for discovery on `apps.home`
- `secretEnv` for the API key used by server-side calls from Next.js to FastAPI
- `secretEnv` for Authentik/OIDC client ID, client secret, issuer/authorize/token/userinfo/JWKS URLs, callback URL, scopes, and session secret from `agenda-oauth-secret`

Update local development and bootstrap wiring:

- Add `agenda` to `Tiltfile` app lists and links.
- Add `agenda.home` to the ingress host setup in `Makefile`.
- Ensure `scripts/setup.sh` discovers and builds the image from `apps/agenda`.
- Add a Terraform `agenda_oidc` module using `terraform/modules/authentik_oidc_app`, `meta_launch_url = "http://agenda.home/"`, and callback URL matching the Next.js auth route.

## Home Assistant Integration

Home Assistant can display reminders, but it should not own them.

Good V1 options:

- SQL sensor querying active reminders from PostgreSQL.
- REST sensor calling a summary endpoint from FastAPI or Next.js.
- Markdown dashboard card showing active reminders and today agenda.

Later, Home Assistant actions could complete reminders through an authenticated API call, but creation and editing should stay in the agenda app.

## Validation

Frontend checks to add once `apps/agenda` exists:

```bash
npm ci
npm run lint
npm run typecheck
npm test
npm run build
```

Repo-level checks:

```bash
helmfile template
make validate-fast
make validate
```

Backend tests should cover:

- active/upcoming/completed reminder filters
- due-soon reminder filtering with the 7-day default
- complete, reopen, archive, and unarchive semantics
- reminder end-date visibility
- normalized upcoming events API
- agenda response shape, LA timezone windows, and event freshness statuses
- API key auth accepts valid server-to-server requests and rejects missing or invalid keys on protected endpoints

Frontend tests should cover:

- create reminder payloads for oil change and Keurig examples
- grouping active and upcoming reminders
- due-soon rendering for the 7-day window
- daily agenda rendering with reminders and next-24-hour events
- complete/reopen/archive flows
- stale/fetch-failed event indicators
- empty and API-error states
- Authentik login/logout/session handling once SSO is added

## Open Decisions

- Event preferences such as followed teams, leagues, fighters, calendars, or social sources.
- Whether recurring reminder templates are worth adding after V1, or whether explicit one-off next reminder dates are enough for most personal maintenance use cases.
