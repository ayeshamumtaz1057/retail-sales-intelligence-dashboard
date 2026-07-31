-- ============================================================
--  Retail Sales Intelligence  |  schema.sql
--  Star schema: one fact table, three conformed dimensions.
--  Engine: SQLite (portable, zero-config). Notes mark the two
--  places you would change syntax for PostgreSQL / MySQL.
-- ============================================================

DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_geography;

-- ------------------------------------------------------------
-- DIMENSIONS
-- ------------------------------------------------------------

CREATE TABLE dim_customer (
    customer_id      TEXT PRIMARY KEY,
    customer_name    TEXT NOT NULL,
    segment          TEXT NOT NULL,   -- Consumer | Corporate | Home Office
    -- Lifetime attributes, precomputed by src/feature_engineering.py
    lifetime_orders  INTEGER,
    lifetime_value   REAL,
    lifetime_profit  REAL,
    avg_order_value  REAL,
    recency_days     INTEGER,
    is_repeat        INTEGER,         -- SQLite stores booleans as 0/1
    is_high_value    INTEGER,         -- top 20% of lifetime spend
    rfm_score        INTEGER,
    rfm_segment      TEXT             -- Champion | Loyal | Potential | At Risk
);

CREATE TABLE dim_product (
    product_id     TEXT PRIMARY KEY,
    product_name   TEXT NOT NULL,
    category       TEXT NOT NULL,     -- Technology | Furniture | Office Supplies
    sub_category   TEXT NOT NULL
);

CREATE TABLE dim_geography (
    geo_id         INTEGER PRIMARY KEY,
    country        TEXT NOT NULL,
    region         TEXT NOT NULL,     -- West | East | Central | South
    state          TEXT NOT NULL,
    city           TEXT NOT NULL,
    postal_code    TEXT
);

-- ------------------------------------------------------------
-- FACT
-- Grain: one row per product line on an order.
-- An order_id therefore repeats across rows - always use
-- COUNT(DISTINCT order_id) when counting orders.
-- ------------------------------------------------------------

CREATE TABLE fact_sales (
    row_id         INTEGER PRIMARY KEY,
    order_id       TEXT NOT NULL,
    order_date     DATE NOT NULL,
    ship_date      DATE,
    ship_mode      TEXT,
    customer_id    TEXT NOT NULL REFERENCES dim_customer(customer_id),
    product_id     TEXT NOT NULL REFERENCES dim_product(product_id),
    geo_id         INTEGER NOT NULL REFERENCES dim_geography(geo_id),
    sales          REAL NOT NULL CHECK (sales >= 0),
    quantity       INTEGER NOT NULL CHECK (quantity > 0),
    discount       REAL NOT NULL CHECK (discount BETWEEN 0 AND 1),
    profit         REAL NOT NULL,     -- may be negative: discounting causes real losses
    shipping_days  INTEGER,
    -- Engineered attributes, carried into the fact for filter performance
    profit_margin     REAL,
    discount_band     TEXT,           -- No discount | 1-15% | 16-30% | 31-50% | 50%+
    sales_category    TEXT,           -- Small | Medium | Large | Very Large
    is_weekend_order  INTEGER,
    is_loss           INTEGER,
    is_delayed        INTEGER
);

-- ------------------------------------------------------------
-- INDEXES
-- Every dashboard filter (date, region, category, segment) becomes
-- a WHERE clause, so each filtered column gets an index.
-- ------------------------------------------------------------

CREATE INDEX idx_fact_order_date  ON fact_sales(order_date);
CREATE INDEX idx_fact_customer    ON fact_sales(customer_id);
CREATE INDEX idx_fact_product     ON fact_sales(product_id);
CREATE INDEX idx_fact_geo         ON fact_sales(geo_id);
CREATE INDEX idx_fact_order_id    ON fact_sales(order_id);
CREATE INDEX idx_product_category ON dim_product(category, sub_category);
CREATE INDEX idx_geo_region       ON dim_geography(region, state);
CREATE INDEX idx_geo_city         ON dim_geography(city);
CREATE INDEX idx_fact_discount    ON fact_sales(discount_band);
CREATE INDEX idx_cust_rfm         ON dim_customer(rfm_segment);

-- ------------------------------------------------------------
-- VIEW: pre-joined flat table for ad-hoc querying and BI tools.
-- Power BI can import this directly instead of re-creating joins.
-- ------------------------------------------------------------

DROP VIEW IF EXISTS vw_sales_detail;
CREATE VIEW vw_sales_detail AS
SELECT
    f.row_id, f.order_id, f.order_date, f.ship_date, f.ship_mode, f.shipping_days,
    c.customer_id, c.customer_name, c.segment,
    p.product_id, p.product_name, p.category, p.sub_category,
    g.region, g.state, g.city, g.postal_code,
    c.lifetime_orders, c.is_high_value, c.rfm_segment,
    f.sales, f.quantity, f.discount, f.profit,
    f.discount_band, f.sales_category, f.is_weekend_order, f.is_loss,
    -- NULLIF guards the divide-by-zero on any zero-value line.
    ROUND(f.profit / NULLIF(f.sales, 0) * 100, 2) AS profit_margin_pct,
    CAST(STRFTIME('%Y', f.order_date) AS INTEGER)  AS order_year,   -- PG: EXTRACT(YEAR FROM ...)
    STRFTIME('%Y-%m', f.order_date)                AS year_month    -- PG: TO_CHAR(..., 'YYYY-MM')
FROM fact_sales f
JOIN dim_customer  c ON f.customer_id = c.customer_id
JOIN dim_product   p ON f.product_id  = p.product_id
JOIN dim_geography g ON f.geo_id      = g.geo_id;
