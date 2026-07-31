"""
build_database.py
-----------------
Loads the processed feature table into the SQLite star schema.

Run:  python src/build_database.py   (run feature_engineering.py first)

Input : data/processed/superstore_features.csv, sql/schema.sql
Output: data/processed/superstore.db
"""

from pathlib import Path
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed" / "superstore_features.csv"
CUST = ROOT / "data" / "processed" / "customer_profile.csv"
SCHEMA = ROOT / "sql" / "schema.sql"
VIEWS = ROOT / "sql" / "views.sql"
DB = ROOT / "data" / "processed" / "superstore.db"


def build_dimensions(df: pd.DataFrame):
    """One row per business entity. Duplicate keys are collapsed on first sighting."""
    prof = pd.read_csv(CUST)
    customer = prof[["customer_id", "customer_name", "segment", "lifetime_orders",
                     "lifetime_value", "lifetime_profit", "avg_order_value",
                     "recency_days", "is_repeat", "is_high_value",
                     "rfm_score", "rfm_segment"]].copy()
    for col in ["is_repeat", "is_high_value"]:
        customer[col] = customer[col].astype(int)

    # Superstore reuses a product_id for slightly different product names.
    # Keeping the first name per id preserves referential integrity.
    product = (df[["product_id", "product_name", "category", "sub_category"]]
               .drop_duplicates("product_id").reset_index(drop=True))

    geo = (df[["country", "region", "state", "city", "postal_code"]]
           .drop_duplicates().reset_index(drop=True))
    geo.insert(0, "geo_id", range(1, len(geo) + 1))

    return customer, product, geo


def build_fact(df: pd.DataFrame, geo: pd.DataFrame) -> pd.DataFrame:
    """Attach the surrogate geo_id, then keep only fact-grain columns."""
    keys = ["country", "region", "state", "city", "postal_code"]
    fact = df.merge(geo, on=keys, how="left")

    assert fact["geo_id"].notna().all(), "Geography join dropped rows - check keys"

    for col in ["is_weekend_order", "is_loss", "is_delayed"]:
        fact[col] = fact[col].fillna(False).astype(int)

    cols = ["row_id", "order_id", "order_date", "ship_date", "ship_mode",
            "customer_id", "product_id", "geo_id",
            "sales", "quantity", "discount", "profit", "shipping_days",
            "profit_margin", "discount_band", "sales_category",
            "is_weekend_order", "is_loss", "is_delayed"]
    return fact[cols]


def main() -> None:
    df = pd.read_csv(PROC, dtype={"postal_code": str})

    customer, product, geo = build_dimensions(df)
    fact = build_fact(df, geo)

    DB.unlink(missing_ok=True)
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA.read_text())          # tables, indexes, base view

    for name, frame in [("dim_customer", customer), ("dim_product", product),
                        ("dim_geography", geo), ("fact_sales", fact)]:
        frame.to_sql(name, con, if_exists="append", index=False)
        print(f"  {name:<15} {len(frame):>6,} rows")

    con.executescript(VIEWS.read_text())           # analytical views
    views = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")]
    print(f"  views created   {len(views):>6}  ({', '.join(views)})")

    # Foreign keys are declared but not enforced by default in SQLite - verify.
    orphans = con.execute("""
        SELECT COUNT(*) FROM fact_sales f
        LEFT JOIN dim_customer c ON f.customer_id = c.customer_id
        WHERE c.customer_id IS NULL
    """).fetchone()[0]

    sales, profit, orders = con.execute("""
        SELECT ROUND(SUM(sales),2), ROUND(SUM(profit),2), COUNT(DISTINCT order_id)
        FROM fact_sales
    """).fetchone()

    con.commit()
    con.close()

    print(f"\n  Orphaned fact rows : {orphans}")
    print(f"  Total sales        : ${sales:,.2f}")
    print(f"  Total profit       : ${profit:,.2f}")
    print(f"  Distinct orders    : {orders:,}")
    print(f"\nSaved -> {DB.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
