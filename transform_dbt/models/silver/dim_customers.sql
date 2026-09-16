{{ config(materialized='table') }}

with customers as (
    select * from {{ ref('stg_customers') }}
)

select
    customer_id,
    customer_name,
    masked_email,
    created_at,
    updated_at
from customers
