{{ config(materialized='table') }}

with customers as (
    select * from {{ ref('dim_customers') }}
),

orders as (
    select * from {{ ref('fct_orders') }}
),

customer_orders as (
    select
        customer_id,
        min(date(created_at)) as first_order_date,
        max(date(created_at)) as last_order_date,
        count(distinct order_id) as total_order_count,
        count(distinct case when order_status = 'completed' then order_id end) as completed_order_count,
        sum(case when order_status = 'completed' then net_amount else 0 end) as lifetime_net_revenue
    from orders
    group by customer_id
),

final as (
    select
        c.customer_id,
        c.customer_name,
        c.masked_email,
        coalesce(co.first_order_date, cast(date(c.created_at) as date)) as first_order_date,
        co.last_order_date,
        coalesce(co.total_order_count, 0) as total_orders,
        coalesce(co.completed_order_count, 0) as completed_orders,
        round(coalesce(co.lifetime_net_revenue, 0), 2) as lifetime_net_revenue,
        case
            when coalesce(co.lifetime_net_revenue, 0) >= 500 then 'Platinum'
            when coalesce(co.lifetime_net_revenue, 0) >= 250 then 'Gold'
            when coalesce(co.lifetime_net_revenue, 0) >= 100 then 'Silver'
            else 'Bronze'
        end as customer_tier
    from customers c
    left join customer_orders co
        on c.customer_id = co.customer_id
)

select * from final
order by lifetime_net_revenue desc
