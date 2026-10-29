{{ config(materialized='view') }}

select
    trim(url)                   as url,
    nullif(trim(title), '')     as title,
    nullif(trim(company), '')   as company,
    nullif(trim(location), '')  as location,
    nullif(trim(ats), '')       as ats,
    nullif(trim(posted_at), '') as posted_at_raw,
    length(description)         as description_chars,
    description
from read_parquet('{{ var('postings_parquet') }}')
