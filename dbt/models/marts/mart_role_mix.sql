{{ config(materialized='table') }}

select r.role_family, count(*) as postings,
       round(100.0 * count(*) / (select count(*) from {{ ref('fct_postings') }}), 1) as pct
from {{ ref('fct_postings') }} f join {{ ref('dim_role') }} r using (role_key)
group by 1 order by postings desc
