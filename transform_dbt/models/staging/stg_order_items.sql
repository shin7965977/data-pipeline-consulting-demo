with source as (
    select * from {{ source('platzi_bronze', 'raw_order_items') }}
),

renamed as (
    select
        cast(item_id as string) as item_id,
        cast(order_id as string) as order_id,
        cast(product_id as integer) as product_id,
        cast(unit_price as numeric) as unit_price,
        cast(quantity as integer) as quantity,
        cast(subtotal as numeric) as subtotal
    from source
)

select * from renamed
