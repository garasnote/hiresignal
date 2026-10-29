-- Marts: one file, one question each. These feed the dashboard and the README.

create or replace table mart_ats_share as
select a.ats, count(*) as postings,
       round(100.0 * count(*) / (select count(*) from fact_posting), 1) as pct
from fact_posting f join dim_ats a using (ats_key)
group by 1 order by postings desc;

create or replace table mart_top_countries as
select l.country, count(*) as postings,
       round(100.0 * count(*) / (select count(*) from fact_posting), 1) as pct
from fact_posting f join dim_location l using (location_key)
group by 1 order by postings desc;

create or replace table mart_role_mix as
select r.role_family, count(*) as postings,
       round(100.0 * count(*) / (select count(*) from fact_posting), 1) as pct
from fact_posting f join dim_role r using (role_key)
group by 1 order by postings desc;

create or replace table mart_top_companies as
select c.name, count(*) as postings, count(distinct f.title) as distinct_titles
from fact_posting f join dim_company c using (company_key)
group by 1 order by postings desc, 2 desc limit 20;

create or replace table mart_remote as
select l.is_remote, count(*) as postings,
       round(100.0 * count(*) / (select count(*) from fact_posting), 1) as pct
from fact_posting f join dim_location l using (location_key)
group by 1 order by postings desc;

create or replace table mart_junior_share as
select r.role_family,
       count(*) as postings,
       sum(case when f.is_junior then 1 else 0 end) as junior,
       round(100.0 * sum(case when f.is_junior then 1 else 0 end) / count(*), 1) as junior_pct
from fact_posting f join dim_role r using (role_key)
group by 1 order by postings desc;

create or replace table mart_monthly as
select d.year, d.month, count(*) as postings
from fact_posting f join dim_date d using (date_key)
group by 1, 2 order by 1, 2;

create or replace table mart_quality as
select
    (select count(*) from stg_postings)                                   as rows_landed,
    (select count(*) from stg_dedup)                                      as rows_after_dedupe,
    (select count(*) from dim_company)                                    as companies,
    (select count(*) from fact_posting where description_chars >= 200)    as with_body,
    (select count(*) from fact_posting where date_key is null)            as without_date;
