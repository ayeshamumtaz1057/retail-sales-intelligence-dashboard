"""
build_web_dashboard.py
----------------------
Generates dashboard/web/index.html - a deployable static dashboard whose numbers
are computed from data/cleaned/superstore_clean.csv, not hardcoded.

Run:  python src/build_web_dashboard.py
"""

from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "processed" / "superstore_features.csv"
TEMPLATE = ROOT / "src" / "templates" / "dashboard.html"
OUT = ROOT / "dashboard" / "web" / "index.html"

STATE_ABBR = {
    'Alabama':'AL','Arizona':'AZ','Arkansas':'AR','California':'CA','Colorado':'CO',
    'Connecticut':'CT','Delaware':'DE','District of Columbia':'DC','Florida':'FL',
    'Georgia':'GA','Idaho':'ID','Illinois':'IL','Indiana':'IN','Iowa':'IA','Kansas':'KS',
    'Kentucky':'KY','Louisiana':'LA','Maine':'ME','Maryland':'MD','Massachusetts':'MA',
    'Michigan':'MI','Minnesota':'MN','Mississippi':'MS','Missouri':'MO','Montana':'MT',
    'Nebraska':'NE','Nevada':'NV','New Hampshire':'NH','New Jersey':'NJ','New Mexico':'NM',
    'New York':'NY','North Carolina':'NC','North Dakota':'ND','Ohio':'OH','Oklahoma':'OK',
    'Oregon':'OR','Pennsylvania':'PA','Rhode Island':'RI','South Carolina':'SC',
    'South Dakota':'SD','Tennessee':'TN','Texas':'TX','Utah':'UT','Vermont':'VT',
    'Virginia':'VA','Washington':'WA','West Virginia':'WV','Wisconsin':'WI','Wyoming':'WY',
}
MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]


def pct_change(cur: float, prev: float) -> float:
    return round((cur - prev) / prev * 100, 1) if prev else 0.0


def build_payload(df: pd.DataFrame) -> dict:
    orders = df.order_id.nunique()
    years = sorted(df.order_year.unique())
    cur_y, prev_y = years[-1], years[-2]
    cur, prev = df[df.order_year == cur_y], df[df.order_year == prev_y]

    def kpi_delta(frame_cur, frame_prev, how):
        return pct_change(how(frame_cur), how(frame_prev))

    # Calendar-month totals across all four years (matches the design's Jan-Dec axis).
    by_month = df.groupby("order_month").agg(sales=("sales","sum"), profit=("profit","sum"))
    by_month = by_month.reindex(range(1, 13), fill_value=0)

    cat = (df.groupby("category")["sales"].sum().sort_values(ascending=False))
    seg = (df.groupby("segment")["sales"].sum().sort_values(ascending=False))

    prod = (df.groupby("product_name")["sales"].sum().nlargest(5))
    cust = (df.groupby("customer_name")["sales"].sum().nlargest(5))
    subc = (df.groupby("sub_category")["profit"].sum().nlargest(5))

    region = (df.groupby("region")
                .agg(sales=("sales","sum"), profit=("profit","sum"),
                     orders=("order_id","nunique"), customers=("customer_id","nunique"))
                .sort_values("sales", ascending=False))
    region["margin"] = region.profit / region.sales * 100

    states = (df.groupby("state")["sales"].sum())
    states.index = states.index.map(STATE_ABBR)
    states = states[states.index.notna()]

    total_sales, total_profit = df.sales.sum(), df.profit.sum()

    return {
        "asOf": df.order_date.max().strftime("%B %d, %Y"),
        "kpis": [
            {"label": "Total Sales",     "value": f"${total_sales/1e6:.2f}M",
             "delta": kpi_delta(cur, prev, lambda d: d.sales.sum())},
            {"label": "Total Profit",    "value": f"${total_profit/1e3:.2f}K",
             "delta": kpi_delta(cur, prev, lambda d: d.profit.sum())},
            {"label": "Total Orders",    "value": f"{orders:,}",
             "delta": kpi_delta(cur, prev, lambda d: d.order_id.nunique())},
            {"label": "Total Customers", "value": f"{df.customer_id.nunique():,}",
             "delta": kpi_delta(cur, prev, lambda d: d.customer_id.nunique())},
            {"label": "Avg Order Value", "value": f"${total_sales/orders:,.2f}",
             "delta": kpi_delta(cur, prev,
                                lambda d: d.sales.sum() / d.order_id.nunique())},
        ],
        "months": MONTHS,
        "salesByMonth":  [round(v, 2) for v in by_month.sales],
        "profitByMonth": [round(v, 2) for v in by_month.profit],
        "category": {"labels": cat.index.tolist(),
                     "values": [round(v/cat.sum()*100, 1) for v in cat]},
        "segment":  {"labels": seg.index.tolist(),
                     "values": [round(v/seg.sum()*100, 1) for v in seg]},
        "topProducts":  [[k, round(v, 2)] for k, v in prod.items()],
        "topCustomers": [[k, round(v, 2)] for k, v in cust.items()],
        "subCategory":  [[k, round(v, 2)] for k, v in subc.items()],
        "regions": [[i, round(r.sales, 2), round(r.profit, 2), int(r.orders),
                     int(r.customers), round(r.margin, 2)] for i, r in region.iterrows()],
        "totals": ["Total", f"${total_sales/1e6:.2f}M", f"${total_profit/1e3:.2f}K",
                   f"{orders:,}", f"{df.customer_id.nunique():,}",
                   f"{total_profit/total_sales*100:.2f}%"],
        "states": {k: round(v, 2) for k, v in states.items()},
        "totalSalesLabel": f"${total_sales/1e6:.2f}M",
    }


def main() -> None:
    df = pd.read_csv(CLEAN, parse_dates=["order_date"], dtype={"postal_code": str})
    payload = build_payload(df)

    html = TEMPLATE.read_text().replace(
        "/*__DATA__*/", json.dumps(payload, indent=2))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html)
    print(f"Saved -> {OUT.relative_to(ROOT)}")
    print(f"  KPIs        : {', '.join(k['value'] for k in payload['kpis'])}")
    print(f"  Categories  : {payload['category']['labels']}")
    print(f"  States mapped: {len(payload['states'])}")


if __name__ == "__main__":
    main()
