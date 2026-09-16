with source as (
    select * from {{ source('platzi_bronze', 'raw_orders') }}
),

renamed as (
    select
        cast(order_id as string) as order_id,
        cast(customer_id as integer) as customer_id,
        cast(order_status as string) as order_status,
        cast(currency as string) as currency,
        cast(gross_amount as numeric) as gross_amount,
        cast(discount_amount as numeric) as discount_amount,
        cast(net_amount as numeric) as net_amount,
        cast(payment_method as string) as payment_method,
        cast(created_at as timestamp) as created_at,
        cast(updated_at as timestamp) as updated_at
    from source
)

select * from renamed
