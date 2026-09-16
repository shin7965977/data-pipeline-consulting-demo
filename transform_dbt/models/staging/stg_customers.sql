with source as (
    select * from {{ source('platzi_bronze', 'raw_customers') }}
),

renamed as (
    select
        cast(customer_id as integer) as customer_id,
        -- PII Protection: Mask customer name and cryptographically hash email
        cast(concat(substr(cast(name as string), 1, 1), '***') as string) as customer_name,
        {% if target.name == 'duckdb' %}
        cast(sha256(cast(email as string)) as string) as masked_email,
        {% else %}
        cast(to_hex(sha256(cast(email as string))) as string) as masked_email,
        {% endif %}
        cast(created_at as timestamp) as created_at,
        cast(updated_at as timestamp) as updated_at
    from source
)

select * from renamed
