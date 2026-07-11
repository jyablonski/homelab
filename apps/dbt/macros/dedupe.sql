{#
    Latest-wins dedup shared by the silver models so they all break
    source_modified_at ties the same way. Expects source_modified_at and
    source_created_at columns in scope.
#}
{% macro latest_row_number(partition_by) -%}
    row_number() over (
        partition by {{ partition_by }}
        order by source_modified_at desc, source_created_at desc
    )
{%- endmacro %}
