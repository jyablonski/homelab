with participant_metadata as (
    select
        event_participants.event_id,
        jsonb_agg(
            jsonb_strip_nulls(
                jsonb_build_object(
                    'name', participants.participant_name,
                    'role', event_participants.participant_role,
                    'bout_id', event_participants.bout_id,
                    'outcome', event_participants.outcome
                )
            )
            order by event_participants.bout_id, event_participants.participant_role
        ) as participants
    from {{ ref('fct_event_participants') }} as event_participants
    inner join {{ ref('dim_event_participants') }} as participants
        on event_participants.participant_id = participants.participant_id
    group by event_participants.event_id
)

select
    events.event_id as id,
    sources.event_source as source,
    sources.category,
    sources.league,
    events.event_title as title,
    events.starts_at as start_at,
    events.event_status as status,
    jsonb_strip_nulls(
        jsonb_build_object(
            'location', events.location_name,
            'source_url', events.source_url,
            'competition', events.competition_name,
            'maps', events.maps,
            'rating', events.rating,
            'participants', participant_metadata.participants
        )
    ) as metadata,
    events.source_modified_at,
    current_timestamp as __dbt_generated_at
from {{ ref('fct_events') }} as events
inner join {{ ref('dim_event_sources') }} as sources
    on events.event_source_id = sources.event_source_id
left join participant_metadata
    on events.event_id = participant_metadata.event_id
