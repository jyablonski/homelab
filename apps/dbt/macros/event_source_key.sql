/* Build stable identifiers for source-system namespaces. */
{% macro event_source_key(event_source) -%}
    md5({{ event_source }})
{%- endmacro %}
