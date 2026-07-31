"""
feature_engineering.py
----------------------
Turns cleaned transactions into the modelling-ready processed layer.

Run:  python src/feature_engineering.py

Input : data/cleaned/superstore_clean.csv
Output: data/processed/superstore_features.csv
        data/processed/customer_profile.csv
        outputs/feature_dictionary.md

Three groups of features are added:
  Time      - year, quarter, month, weekend flag, order processing month
  Value     - profit margin, unit price, sales category, loss flag, discount band
  Customer  - lifetime orders, lifetime value, avg discount, high-value flag, RFM
"""

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "cleaned" / "superstore_clean.csv"
PROC = ROOT / "data" / "processed" / "superstore_features.csv"
CUST = ROOT / "data" / "processed" / "customer_profile.csv"
DICT = ROOT / "outputs" / "feature_dictionary.md"


# ------------------------------------------------------------------ time
def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    d = df["order_date"]
    df["order_year"] = d.dt.year
    df["order_month"] = d.dt.month
    df["order_month_name"] = d.dt.strftime("%b")
    df["order_quarter"] = "Q" + d.dt.quarter.astype(str)
    df["order_quarter_num"] = d.dt.quarter
    df["year_month"] = d.dt.to_period("M").astype(str)
    df["year_quarter"] = df["order_year"].astype(str) + "-" + df["order_quarter"]
    df["order_day_name"] = d.dt.day_name()
    df["order_week"] = d.dt.isocalendar().week.astype(int)

    # Weekend orders behave differently from weekday B2B purchasing.
    df["is_weekend_order"] = d.dt.dayofweek.isin([5, 6])

    # "Order processing month" = the month the order actually shipped in.
    # An order placed 30 Nov and shipped 3 Dec belongs to December operationally.
    df["processing_month"] = df["ship_date"].dt.strftime("%b")
    df["shipping_days"] = (df["ship_date"] - d).dt.days
    df["is_delayed"] = df["shipping_days"] > 5          # 5 days = internal SLA
    return df


# ----------------------------------------------------------------- value
def add_value_features(df: pd.DataFrame) -> pd.DataFrame:
    # Guard both denominators: a zero would raise or produce inf.
    df["profit_margin"] = df["profit"] / df["sales"].where(df["sales"] != 0) * 100
    df["unit_price"] = df["sales"] / df["quantity"].where(df["quantity"] != 0)
    df["is_loss"] = df["profit"] < 0
    df["is_discounted"] = df["discount"] > 0

    # Revenue lost to discounting on each line, versus the undiscounted price.
    df["discount_value"] = np.where(
        df["discount"] < 1,
        df["sales"] / (1 - df["discount"]) - df["sales"],
        0.0)

    df["discount_band"] = pd.cut(
        df["discount"], bins=[-0.01, 0.0, 0.15, 0.30, 0.50, 1.0],
        labels=["No discount", "1-15%", "16-30%", "31-50%", "50%+"])

    # Transaction size bands, cut on quartiles so they adapt to any extract.
    q = df["sales"].quantile([0.25, 0.50, 0.75]).tolist()
    df["sales_category"] = pd.cut(
        df["sales"], bins=[-0.01] + q + [df["sales"].max()],
        labels=["Small", "Medium", "Large", "Very Large"])

    df["margin_band"] = pd.cut(
        df["profit_margin"], bins=[-np.inf, 0, 10, 25, np.inf],
        labels=["Loss", "Low (0-10%)", "Healthy (10-25%)", "Strong (25%+)"])
    return df


# -------------------------------------------------------------- customer
def build_customer_profile(df: pd.DataFrame) -> pd.DataFrame:
    """One row per customer: lifetime behaviour plus RFM scores."""
    snapshot = df["order_date"].max() + pd.Timedelta(days=1)

    prof = df.groupby(["customer_id", "customer_name", "segment"]).agg(
        lifetime_orders=("order_id", "nunique"),
        lifetime_value=("sales", "sum"),
        lifetime_profit=("profit", "sum"),
        lifetime_units=("quantity", "sum"),
        avg_discount=("discount", "mean"),
        first_order=("order_date", "min"),
        last_order=("order_date", "max"),
        distinct_products=("product_id", "nunique"),
    ).reset_index()

    prof["avg_order_value"] = prof.lifetime_value / prof.lifetime_orders
    prof["profit_margin"] = prof.lifetime_profit / prof.lifetime_value * 100
    prof["tenure_days"] = (prof.last_order - prof.first_order).dt.days
    prof["recency_days"] = (snapshot - prof.last_order).dt.days
    prof["is_repeat"] = prof.lifetime_orders > 1

    # High value = top quintile of lifetime spend. A relative cut, not a magic number,
    # so the flag stays meaningful if the business grows.
    threshold = prof.lifetime_value.quantile(0.80)
    prof["is_high_value"] = prof.lifetime_value >= threshold

    # RFM: 5 = best. Recency is reversed because fewer days since last order is better.
    prof["r_score"] = pd.qcut(prof.recency_days, 5, labels=[5, 4, 3, 2, 1]).astype(int)
    prof["f_score"] = pd.qcut(prof.lifetime_orders.rank(method="first"), 5,
                              labels=[1, 2, 3, 4, 5]).astype(int)
    prof["m_score"] = pd.qcut(prof.lifetime_value, 5, labels=[1, 2, 3, 4, 5]).astype(int)
    prof["rfm_score"] = prof.r_score + prof.f_score + prof.m_score

    prof["rfm_segment"] = np.select(
        [prof.rfm_score >= 13, prof.rfm_score >= 10, prof.rfm_score >= 7],
        ["Champion", "Loyal", "Potential"], default="At Risk")

    return prof.sort_values("lifetime_value", ascending=False)


def attach_customer_features(df: pd.DataFrame, prof: pd.DataFrame) -> pd.DataFrame:
    cols = ["customer_id", "lifetime_orders", "lifetime_value",
            "is_high_value", "is_repeat", "rfm_segment"]
    return df.merge(prof[cols], on="customer_id", how="left")


# ----------------------------------------------------------------- write
def write_dictionary(df: pd.DataFrame, prof: pd.DataFrame) -> None:
    engineered = {
        "order_year / order_month / order_quarter": "Calendar parts of the order date",
        "year_month / year_quarter": "Period keys for trend charts",
        "order_day_name / order_week": "Weekday and ISO week number",
        "is_weekend_order": "True if placed Saturday or Sunday",
        "processing_month": "Month the order shipped, for operational reporting",
        "shipping_days": "Ship date minus order date",
        "is_delayed": "True if shipping_days > 5 (internal SLA)",
        "profit_margin": "profit / sales * 100, guarded against zero sales",
        "unit_price": "sales / quantity",
        "is_loss": "True if the line lost money",
        "is_discounted": "True if any discount was applied",
        "discount_value": "Revenue given away versus list price",
        "discount_band": "No discount / 1-15% / 16-30% / 31-50% / 50%+",
        "sales_category": "Small / Medium / Large / Very Large, cut on quartiles",
        "margin_band": "Loss / Low / Healthy / Strong",
        "lifetime_orders": "Distinct orders placed by that customer",
        "lifetime_value": "Total revenue from that customer",
        "is_high_value": "True if in the top 20% of lifetime spend",
        "is_repeat": "True if more than one order",
        "rfm_segment": "Champion / Loyal / Potential / At Risk",
    }
    lines = ["# Feature Dictionary", "",
             f"Transaction table: **{len(df):,} rows x {df.shape[1]} columns** "
             f"({len(engineered)} engineered).", "",
             "| Feature | Definition |", "|---|---|"]
    lines += [f"| `{k}` | {v} |" for k, v in engineered.items()]
    lines += ["", "## Customer profile", "",
              f"One row per customer: **{len(prof):,} rows x {prof.shape[1]} columns**.", "",
              "RFM scores run 1-5 (5 best). Recency is reversed, since a smaller number of",
              "days since the last order is better. `rfm_score` is the sum, so 3-15.", "",
              "| Segment | Rule |", "|---|---|",
              "| Champion | rfm_score >= 13 |", "| Loyal | rfm_score 10-12 |",
              "| Potential | rfm_score 7-9 |", "| At Risk | rfm_score <= 6 |"]
    DICT.parent.mkdir(parents=True, exist_ok=True)
    DICT.write_text("\n".join(lines))


def main() -> None:
    df = pd.read_csv(CLEAN, parse_dates=["order_date", "ship_date"],
                     dtype={"postal_code": str})
    before = df.shape[1]

    df = add_time_features(df)
    df = add_value_features(df)
    prof = build_customer_profile(df)
    df = attach_customer_features(df, prof)

    PROC.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROC, index=False)
    prof.to_csv(CUST, index=False)
    write_dictionary(df, prof)

    print(f"  Columns {before} -> {df.shape[1]} ({df.shape[1]-before} engineered)")
    print(f"  Transactions      : {len(df):,}")
    print(f"  Customer profiles : {len(prof):,}")
    print(f"  High-value custs  : {int(prof.is_high_value.sum()):,} "
          f"({prof.is_high_value.mean()*100:.0f}%), "
          f"{prof[prof.is_high_value].lifetime_value.sum()/prof.lifetime_value.sum()*100:.1f}% of revenue")
    print("  RFM segments      : " +
          ", ".join(f"{k} {v}" for k, v in prof.rfm_segment.value_counts().items()))
    print(f"\nSaved -> {PROC.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
