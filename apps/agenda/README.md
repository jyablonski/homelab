# Agenda

Next.js app for personal reminders and a daily agenda view. Design and rollout
plan: `notes/ideas/frontend-app.md`.

After deployment, access the app through Traefik at `http://agenda.home`.

## Directory Structure

```text
apps/agenda/
├── src/
│   ├── app/            # Routes (App Router): pages, layout, route handlers
│   ├── components/     # Shared UI primitives
│   ├── features/       # Domain UI: agenda, events, reminders
│   ├── lib/            # Server-only API clients, config, dates, schemas
│   └── test/           # Vitest setup and fixture factories
├── Dockerfile           # Container build
├── secrets.sops.yaml    # Encrypted runtime secrets (shared API key)
└── values.yaml          # Helm values for workload chart
```

All calls to `apps/api` happen server-side (Server Components, route handlers,
and Server Actions in `src/lib/api/*` and `src/features/*/*-actions.ts`) using
`AGENDA_API_BASE_URL` and `AGENDA_API_KEY`. The API key is never exposed to the
browser.

## Local Development

```bash
cd apps/agenda
npm ci
npm run dev
```

```bash
npm run lint
npm run typecheck
npm test
npm run build
```

## Deployment

Build and push through the repository helper:

```bash
make image-build-push SERVICE=agenda
```

The API key shared with `apps/api` is sourced from
`apps/agenda/secrets.sops.yaml`. Edit it with:

```bash
sops apps/agenda/secrets.sops.yaml
```

## Known Gaps

- Authentik SSO is not wired up yet (planned as the final rollout step in
  `notes/ideas/frontend-app.md`); the agenda UI is currently unauthenticated.
- The backend has no `is_archived`/`archived_at` fields or archive endpoints
  yet, so there is no Archived view or archive/unarchive actions in this V1.
- "Upcoming" grouping (`active`/`due-soon`/`upcoming`) is computed client-side
  in `src/lib/api/reminders.ts` against the plain reminders list, since there
  is no `/reminders?status=` or `/reminders/due-soon` endpoint yet.
