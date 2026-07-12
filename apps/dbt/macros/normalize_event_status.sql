/*
 * The completed branch is a full-string match (no surrounding %) and is checked
 * last so stage labels like "Grand Final" / "Semifinal" and statuses like
 * "Incomplete" fall through to scheduled instead of being bucketed as completed.
 */
{% macro normalize_event_status(status, live_pattern='live|progress') -%}
    case
        when lower(coalesce({{ status }}, '')) like '%postponed%' then 'postponed'
        when lower(coalesce({{ status }}, '')) similar to '%(cancelled|canceled)%' then 'cancelled'
        when lower(coalesce({{ status }}, '')) similar to '%({{ live_pattern }})%' then 'in_progress'
        when lower(coalesce({{ status }}, '')) similar to '(final%|completed?|finished)' then 'completed'
        else 'scheduled'
    end
{%- endmacro %}
