TRUNCATE
    source.events_nba,
    source.events_cs,
    source.events_ufc,
    source.events_ufc_fighters
RESTART IDENTITY CASCADE;

INSERT INTO source.events_nba (
    source_event_id,
    league,
    event_name,
    event_start,
    status,
    home_team,
    away_team,
    venue,
    source,
    modified_at
)
VALUES
    (
        'nba-scheduled',
        'NBA',
        'Los Angeles Lakers at Golden State Warriors',
        current_timestamp + interval '3 hours',
        '7:00 PM ET',
        'Golden State Warriors',
        'Los Angeles Lakers',
        'Chase Center',
        'nba',
        current_timestamp
    ),
    (
        'nba-completed',
        'NBA',
        'Boston Celtics at New York Knicks',
        current_timestamp - interval '3 hours',
        'Final',
        'New York Knicks',
        'Boston Celtics',
        'Madison Square Garden',
        'nba',
        current_timestamp
    );

INSERT INTO source.events_cs (
    source_event_id,
    league,
    event_name,
    event_start,
    status,
    team1,
    team2,
    tournament,
    maps,
    rating,
    source,
    modified_at
)
VALUES (
    'cs-live',
    'CS2',
    'Team Spirit vs Vitality',
    current_timestamp,
    'live',
    'Team Spirit',
    'Vitality',
    'IEM',
    'bo3',
    5,
    'hltv',
    current_timestamp
);

INSERT INTO source.events_ufc (
    source_event_id,
    league,
    event_name,
    event_start,
    location,
    source_url,
    source,
    modified_at
)
VALUES (
    'ufc-scheduled',
    'UFC',
    'UFC Fight Night',
    current_timestamp + interval '8 hours',
    'Las Vegas, NV',
    'https://example.test/ufc-scheduled',
    'espn',
    current_timestamp
);

INSERT INTO source.events_ufc_fighters (
    source_event_id,
    fighter_id,
    fighter_name,
    bout_id,
    corner,
    outcome,
    source,
    modified_at
)
VALUES
    (
        'ufc-scheduled',
        'fighter-red',
        'Red Corner',
        'bout-main',
        'red',
        NULL,
        'espn',
        current_timestamp
    ),
    (
        'ufc-scheduled',
        'fighter-blue',
        'Blue Corner',
        'bout-main',
        'blue',
        NULL,
        'espn',
        current_timestamp
    );
