{{ config(materialized='table') }}

select
    (select count(*) from {{ ref('stg_postings') }})                                as rows_landed,
    (select count(*) from {{ ref('int_postings_deduped') }})                         as rows_after_dedupe,
    (select count(*) from {{ ref('dim_company') }})                                  as companies,
    (select count(*) from {{ ref('fct_postings') }} where description_chars >= 200)  as with_body,
    (select count(*) from {{ ref('fct_postings') }} where date_key is null)          as without_date
