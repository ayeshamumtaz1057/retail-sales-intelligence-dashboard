-- ============================================================
--  Retail Sales Intelligence  |  analysis_queries.sql
--  Each block answers one business question and backs one
--  dashboard visual. Run against data/cleaned/superstore.db.
--
--  The "-- @name:" markers let src/run_sql_analysis.py execute
--  every query and export each result to outputs/sql/.
-- ============================================================


-- @name: 01_executive_kpis
-- Q: What are the headline numbers for the business?
-- Orders must be counted DISTINCT: the fact grain is order-line, not order.
SELECT
    ROUND(SUM(sales), 2)                                   AS total_sales,
    ROUND(SUM(profit), 2)                                  AS total_profit,
    ROUND(SUM(profit) * 100.0 / SUM(sales), 2)             AS profit_margin_pct,
    COUNT(DISTINCT order_id)                               AS total_orders,
    COUNT(DISTINCT customer_id)                            AS total_customers,
    SUM(quantity)                                          AS units_sold,
    ROUND(SUM(sales) / COUNT(DISTINCT order_id), 2)        AS avg_order_value
FROM fact_sales;


-- @name: 02_monthly_revenue
-- Q: How does revenue move month to month?
-- Backs the "Sales Over Time" line chart.
SELECT
    STRFTIME('%Y-%m', order_date)                          AS year_month,
    ROUND(SUM(sales), 2)                                   AS sales,
    ROUND(SUM(profit), 2)                                  AS profit,
    COUNT(DISTINCT order_id)                               AS orders
FROM fact_sales
GROUP BY year_month
ORDER BY year_month;


-- @name: 03_yearly_growth
-- Q: Are we growing, and by how much each year?
-- LAG() reaches back one row to compute year-over-year change without a self-join.
WITH yearly AS (
    SELECT
        CAST(STRFTIME('%Y', order_date) AS INTEGER)        AS order_year,
        SUM(sales)                                         AS sales,
        SUM(profit)                                        AS profit,
        COUNT(DISTINCT order_id)                           AS orders
    FROM fact_sales
    GROUP BY order_year
)
SELECT
    order_year,
    ROUND(sales, 2)                                        AS sales,
    ROUND(profit, 2)                                       AS profit,
    ROUND(LAG(sales) OVER (ORDER BY order_year), 2)        AS prev_year_sales,
    ROUND((sales - LAG(sales) OVER (ORDER BY order_year))
          * 100.0 / LAG(sales) OVER (ORDER BY order_year), 2) AS yoy_growth_pct,
    orders
FROM yearly
ORDER BY order_year;


-- @name: 04_top_10_products_by_sales
-- Q: Which products bring in the most revenue - and do they actually earn?
-- A high-revenue product with a thin margin is a different decision than a high-margin one.
SELECT
    p.product_name,
    p.category,
    p.sub_category,
    ROUND(SUM(f.sales), 2)                                 AS sales,
    ROUND(SUM(f.profit), 2)                                AS profit,
    ROUND(SUM(f.profit) * 100.0 / SUM(f.sales), 2)         AS margin_pct,
    SUM(f.quantity)                                        AS units
FROM fact_sales f
JOIN dim_product p ON f.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.category, p.sub_category
ORDER BY sales DESC
LIMIT 10;


-- @name: 05_worst_products_by_profit
-- Q: Which products lose the most money?
-- These are candidates to reprice, renegotiate, or discontinue.
SELECT
    p.product_name,
    p.sub_category,
    ROUND(SUM(f.sales), 2)                                 AS sales,
    ROUND(SUM(f.profit), 2)                                AS profit,
    ROUND(AVG(f.discount) * 100, 1)                        AS avg_discount_pct
FROM fact_sales f
JOIN dim_product p ON f.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.sub_category
HAVING SUM(f.profit) < 0
ORDER BY profit ASC
LIMIT 10;


-- @name: 06_category_performance
-- Q: How does each category contribute to revenue and profit?
-- The window function gives each category's share of the total in one pass.
SELECT
    p.category,
    ROUND(SUM(f.sales), 2)                                 AS sales,
    ROUND(SUM(f.sales) * 100.0 / SUM(SUM(f.sales)) OVER (), 2) AS pct_of_sales,
    ROUND(SUM(f.profit), 2)                                AS profit,
    ROUND(SUM(f.profit) * 100.0 / SUM(f.sales), 2)         AS margin_pct,
    COUNT(DISTINCT f.order_id)                             AS orders
FROM fact_sales f
JOIN dim_product p ON f.product_id = p.product_id
GROUP BY p.category
ORDER BY sales DESC;


-- @name: 07_subcategory_performance
-- Q: Which sub-categories earn, and which quietly bleed?
SELECT
    p.category,
    p.sub_category,
    ROUND(SUM(f.sales), 2)                                 AS sales,
    ROUND(SUM(f.profit), 2)                                AS profit,
    ROUND(SUM(f.profit) * 100.0 / SUM(f.sales), 2)         AS margin_pct,
    ROUND(AVG(f.discount) * 100, 1)                        AS avg_discount_pct
FROM fact_sales f
JOIN dim_product p ON f.product_id = p.product_id
GROUP BY p.category, p.sub_category
ORDER BY profit ASC;


-- @name: 08_top_customers
-- Q: Who are our most valuable customers?
-- RANK() labels the leaderboard position directly in the result set.
SELECT
    RANK() OVER (ORDER BY SUM(f.sales) DESC)               AS rank,
    c.customer_name,
    c.segment,
    ROUND(SUM(f.sales), 2)                                 AS sales,
    ROUND(SUM(f.profit), 2)                                AS profit,
    COUNT(DISTINCT f.order_id)                             AS orders,
    ROUND(SUM(f.sales) / COUNT(DISTINCT f.order_id), 2)    AS avg_order_value
FROM fact_sales f
JOIN dim_customer c ON f.customer_id = c.customer_id
GROUP BY c.customer_id, c.customer_name, c.segment
ORDER BY sales DESC
LIMIT 10;


-- @name: 09_customer_segments
-- Q: How do the three segments compare?
SELECT
    c.segment,
    COUNT(DISTINCT c.customer_id)                          AS customers,
    COUNT(DISTINCT f.order_id)                             AS orders,
    ROUND(SUM(f.sales), 2)                                 AS sales,
    ROUND(SUM(f.sales) * 100.0 / SUM(SUM(f.sales)) OVER (), 2) AS pct_of_sales,
    ROUND(SUM(f.profit), 2)                                AS profit,
    ROUND(SUM(f.sales) / COUNT(DISTINCT f.order_id), 2)    AS avg_order_value
FROM fact_sales f
JOIN dim_customer c ON f.customer_id = c.customer_id
GROUP BY c.segment
ORDER BY sales DESC;


-- @name: 10_repeat_customers
-- Q: How much of the business is repeat purchasing?
-- Retention is cheaper than acquisition, so this ratio drives marketing spend.
WITH per_customer AS (
    SELECT customer_id,
           COUNT(DISTINCT order_id) AS orders,
           SUM(sales)               AS sales
    FROM fact_sales
    GROUP BY customer_id
)
SELECT
    CASE WHEN orders = 1 THEN 'One-time' ELSE 'Repeat' END AS customer_type,
    COUNT(*)                                               AS customers,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2)     AS pct_of_customers,
    ROUND(SUM(sales), 2)                                   AS sales,
    ROUND(SUM(sales) * 100.0 / SUM(SUM(sales)) OVER (), 2) AS pct_of_sales,
    ROUND(AVG(orders), 2)                                  AS avg_orders
FROM per_customer
GROUP BY customer_type
ORDER BY sales DESC;


-- @name: 11_region_performance
-- Q: How does each region perform end to end?
-- Backs the "Region Wise Performance" table.
SELECT
    g.region,
    ROUND(SUM(f.sales), 2)                                 AS sales,
    ROUND(SUM(f.profit), 2)                                AS profit,
    COUNT(DISTINCT f.order_id)                             AS orders,
    COUNT(DISTINCT f.customer_id)                          AS customers,
    ROUND(SUM(f.profit) * 100.0 / SUM(f.sales), 2)         AS profit_margin_pct,
    ROUND(AVG(f.discount) * 100, 1)                        AS avg_discount_pct
FROM fact_sales f
JOIN dim_geography g ON f.geo_id = g.geo_id
GROUP BY g.region
ORDER BY sales DESC;


-- @name: 12_state_performance
-- Q: Which states drive sales, and which are unprofitable?
-- Backs the choropleth map.
SELECT
    g.state,
    g.region,
    ROUND(SUM(f.sales), 2)                                 AS sales,
    ROUND(SUM(f.profit), 2)                                AS profit,
    ROUND(SUM(f.profit) * 100.0 / SUM(f.sales), 2)         AS margin_pct,
    COUNT(DISTINCT f.order_id)                             AS orders
FROM fact_sales f
JOIN dim_geography g ON f.geo_id = g.geo_id
GROUP BY g.state, g.region
ORDER BY sales DESC;


-- @name: 13_daily_sales_pattern
-- Q: Which days of the week sell best? Informs staffing and campaign timing.
-- SQLite returns weekday as 0=Sunday; CASE maps it to a readable label.
SELECT
    CASE CAST(STRFTIME('%w', order_date) AS INTEGER)
        WHEN 0 THEN 'Sunday'    WHEN 1 THEN 'Monday'  WHEN 2 THEN 'Tuesday'
        WHEN 3 THEN 'Wednesday' WHEN 4 THEN 'Thursday' WHEN 5 THEN 'Friday'
        ELSE 'Saturday' END                                AS day_of_week,
    COUNT(DISTINCT order_id)                               AS orders,
    ROUND(SUM(sales), 2)                                   AS sales,
    ROUND(AVG(sales), 2)                                   AS avg_line_value
FROM fact_sales
GROUP BY day_of_week
ORDER BY sales DESC;


-- @name: 14_discount_impact
-- Q: At what discount level does an order stop being profitable?
-- The single most actionable query here: it prices the discount policy.
SELECT
    CASE
        WHEN discount = 0            THEN 'No discount'
        WHEN discount <= 0.15        THEN '1-15%'
        WHEN discount <= 0.30        THEN '16-30%'
        WHEN discount <= 0.50        THEN '31-50%'
        ELSE '50%+'
    END                                                    AS discount_band,
    COUNT(*)                                               AS order_lines,
    ROUND(SUM(sales), 2)                                   AS sales,
    ROUND(SUM(profit), 2)                                  AS profit,
    ROUND(SUM(profit) * 100.0 / SUM(sales), 2)             AS margin_pct
FROM fact_sales
GROUP BY discount_band
ORDER BY margin_pct DESC;


-- @name: 15_monthly_running_total
-- Q: How does cumulative revenue build across each year?
-- A running SUM over an ordered window - the standard "revenue to date" pattern.
SELECT
    STRFTIME('%Y', order_date)                             AS order_year,
    STRFTIME('%Y-%m', order_date)                          AS year_month,
    ROUND(SUM(sales), 2)                                   AS monthly_sales,
    ROUND(SUM(SUM(sales)) OVER (
        PARTITION BY STRFTIME('%Y', order_date)
        ORDER BY STRFTIME('%Y-%m', order_date)
    ), 2)                                                  AS running_total_ytd
FROM fact_sales
GROUP BY order_year, year_month
ORDER BY year_month;


-- ============================================================
--  PART 2  |  Queries 16-30
--  Requires sql/views.sql to have been applied.
-- ============================================================


-- @name: 16_top_products_by_profit
-- Q: Which products actually earn the most, as opposed to selling the most?
-- Revenue leaders and profit leaders are different lists - that is the point.
SELECT product_name, category, sub_category, sales, profit, margin_pct, units
FROM vw_product_performance
ORDER BY profit DESC
LIMIT 10;


-- @name: 17_bottom_products_by_sales
-- Q: Which stocked products barely sell? Candidates for delisting.
SELECT product_name, sub_category, sales, profit, orders
FROM vw_product_performance
WHERE orders >= 2                 -- ignore one-off purchases
ORDER BY sales ASC
LIMIT 10;


-- @name: 18_high_sales_low_profit
-- Q: Which products sell well but earn nothing? The CEO's exact question.
-- Above-median revenue, bottom-quartile margin.
WITH stats AS (
    SELECT
        (SELECT AVG(sales) FROM vw_product_performance)          AS avg_sales,
        (SELECT AVG(margin_pct) FROM vw_product_performance)     AS avg_margin
)
SELECT
    v.product_name, v.category, v.sales, v.profit,
    v.margin_pct, v.avg_discount_pct, v.health_flag
FROM vw_product_performance v, stats s
WHERE v.sales > s.avg_sales * 3
  AND v.margin_pct < 5
ORDER BY v.sales DESC
LIMIT 15;


-- @name: 19_quarterly_growth
-- Q: How does each quarter compare with the one before it?
WITH quarterly AS (
    SELECT
        STRFTIME('%Y', order_date) || '-Q' ||
            CAST((CAST(STRFTIME('%m', order_date) AS INTEGER) + 2) / 3 AS TEXT) AS quarter,
        SUM(sales)  AS sales,
        SUM(profit) AS profit
    FROM fact_sales
    GROUP BY quarter
)
SELECT
    quarter,
    ROUND(sales, 2)                                              AS sales,
    ROUND(profit, 2)                                             AS profit,
    ROUND(LAG(sales) OVER (ORDER BY quarter), 2)                 AS prev_quarter,
    ROUND((sales - LAG(sales) OVER (ORDER BY quarter)) * 100.0
          / LAG(sales) OVER (ORDER BY quarter), 2)               AS qoq_growth_pct
FROM quarterly
ORDER BY quarter;


-- @name: 20_rolling_3month_sales
-- Q: What does the trend look like once monthly noise is smoothed out?
-- A 3-month moving average over a framed window.
SELECT
    year_month,
    sales,
    ROUND(AVG(sales) OVER (
        ORDER BY year_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 2)                                                        AS rolling_3m_avg,
    ROUND(AVG(sales) OVER (
        ORDER BY year_month ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
    ), 2)                                                        AS rolling_6m_avg
FROM vw_monthly_summary
ORDER BY year_month;


-- @name: 21_customer_lifetime_value
-- Q: What is each customer worth, and how are they ranked?
-- DENSE_RANK gives ties the same rank with no gaps afterwards.
SELECT
    DENSE_RANK() OVER (ORDER BY lifetime_value DESC)             AS clv_rank,
    customer_name, segment, lifetime_orders, lifetime_value,
    lifetime_profit, avg_order_value, rfm_segment
FROM vw_customer_360
ORDER BY lifetime_value DESC
LIMIT 20;


-- @name: 22_rfm_segments
-- Q: How is the customer base distributed across RFM segments?
SELECT
    rfm_segment,
    COUNT(*)                                                     AS customers,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2)           AS pct_customers,
    ROUND(SUM(lifetime_value), 2)                                AS revenue,
    ROUND(SUM(lifetime_value) * 100.0 / SUM(SUM(lifetime_value)) OVER (), 2)
                                                                 AS pct_revenue,
    ROUND(AVG(lifetime_orders), 1)                               AS avg_orders,
    ROUND(AVG(recency_days), 0)                                  AS avg_recency_days
FROM vw_customer_360
GROUP BY rfm_segment
ORDER BY revenue DESC;


-- @name: 23_high_value_customers
-- Q: How much of the business rests on the top 20% of customers?
SELECT
    CASE WHEN is_high_value = 1 THEN 'High value (top 20%)'
         ELSE 'Standard' END                                     AS tier,
    COUNT(*)                                                     AS customers,
    ROUND(SUM(lifetime_value), 2)                                AS revenue,
    ROUND(SUM(lifetime_value) * 100.0 / SUM(SUM(lifetime_value)) OVER (), 2)
                                                                 AS pct_revenue,
    ROUND(AVG(avg_order_value), 2)                               AS avg_order_value,
    ROUND(AVG(lifetime_orders), 1)                               AS avg_orders
FROM vw_customer_360
GROUP BY is_high_value
ORDER BY revenue DESC;


-- @name: 24_top_cities_by_revenue
-- Q: Which cities generate the most revenue?
SELECT
    city, state, region,
    ROUND(SUM(sales), 2)                                         AS sales,
    ROUND(SUM(profit), 2)                                        AS profit,
    ROUND(SUM(profit) * 100.0 / SUM(sales), 2)                   AS margin_pct,
    SUM(orders)                                                  AS orders
FROM vw_regional_summary
GROUP BY city, state, region
ORDER BY sales DESC
LIMIT 15;


-- @name: 25_underperforming_states
-- Q: Which states consistently lose money?
-- HAVING filters on the aggregate, which WHERE cannot do.
SELECT
    state, region,
    ROUND(SUM(sales), 2)                                         AS sales,
    ROUND(SUM(profit), 2)                                        AS profit,
    ROUND(SUM(profit) * 100.0 / SUM(sales), 2)                   AS margin_pct,
    ROUND(AVG(avg_discount_pct), 1)                              AS avg_discount_pct
FROM vw_regional_summary
GROUP BY state, region
HAVING SUM(profit) < 0
ORDER BY profit ASC;


-- @name: 26_shipping_mode_analysis
-- Q: Which shipping mode is most profitable, and what does speed cost?
SELECT
    ship_mode,
    COUNT(DISTINCT order_id)                                     AS orders,
    ROUND(AVG(shipping_days), 1)                                 AS avg_days,
    ROUND(SUM(sales), 2)                                         AS sales,
    ROUND(SUM(profit), 2)                                        AS profit,
    ROUND(SUM(profit) * 100.0 / SUM(sales), 2)                   AS margin_pct,
    ROUND(SUM(is_delayed) * 100.0 / COUNT(*), 1)                 AS pct_beyond_sla
FROM fact_sales
GROUP BY ship_mode
ORDER BY margin_pct DESC;


-- @name: 27_highest_discount_orders
-- Q: Which individual orders were discounted hardest, and what did they cost us?
SELECT
    f.order_id,
    f.order_date,
    c.customer_name,
    p.product_name,
    ROUND(f.discount * 100, 0)                                   AS discount_pct,
    ROUND(f.sales, 2)                                            AS sales,
    ROUND(f.profit, 2)                                           AS profit
FROM fact_sales f
JOIN dim_customer c ON f.customer_id = c.customer_id
JOIN dim_product  p ON f.product_id  = p.product_id
ORDER BY f.discount DESC, f.profit ASC
LIMIT 15;


-- @name: 28_segment_category_matrix
-- Q: Which segment buys which category, and at what margin?
-- A cross-tab built with conditional aggregation.
SELECT
    c.segment,
    ROUND(SUM(CASE WHEN p.category = 'Technology'      THEN f.sales ELSE 0 END), 2) AS technology,
    ROUND(SUM(CASE WHEN p.category = 'Furniture'       THEN f.sales ELSE 0 END), 2) AS furniture,
    ROUND(SUM(CASE WHEN p.category = 'Office Supplies' THEN f.sales ELSE 0 END), 2) AS office_supplies,
    ROUND(SUM(f.sales), 2)                                       AS total_sales,
    ROUND(SUM(f.profit) * 100.0 / SUM(f.sales), 2)               AS margin_pct
FROM fact_sales f
JOIN dim_customer c ON f.customer_id = c.customer_id
JOIN dim_product  p ON f.product_id  = p.product_id
GROUP BY c.segment
ORDER BY total_sales DESC;


-- @name: 29_weekend_vs_weekday
-- Q: Do weekend orders behave differently from weekday orders?
SELECT
    CASE WHEN is_weekend_order = 1 THEN 'Weekend' ELSE 'Weekday' END AS day_type,
    COUNT(DISTINCT order_id)                                     AS orders,
    ROUND(SUM(sales), 2)                                         AS sales,
    ROUND(SUM(sales) / COUNT(DISTINCT order_id), 2)              AS avg_order_value,
    ROUND(SUM(profit) * 100.0 / SUM(sales), 2)                   AS margin_pct,
    ROUND(AVG(discount) * 100, 1)                                AS avg_discount_pct
FROM fact_sales
GROUP BY is_weekend_order;


-- @name: 30_product_rank_within_category
-- Q: What is each product's rank inside its own category?
-- PARTITION BY restarts the ranking for every category.
WITH ranked AS (
    SELECT
        p.category,
        p.product_name,
        SUM(f.sales)                                             AS sales,
        SUM(f.profit)                                            AS profit,
        RANK() OVER (PARTITION BY p.category ORDER BY SUM(f.sales) DESC) AS sales_rank,
        RANK() OVER (PARTITION BY p.category ORDER BY SUM(f.profit) DESC) AS profit_rank
    FROM fact_sales f
    JOIN dim_product p ON f.product_id = p.product_id
    GROUP BY p.category, p.product_name
)
SELECT
    category, product_name,
    ROUND(sales, 2)  AS sales,
    ROUND(profit, 2) AS profit,
    sales_rank,
    profit_rank,
    -- A large positive gap means the product sells far better than it earns.
    profit_rank - sales_rank AS rank_gap
FROM ranked
WHERE sales_rank <= 5
ORDER BY category, sales_rank;
