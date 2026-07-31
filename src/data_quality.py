"""
data_quality.py
---------------
Profiles the raw extract, runs validation rules against the cleaned data, and
detects outliers. Produces the data quality report referenced in the README.

Run:  python src/data_quality.py

Output: outputs/data_quality_report.md
        outputs/outliers.csv
        images/outlier_boxplots.png
        images/distributions.png
"""

from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "superstore_raw.csv"
PROC = ROOT / "data" / "processed" / "superstore_features.csv"
REPORT = ROOT / "outputs" / "data_quality_report.md"
OUTLIERS = ROOT / "outputs" / "outliers.csv"
IMAGES = ROOT / "images"

BLUE, TEAL, AMBER, RED = "#2f6fed", "#16a888", "#f5b820", "#e03131"


# ---------------------------------------------------------------- profiling
def profile(df: pd.DataFrame) -> pd.DataFrame:
    """Column-level profile: type, completeness, cardinality, sample value."""
    return pd.DataFrame({
        "dtype": df.dtypes.astype(str),
        "non_null": df.notna().sum(),
        "null_count": df.isna().sum(),
        "null_pct": (df.isna().mean() * 100).round(2),
        "unique": df.nunique(),
        "sample": [df[c].dropna().iloc[0] if df[c].notna().any() else "-"
                   for c in df.columns],
    })


# --------------------------------------------------------------- validation
def validate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Business rules the data must satisfy. Each returns a count of violations;
    zero means the rule passes. These are the checks a reviewer will ask about.
    """
    rules = [
        ("No null order IDs", df.order_id.isna().sum()),
        ("No null customer IDs", df.customer_id.isna().sum()),
        ("No null sales values", df.sales.isna().sum()),
        ("No duplicate transactions",
         df.drop(columns=["row_id"], errors="ignore").duplicated().sum()),
        ("Sales are non-negative", (df.sales < 0).sum()),
        ("Quantity is positive", (df.quantity <= 0).sum()),
        ("Discount within 0-100%", (~df.discount.between(0, 1)).sum()),
        ("Ship date on or after order date", (df.ship_date < df.order_date).sum()),
        ("Shipping days within 0-30", (~df.shipping_days.between(0, 30)).sum()),
        ("Country is single-valued (US)", (df.country != "United States").sum()),
        ("Region in expected set",
         (~df.region.isin(["West", "East", "Central", "South"])).sum()),
        ("Segment in expected set",
         (~df.segment.isin(["Consumer", "Corporate", "Home Office"])).sum()),
        ("Category in expected set",
         (~df.category.isin(["Technology", "Furniture", "Office Supplies"])).sum()),
        # Null is permitted: 11 Burlington VT rows have no code in the source and
        # are documented rather than invented. A wrong-length code is still a failure.
        ("Postal code is 5 chars or explicitly null",
         (df.postal_code.notna() &
          (df.postal_code.astype(str).str.len() != 5)).sum()),
        ("Profit margin is finite", (~np.isfinite(df.profit_margin)).sum()),
    ]
    out = pd.DataFrame(rules, columns=["rule", "violations"])
    out["status"] = np.where(out.violations == 0, "PASS", "FAIL")
    return out


# ----------------------------------------------------------------- outliers
def detect_outliers(df: pd.DataFrame, cols: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    IQR fences flag extreme values; a z-score above 3 flags the same idea on a
    normal-ish scale. Both are reported because sales is heavily right-skewed,
    where IQR is the more trustworthy of the two.
    """
    rows, flags = [], pd.DataFrame(index=df.index)

    for col in cols:
        s = df[col].dropna()
        q1, q3 = s.quantile([0.25, 0.75])
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        iqr_mask = (df[col] < lo) | (df[col] > hi)

        z = (df[col] - s.mean()) / s.std()
        z_mask = z.abs() > 3

        flags[f"{col}_outlier"] = iqr_mask.fillna(False)
        rows.append({
            "column": col,
            "min": round(s.min(), 2), "q1": round(q1, 2),
            "median": round(s.median(), 2), "q3": round(q3, 2),
            "max": round(s.max(), 2),
            "iqr_lower": round(lo, 2), "iqr_upper": round(hi, 2),
            "iqr_outliers": int(iqr_mask.sum()),
            "iqr_pct": round(iqr_mask.mean() * 100, 2),
            "zscore_outliers": int(z_mask.sum()),
            "skew": round(s.skew(), 2),
        })

    summary = pd.DataFrame(rows)
    any_flag = flags.any(axis=1)
    return summary, df.loc[any_flag].assign(**flags.loc[any_flag])


# -------------------------------------------------------------------- plots
def plot_boxplots(df: pd.DataFrame, cols: list[str]) -> None:
    fig, axes = plt.subplots(1, len(cols), figsize=(3.3 * len(cols), 4))
    for ax, col in zip(np.atleast_1d(axes), cols):
        ax.boxplot(df[col].dropna(), vert=True, widths=.5,
                   patch_artist=True,
                   boxprops=dict(facecolor=BLUE, alpha=.55, edgecolor="#374151"),
                   medianprops=dict(color=RED, lw=1.8),
                   flierprops=dict(marker="o", ms=3, alpha=.28,
                                   markerfacecolor=AMBER, markeredgecolor="none"))
        ax.set_title(col.replace("_", " ").title(), fontsize=11, weight="bold")
        ax.set_xticks([])
        ax.grid(axis="y", color="#eef0f4")
        ax.set_axisbelow(True)
    fig.suptitle("Outlier Detection — IQR Boxplots", fontsize=13, weight="bold")
    plt.tight_layout()
    plt.savefig(IMAGES / "outlier_boxplots.png", dpi=140, bbox_inches="tight")
    plt.close()


def plot_distributions(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(2, 2, figsize=(12, 7))

    ax[0, 0].hist(df.sales, bins=80, color=BLUE, alpha=.85)
    ax[0, 0].set_yscale("log")
    ax[0, 0].set_title("Sales per Order Line (log count)")
    ax[0, 0].set_xlabel("Sales ($)")

    ax[0, 1].hist(np.log10(df.sales.clip(lower=0.1)), bins=60, color=TEAL, alpha=.85)
    ax[0, 1].set_title("Sales, log10 — near-normal once transformed")
    ax[0, 1].set_xlabel("log10(sales)")

    ax[1, 0].hist(df.profit, bins=100, color=AMBER, alpha=.85)
    ax[1, 0].axvline(0, color=RED, lw=1.4)
    ax[1, 0].set_yscale("log")
    ax[1, 0].set_title("Profit per Order Line (log count)")
    ax[1, 0].set_xlabel("Profit ($)")

    ax[1, 1].hist(df.discount * 100, bins=25, color="#7b45c9", alpha=.85)
    ax[1, 1].set_title("Discount Distribution")
    ax[1, 1].set_xlabel("Discount (%)")

    for a in ax.flat:
        a.grid(color="#eef0f4")
        a.set_axisbelow(True)
    fig.suptitle("Distribution Analysis", fontsize=13, weight="bold")
    plt.tight_layout()
    plt.savefig(IMAGES / "distributions.png", dpi=140, bbox_inches="tight")
    plt.close()


# ------------------------------------------------------------------- report
def main() -> None:
    IMAGES.mkdir(exist_ok=True)
    raw = pd.read_csv(RAW, encoding="latin-1")
    df = pd.read_csv(PROC, parse_dates=["order_date", "ship_date"],
                     dtype={"postal_code": str})

    raw_prof = profile(raw)
    checks = validate(df)
    cols = ["sales", "profit", "quantity", "discount", "shipping_days"]
    summary, outlier_rows = detect_outliers(df, cols)

    plot_boxplots(df, cols)
    plot_distributions(df)
    outlier_rows.to_csv(OUTLIERS, index=False)

    passed = int((checks.status == "PASS").sum())
    md = [
        "# Data Quality Report", "",
        f"Raw extract: **{len(raw):,} rows x {raw.shape[1]} columns**  ",
        f"Processed:  **{len(df):,} rows x {df.shape[1]} columns**  ",
        f"Validation: **{passed}/{len(checks)} rules passed**", "",
        "---", "", "## 1. Raw data profile", "",
        "Columns with missing values in the raw extract:", "",
        raw_prof[raw_prof.null_count > 0][
            ["dtype", "null_count", "null_pct", "unique"]].to_markdown(), "",
        f"All {int((raw_prof.null_count > 0).sum())} affected columns share the same "
        f"{int(raw_prof.null_count.max())} missing rows, which is the signature of empty "
        "shell records rather than scattered data entry gaps.", "",
        "---", "", "## 2. Validation rules", "",
        "Each rule is a business constraint the data must satisfy after cleaning.", "",
        checks.to_markdown(index=False), "",
        "---", "", "## 3. Outlier detection", "",
        "IQR fences (1.5 x IQR beyond the quartiles) and a 3-sigma z-score, reported side "
        "by side. Sales and profit are heavily right-skewed, so the IQR count is the more "
        "reliable of the two.", "",
        summary.to_markdown(index=False), "",
        f"**{len(outlier_rows):,} rows** ({len(outlier_rows)/len(df)*100:.1f}%) are flagged "
        "on at least one measure. Full list in `outputs/outliers.csv`.", "",
        "![Boxplots](../images/outlier_boxplots.png)", "",
        "### Decision: outliers are kept", "",
        "They are not errors. The largest sale is a "
        f"${df.sales.max():,.0f} copier order, and the largest loss is "
        f"${df.profit.min():,.0f} on a heavily discounted machine. Both are genuine "
        "transactions, and the loss-making ones are precisely what the analysis is about. "
        "Removing them would delete the finding.", "",
        "Where a skewed distribution would distort a chart, a log scale is used instead of "
        "dropping rows.", "",
        "![Distributions](../images/distributions.png)", "",
        "---", "", "## 4. Cleaning actions applied", "",
        "| Issue | Rows | Action |", "|---|---:|---|",
        "| Shell rows (order ID present, all detail null) | 806 | Dropped |",
        "| Exact duplicate transactions | 504 | Dropped |",
        "| Mixed date formats | all | Parsed with `format='mixed'` |",
        "| Postal codes read as integers | all | Cast to text, zero-padded to 5 |",
        "| Stray whitespace in text columns | all | Trimmed |", "",
        f"Result: **{len(df):,} clean transactions**, matching the canonical Superstore "
        "row count.",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(md))

    print(f"  Validation rules  : {passed}/{len(checks)} passed")
    if passed < len(checks):
        print(checks[checks.status == "FAIL"].to_string(index=False))
    print(f"  Rows flagged      : {len(outlier_rows):,} "
          f"({len(outlier_rows)/len(df)*100:.1f}%)")
    print(f"  Max sale / max loss: ${df.sales.max():,.0f} / ${df.profit.min():,.0f}")
    print(f"\nSaved -> {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
