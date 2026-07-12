with deduplicated as (
    select
        *,
        {{ latest_row_number('participant_id') }} as row_number
    from {{ ref('stg_event_participants') }}
)

select
    participant_id,
    event_source_id,
    event_source,
    source_participant_id,
    participant_name,
    participant_type,
    source_modified_at,
    current_timestamp as __dbt_generated_at
from deduplicated
where row_number = 1
