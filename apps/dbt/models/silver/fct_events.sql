with nba as (
    select
        {{ event_key("'nba'", 'source_event_id') }} as event_id,
        {{ event_source_key("'nba'") }} as event_source_id,
        'nba'::text as event_source,
        source_event_id::text as source_event_id,
        trim(event_name)::text as event_title,
        event_start::timestamptz as starts_at,
        {{ normalize_event_status(
            'status', live_pattern='live|progress|quarter|half'
        ) }}::text as event_status,
        nullif(trim(venue), '')::text as location_name,
        null::text as source_url,
        null::text as competition_name,
        null::text as maps,
        null::integer as rating,
        source::text as upstream_source,
        created_at::timestamptz as source_created_at,
        modified_at::timestamptz as source_modified_at
    from {{ source('bronze', 'events_nba') }}
),

cs2 as (
    select
        {{ event_key("'cs2'", 'source_event_id') }} as event_id,
        {{ event_source_key("'cs2'") }} as event_source_id,
        'cs2'::text as event_source,
        source_event_id::text as source_event_id,
        trim(event_name)::text as event_title,
        event_start::timestamptz as starts_at,
        {{ normalize_event_status('status') }}::text as event_status,
        null::text as location_name,
        null::text as source_url,
        nullif(trim(tournament), '')::text as competition_name,
        nullif(trim(maps), '')::text as maps,
        rating::integer as rating,
        source::text as upstream_source,
        created_at::timestamptz as source_created_at,
        modified_at::timestamptz as source_modified_at
    from {{ source('bronze', 'events_cs') }}
),

ufc as (
    select
        {{ event_key("'ufc'", 'source_event_id') }} as event_id,
        {{ event_source_key("'ufc'") }} as event_source_id,
        'ufc'::text as event_source,
        source_event_id::text as source_event_id,
        trim(event_name)::text as event_title,
        event_start::timestamptz as starts_at,
        'scheduled'::text as event_status,
        nullif(trim(location), '')::text as location_name,
        nullif(trim(source_url), '')::text as source_url,
        null::text as competition_name,
        null::text as maps,
        null::integer as rating,
        source::text as upstream_source,
        created_at::timestamptz as source_created_at,
        modified_at::timestamptz as source_modified_at
    from {{ source('bronze', 'events_ufc') }}
),

all_events as (
    select * from nba
    union all
    select * from cs2
    union all
    select * from ufc
),

deduplicated as (
    select
        *,
        {{ latest_row_number('event_id') }} as row_number
    from all_events
)

select
    event_id,
    event_source_id,
    event_source,
    source_event_id,
    event_title,
    starts_at,
    event_status,
    location_name,
    source_url,
    competition_name,
    maps,
    rating,
    upstream_source,
    source_created_at,
    source_modified_at,
    current_timestamp as __dbt_generated_at
from deduplicated
where row_number = 1
