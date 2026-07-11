{% macro event_source_key(event_source) -%}
    md5({{ event_source }})
{%- endmacro %}

{% macro event_key(event_source, source_event_id) -%}
    md5(concat_ws(':', {{ event_source }}, {{ source_event_id }}::text))
{%- endmacro %}

{% macro participant_key(event_source, participant_source_id, participant_name) -%}
    md5(concat_ws(
        ':',
        {{ event_source }},
        coalesce({{ participant_source_id }}::text, lower(trim({{ participant_name }})))
    ))
{%- endmacro %}
