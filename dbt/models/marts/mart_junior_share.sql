{{ config(materialized='table') }}

select r.role_family,
       count(*) as postings,
       sum(case when f.is_junior then 1 else 0 end) as junior,
       round(100.0 * sum(case when f.is_junior then 1 else 0 end) / count(*), 1) as junior_pct
from {{ ref('fct_postings') }} f join {{ ref('dim_role') }} r using (role_key)
group by 1 order by postings desc
