with source as (
    select * from {{ source('platzi_bronze', 'raw_products') }}
),

renamed as (
    select
        cast(product_id as integer) as product_id,
        cast(title as string) as product_title,
        cast(price as numeric) as unit_price,
        cast(category_id as integer) as category_id,
        cast(category_name as string) as category_name,
        cast(updated_at as timestamp) as updated_at
    from source
)

select * from renamed
