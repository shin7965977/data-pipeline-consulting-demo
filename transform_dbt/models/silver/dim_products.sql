{{ config(materialized='table') }}

with products as (
    select * from {{ ref('stg_products') }}
)

select
    product_id,
    product_title,
    unit_price,
    category_id,
    category_name,
    updated_at
from products
