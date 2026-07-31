"""
clean_data.py
-------------
Cleans the raw Superstore extract.

Cleaning only - feature engineering lives in src/feature_engineering.py so that the
two concerns stay separately testable.

Run:  python src/clean_data.py

Input : data/raw/superstore_raw.csv
Output: data/cleaned/superstore_clean.csv
        outputs/cleaning_report.txt
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "superstore_raw.csv"
CLEAN = ROOT / "data" / "cleaned" / "superstore_clean.csv"
REPORT = ROOT / "outputs" / "cleaning_report.txt"

# Columns that must be populated for a row to represent a real transaction.
CRITICAL = ["Order Date", "Customer ID", "Product ID", "Sales", "Quantity"]

MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def load_raw() -> pd.DataFrame:
    """Superstore ships as latin-1; utf-8 fails on customer names with accents."""
    return pd.read_csv(RAW, encoding="latin-1")


def clean(df: pd.DataFrame, log: list) -> pd.DataFrame:
    start = len(df)
    log.append(f"Rows loaded from raw extract           : {start:,}")

    # 1 ── Standardise column names to snake_case so SQL and pandas agree.
    df.columns = (df.columns.str.strip()
                            .str.lower()
                            .str.replace(r"[ \-]", "_", regex=True))

    # 2 ── Drop shell rows: an order id was written but no transaction detail.
    #      These are not "missing values to impute" - they carry zero information.
    shells = df[CRITICAL_SNAKE].isna().all(axis=1).sum()
    df = df.dropna(subset=CRITICAL_SNAKE, how="all")
    log.append(f"Removed empty shell rows               : {shells:,}")

    # Any row still missing a critical field is unusable for revenue analysis.
    residual = df[CRITICAL_SNAKE].isna().any(axis=1).sum()
    df = df.dropna(subset=CRITICAL_SNAKE)
    log.append(f"Removed rows missing critical fields   : {residual:,}")

    # 3 ── Exact duplicate transactions (same row repeated during extraction).
    dupes = df.duplicated(subset=[c for c in df.columns if c != "row_id"]).sum()
    df = df.drop_duplicates(subset=[c for c in df.columns if c != "row_id"])
    log.append(f"Removed duplicate transactions         : {dupes:,}")

    # 4 ── Types. Dates are mixed-format in the source, hence format='mixed'.
    for col in ["order_date", "ship_date"]:
        df[col] = pd.to_datetime(df[col], format="mixed", errors="coerce")
    for col in ["sales", "profit", "discount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").astype("Int64")

    # postal_code is an identifier, not a number - leading zeros matter (e.g. 01810).
    df["postal_code"] = (df["postal_code"].astype("Float64").astype("Int64")
                         .astype(str).str.zfill(5).replace("<NA>", None))

    # Impute any remaining gaps from the most common code for that city and state.
    missing_before = df["postal_code"].isna().sum()
    if missing_before:
        mode_by_city = (df.dropna(subset=["postal_code"])
                          .groupby(["state", "city"])["postal_code"]
                          .agg(lambda s: s.mode().iat[0]))
        keys = pd.MultiIndex.from_arrays([df["state"], df["city"]])
        df["postal_code"] = df["postal_code"].fillna(
            pd.Series(keys.map(mode_by_city), index=df.index))
    still_missing = df["postal_code"].isna().sum()
    log.append(f"Postal codes imputed from city/state    : "
               f"{missing_before - still_missing:,}")

    # Any that remain are cities the dataset never supplies a code for. They are
    # left null rather than filled from an external source: postal_code is not used
    # in any analysis (state is the geographic grain), and inventing values would
    # put unverifiable data into a file presented as cleaned.
    if still_missing:
        cities = df.loc[df["postal_code"].isna(), ["city", "state"]].drop_duplicates()
        log.append(f"Postal codes still missing             : {still_missing:,} "
                   f"({', '.join(cities.city + ', ' + cities.state)})")

    # 5 ── Trim stray whitespace in every text column.
    text_cols = [c for c in df.columns
                 if pd.api.types.is_string_dtype(df[c]) or df[c].dtype == "object"]
    for col in text_cols:
        df[col] = df[col].astype("string").str.strip()

    # 6 ── Integrity check: a ship date before the order date is a data error.
    bad_ship = (df["ship_date"] < df["order_date"]).sum()
    log.append(f"Ship date earlier than order date      : {bad_ship:,}")

    log.append(f"Rows remaining after cleaning          : {len(df):,}")
    log.append(f"Total rows dropped                     : {start - len(df):,}")
    return df.reset_index(drop=True)


def summarise(df: pd.DataFrame, log: list) -> None:
    orders = df["order_id"].nunique()
    log.append("")
    log.append("VALIDATED TOTALS")
    log.append(f"  Total sales      : ${df['sales'].sum():,.2f}")
    log.append(f"  Total profit     : ${df['profit'].sum():,.2f}")
    log.append(f"  Overall margin   : {df['profit'].sum()/df['sales'].sum()*100:.2f}%")
    log.append(f"  Orders           : {orders:,}")
    log.append(f"  Customers        : {df['customer_id'].nunique():,}")
    log.append(f"  Products         : {df['product_id'].nunique():,}")
    log.append(f"  Avg order value  : ${df['sales'].sum()/orders:,.2f}")
    log.append(f"  Date range       : {df['order_date'].min():%Y-%m-%d} to "
               f"{df['order_date'].max():%Y-%m-%d}")


CRITICAL_SNAKE = ["order_date", "customer_id", "product_id", "sales", "quantity"]

if __name__ == "__main__":
    log = ["SUPERSTORE CLEANING REPORT", "=" * 46, ""]
    df = clean(load_raw(), log)
    summarise(df, log)

    CLEAN.parent.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CLEAN, index=False)
    REPORT.write_text("\n".join(log))

    print("\n".join(log))
    print(f"\nSaved -> {CLEAN.relative_to(ROOT)}")
