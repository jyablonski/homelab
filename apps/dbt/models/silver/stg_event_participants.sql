{{ config(materialized='ephemeral') }}

{% set team_branches = [
    ('nba', 'events_nba', 'home_team', 'home'),
    ('nba', 'events_nba', 'away_team', 'away'),
    ('cs2', 'events_cs', 'team1', 'team_1'),
    ('cs2', 'events_cs', 'team2', 'team_2'),
] %}

{% for event_source, table_name, team_column, role in team_branches %}
    select
        {{ event_key("'" ~ event_source ~ "'", 'source_event_id') }} as event_id,
        {{ participant_key("'" ~ event_source ~ "'", 'null', team_column) }} as participant_id,
        {{ event_source_key("'" ~ event_source ~ "'") }} as event_source_id,
        '{{ event_source }}'::text as event_source,
        null::text as source_participant_id,
        trim({{ team_column }})::text as participant_name,
        'team'::text as participant_type,
        '{{ role }}'::text as participant_role,
        null::text as bout_id,
        null::text as outcome,
        created_at::timestamptz as source_created_at,
        modified_at::timestamptz as source_modified_at,
        current_timestamp as __dbt_generated_at
    from {{ source('bronze', table_name) }}
    where nullif(trim({{ team_column }}), '') is not null

    union all

{% endfor %}
select
    {{ event_key("'ufc'", 'source_event_id') }} as event_id,
    {{ participant_key("'ufc'", 'fighter_id', 'fighter_name') }} as participant_id,
    {{ event_source_key("'ufc'") }} as event_source_id,
    'ufc'::text as event_source,
    fighter_id::text as source_participant_id,
    trim(fighter_name)::text as participant_name,
    'fighter'::text as participant_type,
    coalesce(nullif(trim(corner), ''), 'fighter')::text as participant_role,
    nullif(trim(bout_id), '')::text as bout_id,
    nullif(trim(outcome), '')::text as outcome,
    created_at::timestamptz as source_created_at,
    modified_at::timestamptz as source_modified_at,
    current_timestamp as __dbt_generated_at
from {{ source('bronze', 'events_ufc_fighters') }}
where nullif(trim(fighter_name), '') is not null
