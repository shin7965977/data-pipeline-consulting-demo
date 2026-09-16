{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set default_schema = target.schema -%}
    {%- if target.name == 'duckdb' -%}
        {{ default_schema }}
    {%- elif custom_schema_name is none -%}
        {{ default_schema }}
    {%- elif custom_schema_name | trim == 'gold' -%}
        platzi_gold
    {%- elif custom_schema_name | trim == 'silver' -%}
        platzi_silver
    {%- else -%}
        {{ default_schema }}_{{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
