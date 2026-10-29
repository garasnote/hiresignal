{{ config(materialized='table') }}

select row_number() over (order by d) as date_key, d as date, year(d) as year, month(d) as month
from (select distinct cast(try_cast(posted_at_raw as timestamp) as date) as d from {{ ref('int_postings_deduped') }})
where d is not null and year(d) between 2000 and 2100
