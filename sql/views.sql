-- ============================================================
--  Retail Sales Intelligence  |  views.sql
--  Reusable views. Each one encapsulates a join or aggregation
--  that would otherwise be repeated across many queries.
--
--  Apply after schema.sql:
--      sqlite3 data/processed/superstore.db < sql/views.sql
-- ============================================================

-- ------------------------------------------------------------
-- 1. Monthly summary - the spine of every trend visual.
-- ------------------------------------------------------------
DROP VIEW IF EXISTS vw_monthly_summary;
CREATE VIEW vw_monthly_summary AS
SELECT
    STRFTIME('%Y-%m', order_date)                        AS year_month,
    CAST(STRFTIME('%Y', order_date) AS INTEGER)          AS order_year,
    CAST(STRFTIME('%m', order_date) AS INTEGER)          AS order_month,
    ROUND(SUM(sales), 2)                                 AS sales,
    ROUND(SUM(profit), 2)                                AS profit,
    ROUND(SUM(profit) * 100.0 / SUM(sales), 2)           AS margin_pct,
    COUNT(DISTINCT order_id)                             AS orders,
    COUNT(DISTINCT customer_id)                          AS customers,
    SUM(quantity)                                        AS units,
    ROUND(AVG(discount) * 100, 2)                        AS avg_discount_pct,
    ROUND(SUM(sales) / COUNT(DISTINCT order_id), 2)      AS avg_order_value
FROM fact_sales
GROUP BY year_month;


-- ------------------------------------------------------------
-- 2. Customer 360 - lifetime behaviour joined to RFM segment.
-- ------------------------------------------------------------
DROP VIEW IF EXISTS vw_customer_360;
CREATE VIEW vw_customer_360 AS
SELECT
    c.customer_id,
    c.customer_name,
    c.segment,
    c.lifetime_orders,
    ROUND(c.lifetime_value, 2)                           AS lifetime_value,
    ROUND(c.lifetime_profit, 2)                          AS lifetime_profit,
    ROUND(c.avg_order_value, 2)                          AS avg_order_value,
    c.recency_days,
    c.rfm_score,
    c.rfm_segment,
    c.is_repeat,
    c.is_high_value,
    COUNT(DISTINCT f.product_id)                         AS distinct_products,
    COUNT(DISTINCT g.state)                              AS states_shipped_to,
    ROUND(AVG(f.discount) * 100, 2)                      AS avg_discount_pct
FROM dim_customer c
JOIN fact_sales   f ON c.customer_id = f.customer_id
JOIN dim_geography g ON f.geo_id     = g.geo_id
GROUP BY c.customer_id;


-- ------------------------------------------------------------
-- 3. Product performance - revenue, profit and discount depth.
--    The health_flag encodes the decision, not just the numbers.
-- ------------------------------------------------------------
DROP VIEW IF EXISTS vw_product_performance;
CREATE VIEW vw_product_performance AS
SELECT
    p.product_id,
    p.product_name,
    p.category,
    p.sub_category,
    ROUND(SUM(f.sales), 2)                               AS sales,
    ROUND(SUM(f.profit), 2)                              AS profit,
    ROUND(SUM(f.profit) * 100.0 / SUM(f.sales), 2)       AS margin_pct,
    SUM(f.quantity)                                      AS units,
    COUNT(DISTINCT f.order_id)                           AS orders,
    ROUND(AVG(f.discount) * 100, 2)                      AS avg_discount_pct,
    CASE
        WHEN SUM(f.profit) < 0                     THEN 'Loss making'
        WHEN SUM(f.profit) * 100.0 / SUM(f.sales) < 5  THEN 'Thin margin'
        WHEN SUM(f.profit) * 100.0 / SUM(f.sales) < 20 THEN 'Healthy'
        ELSE 'Strong'
    END                                                  AS health_flag
FROM fact_sales f
JOIN dim_product p ON f.product_id = p.product_id
GROUP BY p.product_id;


-- ------------------------------------------------------------
-- 4. Regional summary - region, state and city in one place.
-- ------------------------------------------------------------
DROP VIEW IF EXISTS vw_regional_summary;
CREATE VIEW vw_regional_summary AS
SELECT
    g.region,
    g.state,
    g.city,
    ROUND(SUM(f.sales), 2)                               AS sales,
    ROUND(SUM(f.profit), 2)                              AS profit,
    ROUND(SUM(f.profit) * 100.0 / SUM(f.sales), 2)       AS margin_pct,
    COUNT(DISTINCT f.order_id)                           AS orders,
    COUNT(DISTINCT f.customer_id)                        AS customers,
    ROUND(AVG(f.discount) * 100, 2)                      AS avg_discount_pct
FROM fact_sales f
JOIN dim_geography g ON f.geo_id = g.geo_id
GROUP BY g.region, g.state, g.city;


-- ------------------------------------------------------------
-- 5. Discount analysis - the view behind the headline finding.
-- ------------------------------------------------------------
DROP VIEW IF EXISTS vw_discount_analysis;
CREATE VIEW vw_discount_analysis AS
SELECT
    f.discount_band,
    p.category,
    COUNT(*)                                             AS order_lines,
    ROUND(SUM(f.sales), 2)                               AS sales,
    ROUND(SUM(f.profit), 2)                              AS profit,
    ROUND(SUM(f.profit) * 100.0 / SUM(f.sales), 2)       AS margin_pct,
    SUM(f.is_loss)                                       AS loss_making_lines
FROM fact_sales f
JOIN dim_product p ON f.product_id = p.product_id
GROUP BY f.discount_band, p.category;
