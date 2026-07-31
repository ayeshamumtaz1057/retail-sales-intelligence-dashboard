"""
make_notebooks.py
-----------------
Builds and executes the four analysis notebooks so the committed .ipynb files
carry their outputs (GitHub renders them without anyone running the code).

Run:  python src/make_notebooks.py

Output: notebooks/01_data_cleaning.ipynb
        notebooks/02_feature_engineering.ipynb
        notebooks/03_eda.ipynb
        notebooks/04_visualization.ipynb
        images/*.png
"""

from pathlib import Path
import nbformat as nbf
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
NBDIR = ROOT / "notebooks"

md = lambda s: nbf.v4.new_markdown_cell(s.strip())
code = lambda s: nbf.v4.new_code_cell(s.strip())

SETUP = """
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns

warnings.filterwarnings("ignore")
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()

BLUE, TEAL, AMBER, PURPLE, RED = "#2f6fed", "#16a888", "#f5b820", "#7b45c9", "#e03131"
sns.set_theme(style="whitegrid")
plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 140, "savefig.bbox": "tight",
    "font.size": 10, "axes.titlesize": 12, "axes.titleweight": "bold",
    "axes.edgecolor": "#d7dbe3", "grid.color": "#eef0f4", "axes.facecolor": "white",
})
IMAGES = ROOT / "images"; IMAGES.mkdir(exist_ok=True)
pd.set_option("display.float_format", lambda v: f"{v:,.2f}")
money = mticker.FuncFormatter(lambda v, _: f"${v/1000:,.0f}K")
"""


# ══════════════════════════════════════════════════ 01 DATA CLEANING
NB01 = [
md("""
# 01 · Data Cleaning

**Input:** `data/raw/superstore_raw.csv` (10,800 rows as received)
**Output:** `data/cleaned/superstore_clean.csv`

Profile the extract, decide what is wrong with it, and fix it — documenting every
decision. The reusable implementation is `src/clean_data.py`; this notebook shows
the reasoning behind it.
"""),
code(SETUP),
md("## 1. Load and inspect"),
code("""
# Superstore ships as latin-1. utf-8 fails on customer names with accented characters.
raw = pd.read_csv(ROOT / "data" / "raw" / "superstore_raw.csv", encoding="latin-1")
print(f"Shape: {raw.shape[0]:,} rows x {raw.shape[1]} columns")
raw.head(3)
"""),
md("## 2. Data profiling"),
code("""
profile = pd.DataFrame({
    "dtype": raw.dtypes.astype(str),
    "nulls": raw.isna().sum(),
    "null_%": (raw.isna().mean() * 100).round(2),
    "unique": raw.nunique(),
    "sample": [raw[c].dropna().iloc[0] if raw[c].notna().any() else "-" for c in raw.columns],
})
profile
"""),
md("""
### Reading the null pattern

19 columns each report exactly **806** nulls, and `Postal Code` reports 817. Identical
counts across unrelated columns is not scattered data entry error — it is whole records
arriving empty. Confirm before deciding what to do.
"""),
code("""
shells = raw[raw["Sales"].isna()]
print(f"Rows with no Sales value : {len(shells):,}")
print(f"Of those, Order ID present: {shells['Order ID'].notna().sum():,}")
print(f"Columns null in ALL shells: "
      f"{(shells.isna().all() | (shells.notna().sum() == 0)).sum()}")
shells.head(3)
"""),
md("""
**Confirmed.** These rows carry an Order ID and nothing else. They are not missing values
to impute — there is no transaction to reconstruct. They are dropped.

The 11 extra `Postal Code` nulls are a separate issue, examined in step 5.
"""),
code("""
print(f"Exact duplicate rows: {raw.duplicated().sum():,}")
print(f"All duplicates inside the shell rows: "
      f"{raw[raw.duplicated()]['Sales'].isna().all()}")
"""),
md("## 3. Cleaning"),
code("""
df = raw.copy()
df.columns = (df.columns.str.strip().str.lower()
                .str.replace(r"[ \\-]", "_", regex=True))

before = len(df)
critical = ["order_date", "customer_id", "product_id", "sales", "quantity"]

df = df.dropna(subset=critical, how="all")
print(f"After dropping shell rows : {len(df):,}  (-{before - len(df):,})")

n = len(df)
df = df.drop_duplicates(subset=[c for c in df.columns if c != "row_id"])
print(f"After dropping duplicates : {len(df):,}  (-{n - len(df):,})")
"""),
md("## 4. Type correction"),
code("""
# Dates arrive in mixed formats, so let pandas infer per value rather than forcing one.
for col in ["order_date", "ship_date"]:
    df[col] = pd.to_datetime(df[col], format="mixed", errors="coerce")

for col in ["sales", "profit", "discount"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")
df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").astype("Int64")

print(f"Unparsed dates: {df.order_date.isna().sum()}")
print(f"Date range    : {df.order_date.min():%Y-%m-%d} to {df.order_date.max():%Y-%m-%d}")
df[["order_date", "ship_date", "sales", "quantity", "discount", "profit"]].dtypes
"""),
md("""
### Postal codes are identifiers, not numbers

Read as integers, `01810` becomes `1810`. Cast to text and zero-pad.
"""),
code("""
df["postal_code"] = (df["postal_code"].astype("Float64").astype("Int64")
                     .astype(str).str.zfill(5).replace("<NA>", None))

# Trim stray whitespace in every text column.
text_cols = [c for c in df.columns
             if pd.api.types.is_string_dtype(df[c]) or df[c].dtype == "object"]
for col in text_cols:
    df[col] = df[col].astype("string").str.strip()

print(f"Still missing a postal code: {df.postal_code.isna().sum()}")
df.loc[df.postal_code.isna(), ["city", "state"]].drop_duplicates()
"""),
md("""
## 5. The Burlington problem

All 11 remaining gaps are **Burlington, Vermont**. Vermont ZIP codes begin with a zero
(Burlington is 05401), so the leading zero was almost certainly stripped by whatever
system exported this file, and the value was lost rather than corrupted.

Two options:

1. **Impute from the data** — take the most common postal code for that city and state.
   Reusable and defensible, but here every Burlington VT row is missing, so there is
   nothing to impute from.
2. **Fill from an external source** — we happen to know it is 05401.

The pipeline does (1) and leaves the residual null. Option (2) would put a value into a
file labelled "cleaned" that cannot be traced to the source data, and `postal_code` is
used in no analysis — `state` is the geographic grain. The gap is documented instead.
"""),
code("""
missing_before = df.postal_code.isna().sum()
mode_by_city = (df.dropna(subset=["postal_code"])
                  .groupby(["state", "city"])["postal_code"]
                  .agg(lambda s: s.mode().iat[0]))
keys = pd.MultiIndex.from_arrays([df["state"], df["city"]])
df["postal_code"] = df["postal_code"].fillna(pd.Series(keys.map(mode_by_city), index=df.index))

print(f"Imputed from city/state: {missing_before - df.postal_code.isna().sum()}")
print(f"Documented as unknown  : {df.postal_code.isna().sum()}")
"""),
md("## 6. Validation"),
code("""
checks = [
    ("No null order IDs",              df.order_id.isna().sum()),
    ("No null sales",                  df.sales.isna().sum()),
    ("No duplicates",                  df.drop(columns=["row_id"]).duplicated().sum()),
    ("Sales non-negative",             (df.sales < 0).sum()),
    ("Quantity positive",              (df.quantity <= 0).sum()),
    ("Discount within 0-1",            (~df.discount.between(0, 1)).sum()),
    ("Ship date >= order date",        (df.ship_date < df.order_date).sum()),
    ("Country single-valued",          (df.country != "United States").sum()),
    ("Region in expected set",         (~df.region.isin(["West","East","Central","South"])).sum()),
]
results = pd.DataFrame(checks, columns=["rule", "violations"])
results["status"] = np.where(results.violations == 0, "PASS", "FAIL")
results
"""),
md("## 7. Result"),
code("""
summary = pd.Series({
    "Rows in":        f"{len(raw):,}",
    "Rows out":       f"{len(df):,}",
    "Rows dropped":   f"{len(raw) - len(df):,}",
    "Total sales":    f"${df.sales.sum():,.2f}",
    "Total profit":   f"${df.profit.sum():,.2f}",
    "Profit margin":  f"{df.profit.sum()/df.sales.sum()*100:.2f}%",
    "Orders":         f"{df.order_id.nunique():,}",
    "Customers":      f"{df.customer_id.nunique():,}",
}, name="Value").to_frame()
summary
"""),
md("""
**9,993 clean transactions**, matching the canonical Superstore row count.

Revenue totals are unchanged by the cleaning, because every dropped row had no sales value.
That is the check worth stating: cleaning removed noise from the row counts without
altering a single financial figure.

→ Continue to `02_feature_engineering.ipynb`
"""),
]


# ══════════════════════════════════════════════ 02 FEATURE ENGINEERING
NB02 = [
md("""
# 02 · Feature Engineering

**Input:** `data/cleaned/superstore_clean.csv`
**Output:** `data/processed/superstore_features.csv`, `customer_profile.csv`

26 features across three groups — time, value, and customer. Every one exists because a
specific question or visual needs it; none are added speculatively.
"""),
code(SETUP),
code("""
df = pd.read_csv(ROOT / "data" / "cleaned" / "superstore_clean.csv",
                 parse_dates=["order_date", "ship_date"], dtype={"postal_code": str})
print(f"{len(df):,} rows x {df.shape[1]} columns")
"""),
md("## 1. Time features"),
code("""
d = df.order_date
df["order_year"] = d.dt.year
df["order_month"] = d.dt.month
df["order_month_name"] = d.dt.strftime("%b")
df["order_quarter"] = "Q" + d.dt.quarter.astype(str)
df["year_month"] = d.dt.to_period("M").astype(str)
df["order_day_name"] = d.dt.day_name()

# Weekend orders may behave differently from weekday B2B purchasing - worth testing.
df["is_weekend_order"] = d.dt.dayofweek.isin([5, 6])

# Fulfilment speed, and a flag against a 5-day internal SLA.
df["shipping_days"] = (df.ship_date - d).dt.days
df["is_delayed"] = df.shipping_days > 5

df[["order_date", "order_quarter", "order_day_name",
    "is_weekend_order", "shipping_days", "is_delayed"]].head()
"""),
md("## 2. Value features"),
code("""
# Guard both denominators - a zero would produce inf rather than raising.
df["profit_margin"] = df.profit / df.sales.where(df.sales != 0) * 100
df["unit_price"] = df.sales / df.quantity.where(df.quantity != 0)
df["is_loss"] = df.profit < 0

# Revenue given away versus list price on each line.
df["discount_value"] = np.where(df.discount < 1,
                                df.sales / (1 - df.discount) - df.sales, 0.0)

df["discount_band"] = pd.cut(df.discount, bins=[-0.01, 0, .15, .30, .50, 1.0],
                             labels=["No discount", "1-15%", "16-30%", "31-50%", "50%+"])

# Size bands cut on quartiles, so they adapt to any extract rather than
# hardcoding thresholds that would go stale.
q = df.sales.quantile([.25, .5, .75]).tolist()
df["sales_category"] = pd.cut(df.sales, bins=[-0.01] + q + [df.sales.max()],
                              labels=["Small", "Medium", "Large", "Very Large"])

df.groupby("discount_band", observed=True).agg(
    lines=("sales", "size"), sales=("sales", "sum"),
    profit=("profit", "sum")).assign(margin=lambda x: x.profit / x.sales * 100)
"""),
md("""
The discount bands already show the finding this project is built on: margin is strongly
positive with no discount and deeply negative above 30%. Quantified properly in notebook 03.
"""),
md("## 3. Customer profile and RFM"),
code("""
snapshot = df.order_date.max() + pd.Timedelta(days=1)

prof = df.groupby(["customer_id", "customer_name", "segment"]).agg(
    lifetime_orders=("order_id", "nunique"),
    lifetime_value=("sales", "sum"),
    lifetime_profit=("profit", "sum"),
    avg_discount=("discount", "mean"),
    first_order=("order_date", "min"),
    last_order=("order_date", "max"),
).reset_index()

prof["avg_order_value"] = prof.lifetime_value / prof.lifetime_orders
prof["recency_days"] = (snapshot - prof.last_order).dt.days
prof["is_repeat"] = prof.lifetime_orders > 1

# Relative threshold, not a magic number: the flag stays meaningful as the business grows.
prof["is_high_value"] = prof.lifetime_value >= prof.lifetime_value.quantile(0.80)

print(f"{len(prof):,} customers")
prof.sort_values("lifetime_value", ascending=False).head()
"""),
code("""
# RFM: 5 is best. Recency is reversed - fewer days since the last order is better.
prof["r_score"] = pd.qcut(prof.recency_days, 5, labels=[5,4,3,2,1]).astype(int)
prof["f_score"] = pd.qcut(prof.lifetime_orders.rank(method="first"), 5,
                          labels=[1,2,3,4,5]).astype(int)
prof["m_score"] = pd.qcut(prof.lifetime_value, 5, labels=[1,2,3,4,5]).astype(int)
prof["rfm_score"] = prof.r_score + prof.f_score + prof.m_score

prof["rfm_segment"] = np.select(
    [prof.rfm_score >= 13, prof.rfm_score >= 10, prof.rfm_score >= 7],
    ["Champion", "Loyal", "Potential"], default="At Risk")

rfm = prof.groupby("rfm_segment").agg(
    customers=("customer_id", "size"), revenue=("lifetime_value", "sum"),
    avg_orders=("lifetime_orders", "mean"), avg_recency=("recency_days", "mean"))
rfm["pct_revenue"] = rfm.revenue / rfm.revenue.sum() * 100
rfm.sort_values("revenue", ascending=False)
"""),
code("""
order = ["Champion", "Loyal", "Potential", "At Risk"]
r = rfm.reindex(order)

fig, ax = plt.subplots(1, 2, figsize=(12, 4))
ax[0].bar(order, r.customers, color=[TEAL, BLUE, AMBER, RED], width=.6)
ax[0].set_title("Customers per RFM Segment"); ax[0].set_ylabel("Customers")
ax[1].bar(order, r.pct_revenue, color=[TEAL, BLUE, AMBER, RED], width=.6)
ax[1].set_title("Share of Revenue per RFM Segment"); ax[1].set_ylabel("% of revenue")
for a, vals in [(ax[0], r.customers), (ax[1], r.pct_revenue)]:
    for x, v in zip(order, vals):
        a.text(x, v, f"{v:,.0f}" if v > 100 else f"{v:.1f}%",
               ha="center", va="bottom", fontsize=9, weight="bold")
plt.tight_layout(); plt.savefig(IMAGES / "rfm_segments.png"); plt.show()
"""),
md("""
**Finding.** *At Risk* is 24.7% of the customer base but only 8.4% of revenue, with an
average of 329 days since their last order. *Champions* are 15.6% of customers and 28.2%
of revenue. The win-back list is large but individually low-value — worth an automated
email sequence rather than sales time.
"""),
md("## 4. Attach and save"),
code("""
df = df.merge(prof[["customer_id", "lifetime_orders", "lifetime_value",
                    "is_high_value", "is_repeat", "rfm_segment"]],
              on="customer_id", how="left")

# This notebook shows the reasoning; src/feature_engineering.py is the single source
# of truth and writes the canonical files. Deliberately not overwriting them here -
# a notebook that half-rebuilds a pipeline artefact is how silent drift starts.
canonical = pd.read_csv(ROOT / "data" / "processed" / "superstore_features.csv",
                        nrows=1)

print(f"This notebook  : {len(df):,} rows x {df.shape[1]} columns")
print(f"Pipeline output: {canonical.shape[1]} columns "
      f"(adds order_week, year_quarter, margin_band and other variants)")
print(f"Customers      : {len(prof):,} rows x {prof.shape[1]} columns")
"""),
md("→ Continue to `03_eda.ipynb`"),
]


# ═══════════════════════════════════════════════════════════ 03 EDA
NB03 = [
md("""
# 03 · Exploratory Data Analysis

**Input:** `data/processed/superstore_features.csv`

Answering the questions the CEO actually asked, plus the statistical work behind them:
distributions, outliers, and correlation.
"""),
code(SETUP),
code("""
df = pd.read_csv(ROOT / "data" / "processed" / "superstore_features.csv",
                 parse_dates=["order_date", "ship_date"], dtype={"postal_code": str})
orders = df.order_id.nunique()
pd.Series({
    "Total Sales":     f"${df.sales.sum():,.2f}",
    "Total Profit":    f"${df.profit.sum():,.2f}",
    "Profit Margin":   f"{df.profit.sum()/df.sales.sum()*100:.2f}%",
    "Orders":          f"{orders:,}",
    "Customers":       f"{df.customer_id.nunique():,}",
    "Avg Order Value": f"${df.sales.sum()/orders:,.2f}",
}, name="Value").to_frame()
"""),
md("## 1. Distribution analysis"),
code("""
fig, ax = plt.subplots(1, 3, figsize=(14, 3.8))

ax[0].hist(df.sales, bins=80, color=BLUE, alpha=.85); ax[0].set_yscale("log")
ax[0].set_title("Sales per line (log count)"); ax[0].set_xlabel("Sales ($)")

ax[1].hist(np.log10(df.sales.clip(lower=.1)), bins=60, color=TEAL, alpha=.85)
ax[1].set_title("log10(Sales) — near-normal"); ax[1].set_xlabel("log10(sales)")

ax[2].hist(df.profit, bins=100, color=AMBER, alpha=.85); ax[2].set_yscale("log")
ax[2].axvline(0, color=RED, lw=1.4)
ax[2].set_title("Profit per line (log count)"); ax[2].set_xlabel("Profit ($)")
plt.tight_layout(); plt.savefig(IMAGES / "distributions_eda.png"); plt.show()

print(f"Sales  skew: {df.sales.skew():.2f}   kurtosis: {df.sales.kurtosis():.2f}")
print(f"Profit skew: {df.profit.skew():.2f}   kurtosis: {df.profit.kurtosis():.2f}")
print(f"Median sale ${df.sales.median():,.2f} vs mean ${df.sales.mean():,.2f}")
"""),
md("""
**Sales are heavily right-skewed** (skew ≈ 12.9): the mean is more than three times the
median, so the mean is a misleading summary. Medians are used for typical-value statements
throughout, and log scales for the charts.

The log transform is close to normal, which matters if this ever feeds a model.
"""),
md("## 2. Outlier detection"),
code("""
def iqr_bounds(s):
    q1, q3 = s.quantile([.25, .75]); iqr = q3 - q1
    return q1 - 1.5*iqr, q3 + 1.5*iqr

rows = []
for col in ["sales", "profit", "quantity", "discount", "shipping_days"]:
    lo, hi = iqr_bounds(df[col].dropna())
    mask = (df[col] < lo) | (df[col] > hi)
    rows.append({"column": col, "lower": round(lo,2), "upper": round(hi,2),
                 "outliers": int(mask.sum()),
                 "pct": round(mask.mean()*100, 2),
                 "skew": round(df[col].skew(), 2)})
pd.DataFrame(rows)
"""),
code("""
extremes = pd.concat([
    df.nlargest(3, "sales")[["product_name","sales","profit","discount"]],
    df.nsmallest(3, "profit")[["product_name","sales","profit","discount"]],
])
extremes
"""),
md("""
**Decision: outliers are kept.** The largest sale is a $22,638 videoconferencing unit sold
at a 50% discount — and it *lost* $1,811. The largest losses are all deeply discounted
machines and binding systems.

These are not data errors. They are the exact transactions the analysis is about; removing
them would delete the finding. Skew is handled with log scales, not by dropping rows.
"""),
md("## 3. Correlation"),
code("""
num = df[["sales", "profit", "quantity", "discount", "unit_price",
          "shipping_days", "profit_margin"]]
corr = num.corr()

fig, ax = plt.subplots(figsize=(8, 6.2))
mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
sns.heatmap(corr, mask=mask, annot=True, fmt=".2f", cmap="RdBu_r", center=0,
            vmin=-1, vmax=1, square=True, linewidths=.5,
            cbar_kws={"shrink": .8, "label": "Pearson r"}, ax=ax)
ax.set_title("Correlation Matrix", fontsize=13, weight="bold", pad=12)
plt.tight_layout(); plt.savefig(IMAGES / "correlation_heatmap.png"); plt.show()

corr["profit"].drop("profit").sort_values().to_frame("corr with profit")
"""),
md("""
**Reading it carefully.** Discount correlates with profit at only about −0.22, which looks
weak — but Pearson measures *linear* association, and the relationship is not linear. It is
a threshold effect: nothing much happens up to 30%, then margin collapses. A single
correlation coefficient hides that entirely, which is why the next section bands the data
instead of trusting the coefficient.

`profit_margin` correlates with discount far more strongly (≈ −0.36), because margin is
scale-free while raw profit is dominated by order size.
"""),
md("## 4. Does discounting reduce profit?"),
code("""
bands = ["No discount", "1-15%", "16-30%", "31-50%", "50%+"]
disc = (df.groupby("discount_band", observed=True)
          .agg(lines=("sales","size"), sales=("sales","sum"),
               profit=("profit","sum"), loss_lines=("is_loss","sum"))
          .reindex(bands))
disc["margin_%"] = disc.profit / disc.sales * 100
disc["loss_rate_%"] = disc.loss_lines / disc.lines * 100
disc
"""),
code("""
fig, ax = plt.subplots(1, 2, figsize=(12.5, 4))

cols = [RED if v < 0 else TEAL for v in disc["margin_%"]]
ax[0].bar(disc.index, disc["margin_%"], color=cols, width=.6)
ax[0].axhline(0, color="#6b7280", lw=1); ax[0].tick_params(axis="x", rotation=20)
ax[0].set_title("Profit Margin by Discount Band"); ax[0].set_ylabel("Margin (%)")
for x, v in zip(disc.index, disc["margin_%"]):
    ax[0].text(x, v, f"{v:.0f}%", ha="center",
               va="bottom" if v > 0 else "top", fontsize=9, weight="bold")

s = df.sample(min(3000, len(df)), random_state=7)
ax[1].scatter(s.discount*100, s.profit, s=9, alpha=.35,
              c=[RED if p < 0 else TEAL for p in s.profit])
ax[1].axhline(0, color="#6b7280", lw=1)
ax[1].axvline(30, color=PURPLE, ls="--", lw=1.6)
ax[1].text(31, s.profit.max()*.8, "30% threshold", color=PURPLE, fontsize=9)
ax[1].set_title("Discount vs Profit per Line")
ax[1].set_xlabel("Discount (%)"); ax[1].set_ylabel("Profit ($)")
plt.tight_layout(); plt.savefig(IMAGES / "discount_impact.png"); plt.show()

deep = df[df.discount > .30]
print(f"Lines above 30% discount: {len(deep):,} ({len(deep)/len(df)*100:.1f}%)")
print(f"Profit destroyed        : ${deep.profit.sum():,.2f}")
print(f"Profit without them     : ${df[df.discount <= .30].profit.sum():,.2f}")
"""),
md("""
**Yes — but only past a threshold.** Margin is +29.5% at full price, holds at +9.2% through
30%, then falls to −24.8% and −119.2%. Just 11.7% of lines sit above 30% and they destroy
**$125,007** against total profit of $286,409.
"""),
md("## 5. Which month has the highest sales?"),
code("""
monthly = df.groupby("year_month").agg(sales=("sales","sum"), profit=("profit","sum")).reset_index()
monthly["date"] = pd.to_datetime(monthly.year_month)

fig, ax = plt.subplots(figsize=(13, 4))
ax.plot(monthly.date, monthly.sales, color=BLUE, lw=1.9, marker="o", ms=3.5)
ax.fill_between(monthly.date, monthly.sales, color=BLUE, alpha=.10)
ax.plot(monthly.date, monthly.sales.rolling(3).mean(), color=PURPLE, lw=1.6, ls="--",
        label="3-month rolling avg")
ax.set_title("Monthly Sales, 2015–2018"); ax.yaxis.set_major_formatter(money)
ax.legend(frameon=False)
plt.tight_layout(); plt.savefig(IMAGES / "sales_trend.png"); plt.show()

season = df.groupby("order_month").sales.sum() / df.order_year.nunique()
print("Strongest months:", ", ".join(
    pd.Timestamp(2020, m, 1).strftime("%B") for m in season.nlargest(3).index))
print("Weakest months  :", ", ".join(
    pd.Timestamp(2020, m, 1).strftime("%B") for m in season.nsmallest(3).index))
"""),
md("## 6. Which category performs best?"),
code("""
cat = (df.groupby("category").agg(sales=("sales","sum"), profit=("profit","sum"))
         .assign(margin=lambda d: d.profit/d.sales*100,
                 share=lambda d: d.sales/d.sales.sum()*100)
         .sort_values("sales", ascending=False))

fig, ax = plt.subplots(1, 2, figsize=(12, 4))
ax[0].pie(cat.sales, labels=cat.index, autopct="%1.1f%%", startangle=90,
          colors=[BLUE, TEAL, AMBER], wedgeprops=dict(width=.42, edgecolor="w"))
ax[0].set_title("Share of Sales")
ax[1].bar(cat.index, cat.margin, color=[BLUE, TEAL, AMBER], width=.55)
ax[1].set_title("Profit Margin by Category"); ax[1].set_ylabel("Margin (%)")
for x, v in zip(cat.index, cat.margin):
    ax[1].text(x, v, f"{v:.1f}%", ha="center", va="bottom", weight="bold")
plt.tight_layout(); plt.savefig(IMAGES / "category_performance.png"); plt.show()
cat
"""),
code("""
sub = (df.groupby("sub_category").agg(sales=("sales","sum"), profit=("profit","sum"),
                                      discount=("discount","mean"))
         .assign(margin=lambda d: d.profit/d.sales*100).sort_values("profit"))

fig, ax = plt.subplots(figsize=(9, 6))
ax.barh(sub.index, sub.profit, color=[RED if v < 0 else TEAL for v in sub.profit])
ax.axvline(0, color="#6b7280", lw=1)
ax.set_title("Profit by Sub-Category"); ax.xaxis.set_major_formatter(money)
plt.tight_layout(); plt.savefig(IMAGES / "profit_analysis.png"); plt.show()
sub[sub.profit < 0]
"""),
md("""
**Furniture is 32% of revenue at a 2.5% margin.** Tables lose $17,725 and Bookcases $3,473.
Tables carry a 26% average discount — the deepest in the catalogue.
"""),
md("## 7. Which states and cities lose money?"),
code("""
state = (df.groupby(["state","region"]).agg(sales=("sales","sum"), profit=("profit","sum"),
                                            discount=("discount","mean"))
           .assign(margin=lambda d: d.profit/d.sales*100).reset_index())
losers = state[state.profit < 0].sort_values("profit")

fig, ax = plt.subplots(1, 2, figsize=(13, 4.4))
ax[0].barh(losers.state[::-1], losers.profit[::-1], color=RED)
ax[0].set_title(f"{len(losers)} States Operating at a Loss")
ax[0].xaxis.set_major_formatter(money)

ax[1].scatter(state.discount*100, state.margin, s=42, alpha=.75,
              c=[RED if m < 0 else TEAL for m in state.margin])
ax[1].axhline(0, color="#6b7280", lw=1)
ax[1].set_title("State Discount vs Margin")
ax[1].set_xlabel("Avg discount (%)"); ax[1].set_ylabel("Margin (%)")
plt.tight_layout(); plt.savefig(IMAGES / "state_performance.png"); plt.show()

print(f"Loss states avg discount    : {losers.discount.mean()*100:.1f}%")
print(f"Profitable states avg disc. : {state[state.profit>0].discount.mean()*100:.1f}%")
"""),
code("""
city = (df.groupby(["city","state"]).agg(sales=("sales","sum"), profit=("profit","sum"))
          .assign(margin=lambda d: d.profit/d.sales*100)
          .sort_values("sales", ascending=False).head(10).reset_index())
city["label"] = city.city + ", " + city.state

fig, ax = plt.subplots(figsize=(9.5, 4.4))
ax.barh(city.label[::-1], city.sales[::-1],
        color=[RED if p < 0 else BLUE for p in city.profit[::-1]])
ax.set_title("Top 10 Cities by Revenue — red bars lose money")
ax.xaxis.set_major_formatter(money)
plt.tight_layout(); plt.savefig(IMAGES / "city_performance.png"); plt.show()
city[["label","sales","profit","margin"]]
"""),
md("""
**Philadelphia is the fifth-largest city by revenue and loses $13,838.** Houston is sixth
and loses $10,154. Revenue rank and profit contribution are not the same thing, and a
revenue-only view of the business would rank both as successes.

Every loss-making state discounts at 28–40%, against 10.9% in West. The geographic pattern
is the discount pattern.
"""),
md("## 8. Which segment and shipping mode perform best?"),
code("""
seg = (df.groupby("segment").agg(customers=("customer_id","nunique"),
                                 orders=("order_id","nunique"), sales=("sales","sum"),
                                 profit=("profit","sum"))
         .assign(margin=lambda d: d.profit/d.sales*100,
                 aov=lambda d: d.sales/d.orders).sort_values("sales", ascending=False))

ship = (df.groupby("ship_mode").agg(orders=("order_id","nunique"),
                                    avg_days=("shipping_days","mean"),
                                    sales=("sales","sum"), profit=("profit","sum"))
          .assign(margin=lambda d: d.profit/d.sales*100).sort_values("margin", ascending=False))

fig, ax = plt.subplots(1, 2, figsize=(12.5, 4))
ax[0].bar(seg.index, seg.aov, color=[BLUE, TEAL, AMBER], width=.55)
ax[0].set_title("Average Order Value by Segment"); ax[0].set_ylabel("AOV ($)")
for x, v in zip(seg.index, seg.aov):
    ax[0].text(x, v, f"${v:,.0f}", ha="center", va="bottom", weight="bold")
ax[1].bar(ship.index, ship.margin, color=PURPLE, width=.55)
ax[1].set_title("Profit Margin by Ship Mode"); ax[1].set_ylabel("Margin (%)")
ax[1].tick_params(axis="x", rotation=15)
for x, v in zip(ship.index, ship.margin):
    ax[1].text(x, v, f"{v:.1f}%", ha="center", va="bottom", weight="bold")
plt.tight_layout(); plt.savefig(IMAGES / "segment_shipping.png"); plt.show()
display(seg, ship)
"""),
md("""
**Home Office has the highest average order value** ($472) despite being the smallest
segment — worth noting against the assumption that Corporate buys biggest.

**Standard Class carries the lowest margin (12.1%) and misses the 5-day SLA on 30.6% of
lines.** First Class is both faster and higher-margin, which is counter-intuitive and worth
a follow-up: it suggests the cheap shipping option is attached to the discount-heavy orders.
"""),
md("→ Continue to `04_visualization.ipynb`"),
]


# ═══════════════════════════════════════════════ 04 VISUALIZATION
NB04 = [
md("""
# 04 · Visualisation & Forecast

Dashboard-ready visuals and a three-month sales forecast.
"""),
code(SETUP),
code("""
df = pd.read_csv(ROOT / "data" / "processed" / "superstore_features.csv",
                 parse_dates=["order_date", "ship_date"], dtype={"postal_code": str})
monthly = (df.groupby("year_month").agg(sales=("sales","sum"), profit=("profit","sum"))
             .reset_index())
monthly["date"] = pd.to_datetime(monthly.year_month)
print(f"{len(monthly)} months, {monthly.date.min():%b %Y} to {monthly.date.max():%b %Y}")
"""),
md("## 1. Yearly growth"),
code("""
yearly = df.groupby("order_year").agg(sales=("sales","sum"), profit=("profit","sum"),
                                      orders=("order_id","nunique")).reset_index()
yearly["yoy"] = yearly.sales.pct_change()*100
yearly["margin"] = yearly.profit/yearly.sales*100

fig, ax = plt.subplots(1, 2, figsize=(12, 4))
ax[0].bar(yearly.order_year.astype(str), yearly.sales, color=BLUE, width=.6)
ax[0].set_title("Annual Sales"); ax[0].yaxis.set_major_formatter(money)
for x, v in zip(yearly.order_year.astype(str), yearly.sales):
    ax[0].text(x, v, f"${v/1000:,.0f}K", ha="center", va="bottom", fontsize=9)

g = yearly.dropna(subset=["yoy"])
ax[1].bar(g.order_year.astype(str), g.yoy,
          color=[RED if v < 0 else TEAL for v in g.yoy], width=.6)
ax[1].axhline(0, color="#9aa3b2", lw=1)
ax[1].set_title("Year-over-Year Growth"); ax[1].set_ylabel("%")
for x, v in zip(g.order_year.astype(str), g.yoy):
    ax[1].text(x, v, f"{v:+.1f}%", ha="center",
               va="bottom" if v > 0 else "top", fontsize=9)
plt.tight_layout(); plt.savefig(IMAGES / "yearly_growth.png"); plt.show()
yearly
"""),
md("""
## 2. Three-month forecast

**Method: seasonal naive with a linear trend.** Each future month is predicted as the same
month last year, scaled by the trailing year-over-year growth rate.

Chosen deliberately over ARIMA or Prophet: with only 48 monthly observations and strong
December seasonality, a fitted model has too few complete seasonal cycles to learn from and
tends to produce confident, wrong intervals. A transparent baseline that a business reader
can verify by hand is worth more here than an opaque one — and it is the benchmark any
sophisticated model would have to beat.
"""),
code("""
s = monthly.set_index("date").sales

# Backtest: hold out the last 6 months, forecast them, measure the error.
train, test = s[:-6], s[-6:]

def seasonal_naive_forecast(series, periods):
    growth = (series[-12:].sum() / series[-24:-12].sum()) if len(series) >= 24 else 1.0
    last_year = series[-12:]
    out, idx = [], []
    for i in range(periods):
        nxt = series.index[-1] + pd.DateOffset(months=i+1)
        out.append(last_year.iloc[i % 12] * growth)
        idx.append(nxt)
    return pd.Series(out, index=idx), growth

pred, growth = seasonal_naive_forecast(train, 6)
mape = (abs(pred.values - test.values) / test.values).mean() * 100
mae = abs(pred.values - test.values).mean()
print(f"Backtest on the last 6 months")
print(f"  Growth factor applied : {growth:.3f}")
print(f"  MAPE                  : {mape:.1f}%")
print(f"  MAE                   : ${mae:,.0f}")
"""),
code("""
forecast, growth = seasonal_naive_forecast(s, 3)

# An empirical interval from historical residuals, not a model assumption.
resid_pct = abs(pred.values - test.values) / test.values
band = resid_pct.mean()
lower, upper = forecast * (1 - band), forecast * (1 + band)

fig, ax = plt.subplots(figsize=(13, 4.4))
ax.plot(s.index, s.values, color=BLUE, lw=1.8, marker="o", ms=3, label="Actual")
ax.plot(forecast.index, forecast.values, color=PURPLE, lw=2.2, ls="--",
        marker="s", ms=5, label="Forecast")
ax.fill_between(forecast.index, lower, upper, color=PURPLE, alpha=.16,
                label=f"±{band*100:.0f}% (empirical)")
ax.axvline(s.index[-1], color="#9aa3b2", ls=":", lw=1.2)
ax.set_title("Monthly Sales with 3-Month Forecast")
ax.yaxis.set_major_formatter(money); ax.legend(frameon=False)
plt.tight_layout(); plt.savefig(IMAGES / "sales_forecast.png"); plt.show()

pd.DataFrame({"forecast": forecast.round(0), "lower": lower.round(0),
              "upper": upper.round(0)})
"""),
md("""
The backtest MAPE is the number to quote, not the forecast itself. It says how wrong this
method was on months it had not seen — the honest measure of whether the projection is
usable for planning.
"""),
md("## 3. Discount simulation — the what-if"),
code("""
# What would profit be if every discount were capped at a given level?
# Assumes the sale still happens at the lower discount, which is optimistic:
# some customers would walk. Treated as an upper bound, not a promise.
def simulate_cap(cap):
    d = df.copy()
    capped = d.discount.clip(upper=cap)
    list_price = np.where(d.discount < 1, d.sales / (1 - d.discount), d.sales)
    new_sales = list_price * (1 - capped)
    # Cost per line is unchanged; profit moves with the recovered revenue.
    return (d.profit + (new_sales - d.sales)).sum()

caps = [1.0, .70, .50, .40, .30, .20, .10, 0.0]
sim = pd.DataFrame({
    "cap_%": [int(c*100) for c in caps],
    "profit": [simulate_cap(c) for c in caps],
})
sim["uplift"] = sim.profit - sim.profit.iloc[0]
sim["uplift_%"] = sim.uplift / sim.profit.iloc[0] * 100

fig, ax = plt.subplots(figsize=(9.5, 4))
ax.plot(sim["cap_%"], sim.profit, color=PURPLE, lw=2.2, marker="o")
ax.axhline(df.profit.sum(), color="#9aa3b2", ls="--", lw=1.2, label="Current profit")
ax.axvline(30, color=TEAL, ls=":", lw=1.6, label="Recommended cap (30%)")
ax.set_title("Simulated Profit by Discount Cap")
ax.set_xlabel("Maximum discount allowed (%)"); ax.set_ylabel("Total profit ($)")
ax.yaxis.set_major_formatter(money); ax.legend(frameon=False); ax.invert_xaxis()
plt.tight_layout(); plt.savefig(IMAGES / "discount_simulation.png"); plt.show()
sim
"""),
md("""
**The 30% cap is where the curve flattens.** Tightening further returns progressively less
while affecting far more orders — the classic point of diminishing returns, and the reason
the recommendation is 30% rather than "discount less".

Stated as an upper bound: the model assumes every sale still closes at the lower discount.
Some would not. The pilot is what settles it.
"""),
md("## 4. Regional and product views"),
code("""
region = (df.groupby("region").agg(sales=("sales","sum"), profit=("profit","sum"),
                                   discount=("discount","mean"))
            .assign(margin=lambda d: d.profit/d.sales*100).sort_values("sales", ascending=False))

fig, ax = plt.subplots(1, 2, figsize=(12.5, 4))
x = np.arange(len(region)); w = .38
ax[0].bar(x-w/2, region.sales, w, label="Sales", color=BLUE)
ax[0].bar(x+w/2, region.profit, w, label="Profit", color=TEAL)
ax[0].set_xticks(x, region.index); ax[0].set_title("Sales vs Profit by Region")
ax[0].yaxis.set_major_formatter(money); ax[0].legend(frameon=False)

ax[1].scatter(region.discount*100, region.margin, s=190, color=PURPLE, zorder=3)
for name, r in region.iterrows():
    ax[1].annotate(name, (r.discount*100, r.margin), textcoords="offset points",
                   xytext=(0,13), ha="center", fontsize=10)
ax[1].set_title("Discount vs Margin by Region")
ax[1].set_xlabel("Avg discount (%)"); ax[1].set_ylabel("Margin (%)"); ax[1].margins(.22)
plt.tight_layout(); plt.savefig(IMAGES / "regional_performance.png"); plt.show()
"""),
code("""
prod = df.groupby("product_name").sales.sum().nlargest(10)
cust = df.groupby("customer_name").sales.sum().nlargest(10)

fig, ax = plt.subplots(1, 2, figsize=(14, 4.6))
ax[0].barh([p[:32] for p in prod.index][::-1], prod.values[::-1], color=BLUE)
ax[0].set_title("Top 10 Products by Sales"); ax[0].xaxis.set_major_formatter(money)
ax[1].barh(cust.index[::-1], cust.values[::-1], color=TEAL)
ax[1].set_title("Top 10 Customers by Sales"); ax[1].xaxis.set_major_formatter(money)
plt.tight_layout(); plt.savefig(IMAGES / "top_products_customers.png"); plt.show()
"""),
md("## 5. Export aggregates for Power BI"),
code("""
out = ROOT / "data" / "processed"
exports = {
    "agg_monthly.csv":     monthly[["year_month","sales","profit"]],
    "agg_yearly.csv":      yearly,
    "agg_region.csv":      region.reset_index(),
    "agg_forecast.csv":    pd.DataFrame({"date": forecast.index, "forecast": forecast.values,
                                         "lower": lower.values, "upper": upper.values}),
    "agg_discount_sim.csv": sim,
}
for name, frame in exports.items():
    frame.to_csv(out / name, index=False)
    print(f"  {name:<24} {len(frame):>4} rows")
"""),
md("""
## Summary

| Finding | Evidence |
|---|---|
| Discounts above 30% destroy $125,007 | 11.7% of lines, margin −24.8% then −119.2% |
| Furniture: 32% of revenue, 2.5% margin | Tables −$17.7K, Bookcases −$3.5K |
| 10 states lose money | All discount 28–40% vs West's 10.9% |
| Philadelphia is 5th by revenue, loses $13.8K | Revenue rank ≠ profit contribution |
| Growth is recent | −2.8% (2016), +29.5% (2017), +20.4% (2018) |
| At Risk = 24.7% of customers, 8.4% of revenue | Avg 329 days since last order |

Every recommendation traces to one of these rows.
"""),
]


def build(name: str, cells: list) -> Path:
    nb = nbf.v4.new_notebook(cells=cells)
    nb.metadata = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.11"}}
    path = NBDIR / name
    nbf.write(nb, path)
    NotebookClient(nb, timeout=900, kernel_name="python3",
                   resources={"metadata": {"path": str(NBDIR)}}).execute()
    nbf.write(nb, path)
    print(f"  {name:<34} {len(cells):>3} cells")
    return path


def main() -> None:
    NBDIR.mkdir(parents=True, exist_ok=True)
    for name, cells in [("01_data_cleaning.ipynb", NB01),
                        ("02_feature_engineering.ipynb", NB02),
                        ("03_eda.ipynb", NB03),
                        ("04_visualization.ipynb", NB04)]:
        build(name, cells)
    print(f"\nSaved -> {NBDIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
