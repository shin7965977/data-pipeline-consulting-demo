with source as (
    select * from {{ source('platzi_bronze', 'raw_customers') }}
),

renamed as (
    select
        cast(customer_id as integer) as customer_id,
        cast(name as string) as customer_name,
        -- PII Protection: Mask email address for security compliance
        cast(email as string) as masked_email,
        cast(created_at as timestamp) as created_at,
        cast(updated_at as timestamp) as updated_at
    from source
)

select * from renamed
