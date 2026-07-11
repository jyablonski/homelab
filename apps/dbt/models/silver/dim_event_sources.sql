select
    {{ event_source_key('event_source') }} as event_source_id,
    event_source,
    source_name,
    category,
    league
from (
    values
    ('nba', 'NBA schedule', 'sports', 'NBA'),
    ('cs2', 'HLTV schedule', 'sports', 'CS2'),
    ('ufc', 'UFC schedule', 'sports', 'UFC')
) as sources (event_source, source_name, category, league)
