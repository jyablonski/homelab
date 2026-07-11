with deduplicated as (
    select
        *,
        {{ latest_row_number('event_id, participant_id') }} as row_number
    from {{ ref('stg_event_participants') }}
)

select
    event_id,
    participant_id,
    participant_role,
    bout_id,
    outcome,
    source_modified_at
from deduplicated
where row_number = 1
