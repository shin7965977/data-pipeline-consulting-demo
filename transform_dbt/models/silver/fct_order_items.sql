{{
    config(
        materialized='incremental',
        unique_key='item_id',
        incremental_strategy='merge'
    )
}}

with items as (
    select * from {{ ref('stg_order_items') }}
),

deduped as (
    select
        item_id,
        order_id,
        product_id,
        unit_price,
        quantity,
        subtotal,
        row_number() over (
            partition by item_id
            order by item_id
        ) as rn
    from items
)

select
    item_id,
    order_id,
    product_id,
    unit_price,
    quantity,
    subtotal
from deduped
where rn = 1
