{{ config(materialized='table') }}

select row_number() over (order by ats) as ats_key, ats
from (select distinct ats from {{ ref('int_postings_deduped') }} where ats is not null)
