{{ config(materialized='table') }}

select c.name, count(*) as postings, count(distinct f.title) as distinct_titles
from {{ ref('fct_postings') }} f join {{ ref('dim_company') }} c using (company_key)
group by 1 order by postings desc, 2 desc limit 20
