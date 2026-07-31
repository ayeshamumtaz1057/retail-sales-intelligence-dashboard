"""
run_all.py
----------
Runs the full pipeline in dependency order.

    python run_all.py

Each step is independent and re-runnable; nothing is cached.
"""

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

STEPS = [
    ("Cleaning raw data",            "src/clean_data.py"),
    ("Engineering features",         "src/feature_engineering.py"),
    ("Auditing data quality",        "src/data_quality.py"),
    ("Building SQLite warehouse",    "src/build_database.py"),
    ("Running SQL analysis",         "src/run_sql_analysis.py"),
    ("Building analysis notebooks",  "src/make_notebooks.py"),
    ("Exporting Excel workbook",     "src/export_excel.py"),
    ("Generating web dashboard",     "src/build_web_dashboard.py"),
]


def main() -> int:
    print("=" * 62)
    print("  RETAIL SALES INTELLIGENCE  |  full pipeline")
    print("=" * 62)
    started = time.time()

    for i, (label, script) in enumerate(STEPS, 1):
        print(f"\n[{i}/{len(STEPS)}] {label}")
        print("-" * 62)
        result = subprocess.run([sys.executable, str(ROOT / script)], cwd=ROOT)
        if result.returncode != 0:
            print(f"\nFAILED at step {i}: {script}")
            return result.returncode

    print("\n" + "=" * 62)
    print(f"  Pipeline complete in {time.time() - started:.1f}s")
    print("=" * 62)
    print("""
  Outputs
    data/cleaned/superstore_clean.csv       cleaned transactions
    data/processed/superstore_features.csv  47 columns, 26 engineered
    data/processed/customer_profile.csv     one row per customer, with RFM
    data/processed/superstore.db            SQLite star schema + 6 views
    outputs/data_quality_report.md          profiling, validation, outliers
    outputs/sql/                            one CSV per query (30)
    notebooks/01-04*.ipynb                  executed analysis notebooks
    images/                                 charts
    excel/retail_sales_analysis.xlsx        Excel workbook, live formulas
    dashboard/web/index.html                deployable dashboard

  Not in the pipeline (run separately)
    node src/make_presentation.js           executive deck
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
