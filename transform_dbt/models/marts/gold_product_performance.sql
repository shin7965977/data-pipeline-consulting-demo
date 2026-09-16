{{ config(materialized='table') }}

with products as (
    select * from {{ ref('dim_products') }}
),

items as (
    select * from {{ ref('fct_order_items') }}
),

orders as (
    select * from {{ ref('fct_orders') }}
),

item_metrics as (
    select
        i.product_id,
        count(distinct i.order_id) as orders_containing_product,
        sum(case when o.order_status = 'completed' then i.quantity else 0 end) as units_sold,
        sum(case when o.order_status = 'completed' then i.subtotal else 0 end) as completed_sales_amount,
        sum(case when o.order_status = 'refunded' then i.quantity else 0 end) as refunded_units
    from items i
    left join orders o
        on i.order_id = o.order_id
    group by i.product_id
),

final as (
    select
        p.product_id,
        p.product_title,
        p.category_id,
        p.category_name,
        p.unit_price,
        coalesce(im.orders_containing_product, 0) as total_order_appearances,
        coalesce(im.units_sold, 0) as units_sold,
        round(coalesce(im.completed_sales_amount, 0), 2) as completed_sales_amount,
        coalesce(im.refunded_units, 0) as refunded_units
    from products p
    left join item_metrics im
        on p.product_id = im.product_id
)

select * from final
order by completed_sales_amount desc
