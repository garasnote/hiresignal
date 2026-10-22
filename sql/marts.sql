-- Marts: the tables a BI tool or a human actually reads.
DROP VIEW IF EXISTS mart_market_by_family;
CREATE VIEW mart_market_by_family AS
SELECT
    r.family                                   AS role_family,
    COUNT(*)                                   AS offers,
    SUM(f.is_junior)                           AS junior_offers,
    ROUND(100.0 * SUM(f.is_junior) / COUNT(*), 1) AS junior_share_pct,
    COUNT(DISTINCT c.country)                  AS countries,
    ROUND(AVG(f.salary_min_cop))               AS avg_salary_min_cop
FROM fact_offer f
JOIN dim_role r    ON r.role_key = f.role_key
JOIN dim_country c ON c.country_key = f.country_key
GROUP BY r.family
ORDER BY offers DESC;

DROP VIEW IF EXISTS mart_salary_by_family;
CREATE VIEW mart_salary_by_family AS
SELECT
    r.family                        AS role_family,
    COUNT(*)                        AS offers_with_salary,
    MIN(f.salary_min_cop)           AS min_cop,
    ROUND(AVG(f.salary_min_cop))    AS avg_cop,
    MAX(f.salary_max_cop)           AS max_cop
FROM fact_offer f
JOIN dim_role r ON r.role_key = f.role_key
WHERE f.salary_min_cop IS NOT NULL
GROUP BY r.family
ORDER BY avg_cop DESC;

DROP VIEW IF EXISTS mart_funnel_by_country;
CREATE VIEW mart_funnel_by_country AS
SELECT
    c.country                      AS country,
    s.status                       AS status,
    COUNT(*)                       AS applications,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY c.country), 1) AS pct_of_country
FROM fact_application a
JOIN dim_country c ON c.country_key = a.country_key
JOIN dim_status  s ON s.status_key = a.status_key
GROUP BY c.country, s.status
ORDER BY c.country, applications DESC;

DROP VIEW IF EXISTS mart_weekly_applications;
CREATE VIEW mart_weekly_applications AS
SELECT
    d.week                         AS week,
    c.country                      AS country,
    COUNT(*)                       AS applications,
    SUM(CASE WHEN s.status IN ('Interview','Offer') THEN 1 ELSE 0 END) AS progressed
FROM fact_application a
JOIN dim_date d    ON d.date_key = a.date_key
JOIN dim_country c ON c.country_key = a.country_key
JOIN dim_status s  ON s.status_key = a.status_key
GROUP BY d.week, c.country
ORDER BY d.week;

DROP VIEW IF EXISTS mart_offer_sources;
CREATE VIEW mart_offer_sources AS
SELECT
    source                                   AS source,
    COUNT(*)                                 AS offers,
    SUM(CASE WHEN salary_raw IS NOT NULL AND lower(salary_raw) NOT LIKE '%confidencial%'
             THEN 1 ELSE 0 END)              AS with_salary,
    MIN(scraped_at)                          AS first_seen,
    MAX(scraped_at)                          AS last_seen
FROM raw_offers
GROUP BY source;
