RSS_FEED_SEEN_GUIDS = """
SELECT entry_guid
FROM source.rss_feed_entries
WHERE feed_url = %s
"""

RSS_FEED_CLAIM_ENTRY = """
INSERT INTO source.rss_feed_entries (feed_url, entry_guid)
VALUES (%s, %s)
ON CONFLICT (feed_url, entry_guid) DO NOTHING
RETURNING entry_guid
"""
