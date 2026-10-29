{{ config(materialized='table') }}

select d.year, d.month, count(*) as postings
from {{ ref('fct_postings') }} f join {{ ref('dim_date') }} d using (date_key)
group by 1, 2 order by 1, 2
