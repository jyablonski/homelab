#!/usr/bin/env python3
"""One-time local helper to authorize a Google account for calendar sync.

Run this once per account (personal, then work). It opens a browser for the
Google OAuth consent screen requesting read-only Calendar access, then prints
the account's config entry for GOOGLE_CALENDAR_ACCOUNTS_JSON. Nothing is ever
written to disk; copy the printed JSON into apps/dagster/secrets.sops.yaml
yourself (`sops apps/dagster/secrets.sops.yaml`).

Usage:
    UV_CACHE_DIR=/tmp/uv-cache /home/jacob/.local/bin/uv run --directory apps/dagster \\
        python scripts/authorize_google_calendar.py \\
        --client-id "<oauth client id>" \\
        --client-secret "<oauth client secret>" \\
        --email jyablonski9@gmail.com \\
        --label personal

Client id/secret can also come from GOOGLE_CALENDAR_CLIENT_ID /
GOOGLE_CALENDAR_CLIENT_SECRET so they don't need to be typed on the command line.
"""

from __future__ import annotations

import argparse
import json
import sys
from os import getenv

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar.events.readonly"]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--client-id",
        default=getenv("GOOGLE_CALENDAR_CLIENT_ID", ""),
        help="OAuth client ID (defaults to GOOGLE_CALENDAR_CLIENT_ID env var).",
    )
    parser.add_argument(
        "--client-secret",
        default=getenv("GOOGLE_CALENDAR_CLIENT_SECRET", ""),
        help="OAuth client secret (defaults to GOOGLE_CALENDAR_CLIENT_SECRET env var).",
    )
    parser.add_argument(
        "--email",
        required=True,
        help="Google account email being authorized, e.g. jyablonski9@gmail.com.",
    )
    parser.add_argument(
        "--calendar-id",
        default="primary",
        help="Calendar ID to sync for this account (default: primary).",
    )
    parser.add_argument(
        "--label",
        default="",
        help="Human-readable label for this account, e.g. personal or work.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=0,
        help="Local port for the OAuth redirect server (0 picks a free port).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.client_id or not args.client_secret:
        print(
            "Missing OAuth client id/secret. Pass --client-id/--client-secret or "
            "set GOOGLE_CALENDAR_CLIENT_ID/GOOGLE_CALENDAR_CLIENT_SECRET.",
            file=sys.stderr,
        )
        return 1

    client_config = {
        "installed": {
            "client_id": args.client_id,
            "client_secret": args.client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
    credentials = flow.run_local_server(
        port=args.port,
        access_type="offline",
        prompt="consent",
    )

    if not credentials.refresh_token:
        print(
            f"No refresh token returned for {args.email}. Google omits it when this "
            "client already has an active grant for the account; revoke prior access "
            "at https://myaccount.google.com/permissions and re-run.",
            file=sys.stderr,
        )
        return 1

    entry = {
        "email": args.email,
        "refresh_token": credentials.refresh_token,
        "calendar_id": args.calendar_id,
        "label": args.label,
    }
    print(f"Authorized {args.email} ({args.calendar_id}).\n")
    print("Add this entry to the GOOGLE_CALENDAR_ACCOUNTS_JSON array in")
    print("apps/dagster/secrets.sops.yaml (`sops apps/dagster/secrets.sops.yaml`):\n")
    print(json.dumps(entry, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
