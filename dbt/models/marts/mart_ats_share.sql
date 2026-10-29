{{ config(materialized='table') }}

select a.ats, count(*) as postings,
       round(100.0 * count(*) / (select count(*) from {{ ref('fct_postings') }}), 1) as pct
from {{ ref('fct_postings') }} f join {{ ref('dim_ats') }} a using (ats_key)
group by 1 order by postings desc
