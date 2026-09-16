{{ config(materialized='table') }}

with orders as (
    select * from {{ ref('fct_orders') }}
),

daily_aggregation as (
    select
        cast(date(created_at) as date) as order_date,
        count(distinct order_id) as total_orders,
        count(distinct case when order_status = 'completed' then order_id end) as completed_orders,
        count(distinct case when order_status = 'cancelled' then order_id end) as cancelled_orders,
        count(distinct case when order_status = 'refunded' then order_id end) as refunded_orders,
        sum(gross_amount) as gmv,
        sum(discount_amount) as total_discount_amount,
        sum(case when order_status = 'completed' then net_amount else 0 end) as net_revenue,
        sum(case when order_status = 'refunded' then gross_amount else 0 end) as refunded_amount
    from orders
    group by 1
),

final as (
    select
        order_date,
        total_orders,
        completed_orders,
        cancelled_orders,
        refunded_orders,
        round(gmv, 2) as gmv,
        round(total_discount_amount, 2) as total_discount_amount,
        round(net_revenue, 2) as net_revenue,
        round(refunded_amount, 2) as refunded_amount,
        round(
            case
                when completed_orders > 0 then net_revenue / completed_orders
                else 0
            end,
            2
        ) as aov,
        round(
            case
                when total_orders > 0 then (cancelled_orders * 1.0) / total_orders
                else 0
            end,
            4
        ) as cancellation_rate,
        round(
            case
                when total_orders > 0 then (refunded_orders * 1.0) / total_orders
                else 0
            end,
            4
        ) as refund_rate
    from daily_aggregation
)

select * from final
order by order_date desc
