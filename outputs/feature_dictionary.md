# Feature Dictionary

Transaction table: **9,993 rows x 47 columns** (20 engineered).

| Feature | Definition |
|---|---|
| `order_year / order_month / order_quarter` | Calendar parts of the order date |
| `year_month / year_quarter` | Period keys for trend charts |
| `order_day_name / order_week` | Weekday and ISO week number |
| `is_weekend_order` | True if placed Saturday or Sunday |
| `processing_month` | Month the order shipped, for operational reporting |
| `shipping_days` | Ship date minus order date |
| `is_delayed` | True if shipping_days > 5 (internal SLA) |
| `profit_margin` | profit / sales * 100, guarded against zero sales |
| `unit_price` | sales / quantity |
| `is_loss` | True if the line lost money |
| `is_discounted` | True if any discount was applied |
| `discount_value` | Revenue given away versus list price |
| `discount_band` | No discount / 1-15% / 16-30% / 31-50% / 50%+ |
| `sales_category` | Small / Medium / Large / Very Large, cut on quartiles |
| `margin_band` | Loss / Low / Healthy / Strong |
| `lifetime_orders` | Distinct orders placed by that customer |
| `lifetime_value` | Total revenue from that customer |
| `is_high_value` | True if in the top 20% of lifetime spend |
| `is_repeat` | True if more than one order |
| `rfm_segment` | Champion / Loyal / Potential / At Risk |

## Customer profile

One row per customer: **793 rows x 22 columns**.

RFM scores run 1-5 (5 best). Recency is reversed, since a smaller number of
days since the last order is better. `rfm_score` is the sum, so 3-15.

| Segment | Rule |
|---|---|
| Champion | rfm_score >= 13 |
| Loyal | rfm_score 10-12 |
| Potential | rfm_score 7-9 |
| At Risk | rfm_score <= 6 |