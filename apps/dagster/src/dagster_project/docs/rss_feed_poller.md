Polls the configured RSS and Atom feeds every 30 minutes and posts unseen entries to Discord as MonitoRSS-style embeds.

#### Configuration

The `rss_feed_poller` op accepts one global `discord_webhook_url` and a `feeds` list. Every feed item requires only `name` and `url`. Launch a run with config shaped like this:

```yaml
ops:
  rss_feed_poller:
    config:
      discord_webhook_url: https://discord.com/api/webhooks/...
      feeds:
        - name: DHH
          url: https://world.hey.com/dhh/feed.atom
```

The built-in schedule uses the two seed feeds from the op module and resolves their global webhook URL from `RSS_FEED_DISCORD_WEBHOOK_URL`. Configure that environment variable through the Dagster SOPS secret before enabling the schedule. A webhook URL is never included in logs.

#### State and failure behavior

Posted GUID/ID values are stored in `source.rss_feed_entries` in the source Postgres database. State is scoped to the feed URL and entry GUID/ID. The table is owned by the Django `core` migration and must exist before the Dagster job runs.

Each feed request has a 10-second timeout. Non-200 responses, request failures, timeouts, and malformed XML are logged as warnings and skipped while the remaining feeds continue. Discord posts also use a 10-second timeout, and an entry is recorded only after Discord accepts the post. New posts in a run are separated by 2 seconds.

The poller supports RSS 2.0 and Atom through `feedparser`. Entries use their `guid` or `id` as the deduplication key, and embed descriptions are limited to 300 characters.
