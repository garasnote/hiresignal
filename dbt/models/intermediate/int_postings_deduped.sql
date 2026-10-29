{{ config(materialized='view') }}

with ranked as (
    select *, row_number() over (
        partition by company_norm, title_norm, location_norm
        order by description_chars desc nulls last, url
    ) as rn
    from {{ ref('stg_conformed') }}
)
select * exclude (rn) from ranked where rn = 1
