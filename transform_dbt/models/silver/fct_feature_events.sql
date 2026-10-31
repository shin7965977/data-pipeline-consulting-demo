with stg as (
    select * from {{ ref('stg_ga4_events') }}
)

select
    event_record_id,
    event_date,
    event_name,
    device_category,
    channel_group,
    event_count,
    total_users,
    round(cast(event_count as {{ dbt.type_float() }}) / nullif(total_users, 0), 2) as events_per_user,
    updated_at
from stg
