/* Build stable participant identifiers, falling back to a normalized name when needed. */
{% macro participant_key(event_source, participant_source_id, participant_name) -%}
    md5(concat_ws(
        ':',
        {{ event_source }},
        coalesce({{ participant_source_id }}::text, lower(trim({{ participant_name }})))
    ))
{%- endmacro %}
