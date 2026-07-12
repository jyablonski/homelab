/* Build stable event identifiers from the source namespace and source event ID. */
{% macro event_key(event_source, source_event_id) -%}
    md5(concat_ws(':', {{ event_source }}, {{ source_event_id }}::text))
{%- endmacro %}
