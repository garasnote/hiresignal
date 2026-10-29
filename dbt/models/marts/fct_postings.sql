{{ config(materialized='table') }}

select
    row_number() over (order by s.url) as posting_key,
    coalesce(c.company_key, 0) as company_key, a.ats_key, l.location_key, r.role_key, d.date_key,
    s.url, s.title, s.description_chars,
    regexp_matches(lower(s.title), '\b(junior|jr|entry|graduate|trainee|intern)\b') as is_junior
from {{ ref('int_postings_deduped') }} s
left join {{ ref('dim_company') }}  c on c.company_norm = s.company_norm
left join {{ ref('dim_ats') }}      a on a.ats = s.ats
left join {{ ref('dim_location') }} l on l.location_norm = s.location_norm
left join {{ ref('dim_role') }}     r on r.role_family = s.role_family
left join {{ ref('dim_date') }}     d on d.date = cast(try_cast(s.posted_at_raw as timestamp) as date)
