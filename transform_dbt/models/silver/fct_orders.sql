{{
    config(
        materialized='incremental',
        unique_key='order_id',
        incremental_strategy='merge'
    )
}}

with orders as (
    select * from {{ ref('stg_orders') }}
    {% if is_incremental() %}
    where updated_at >= (select coalesce(max(updated_at), '1970-01-01') from {{ this }})
    {% endif %}
),

deduped as (
    select
        order_id,
        customer_id,
        order_status,
        currency,
        gross_amount,
        discount_amount,
        net_amount,
        payment_method,
        created_at,
        updated_at,
        row_number() over (
            partition by order_id
            order by updated_at desc, created_at desc
        ) as rn
    from orders
)

select
    order_id,
    customer_id,
    order_status,
    currency,
    gross_amount,
    discount_amount,
    net_amount,
    payment_method,
    created_at,
    updated_at
from deduped
where rn = 1
