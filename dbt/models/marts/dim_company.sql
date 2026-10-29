{{ config(materialized='table') }}

select row_number() over (order by company_norm) as company_key, company_norm,
       any_value(company) as name
from {{ ref('int_postings_deduped') }} where company_norm <> '' group by company_norm

-- Unknown member: a posting with no company is still a posting.
union all select 0 as company_key, '' as company_norm, '(unknown)' as name
