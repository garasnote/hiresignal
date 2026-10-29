{{ config(materialized='table') }}

select row_number() over (order by location_norm) as location_key, location_norm,
       any_value(location) as raw, any_value(country) as country, bool_or(is_remote) as is_remote
from {{ ref('int_postings_deduped') }} group by location_norm
