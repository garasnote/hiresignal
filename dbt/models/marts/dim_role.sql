{{ config(materialized='table') }}

select row_number() over (order by role_family) as role_key, role_family
from (select distinct role_family from {{ ref('int_postings_deduped') }})
