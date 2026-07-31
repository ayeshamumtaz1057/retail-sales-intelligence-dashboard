# Power BI Build Guide

How to rebuild the dashboard in Power BI Desktop from this repo's cleaned data.
Follow it top to bottom and the visuals will match `images/dashboard.png`.

---

## 1. Load the data

Power BI Desktop → **Get Data** → **Text/CSV** → `data/processed/superstore_features.csv`
→ **Transform Data** and confirm these types before loading:

| Column | Type |
|---|---|
| `order_date`, `ship_date` | Date |
| `sales`, `profit`, `discount`, `profit_margin` | Decimal Number |
| `quantity`, `shipping_days`, `order_year`, `order_month` | Whole Number |
| `postal_code` | **Text** (leading zeros are lost as a number) |

Everything else is Text. Then **Close & Apply**.

> Prefer the star schema? Load `data/processed/superstore.db` instead — but SQLite needs an ODBC
> driver. The flat CSV is simpler and performs fine at 9,993 rows.

---

## 2. Create a date table

Power BI's time intelligence needs a marked date table. **Modeling → New Table**:

```dax
Date =
VAR MinDate = MIN( superstore_features[order_date] )
VAR MaxDate = MAX( superstore_features[order_date] )
RETURN
ADDCOLUMNS (
    CALENDAR ( DATE ( YEAR(MinDate), 1, 1 ), DATE ( YEAR(MaxDate), 12, 31 ) ),
    "Year",        YEAR ( [Date] ),
    "Month",       MONTH ( [Date] ),
    "Month Name",  FORMAT ( [Date], "MMM" ),
    "Quarter",     "Q" & QUARTER ( [Date] ),
    "Year Month",  FORMAT ( [Date], "YYYY-MM" ),
    "Day Name",    FORMAT ( [Date], "dddd" )
)
```

Then:

1. Select the **Date** table → **Table tools → Mark as Date Table** → `Date`.
2. Sort **Month Name** by **Month** (select the column → *Sort by Column* → `Month`),
   otherwise months render alphabetically: Apr, Aug, Dec…
3. **Model view**: drag `Date[Date]` → `superstore_features[order_date]` to build a
   one-to-many relationship (single direction).

---

## 3. Measures

Create a blank table called `_Measures` (**Enter Data** → name it → Load) and put every
measure there. It keeps the field list clean.

### Core KPIs

```dax
Total Sales = SUM ( superstore_features[sales] )

Total Profit = SUM ( superstore_features[profit] )

Profit Margin % = DIVIDE ( [Total Profit], [Total Sales], 0 )

Total Orders = DISTINCTCOUNT ( superstore_features[order_id] )

Total Customers = DISTINCTCOUNT ( superstore_features[customer_id] )

Units Sold = SUM ( superstore_features[quantity] )

Avg Order Value = DIVIDE ( [Total Sales], [Total Orders], 0 )
```

> Always `DIVIDE()` rather than `/`. It returns the third argument instead of erroring when the
> denominator is zero — which happens the moment a slicer filters everything out.

### Period-over-period (the "↑ 12.5% vs Previous Period" line)

```dax
Sales PY =
CALCULATE ( [Total Sales], SAMEPERIODLASTYEAR ( 'Date'[Date] ) )

Sales YoY % =
VAR Prev = [Sales PY]
RETURN DIVIDE ( [Total Sales] - Prev, Prev )

Profit PY =
CALCULATE ( [Total Profit], SAMEPERIODLASTYEAR ( 'Date'[Date] ) )

Profit YoY % =
VAR Prev = [Profit PY]
RETURN DIVIDE ( [Total Profit] - Prev, Prev )

Orders YoY % =
VAR Prev = CALCULATE ( [Total Orders], SAMEPERIODLASTYEAR ( 'Date'[Date] ) )
RETURN DIVIDE ( [Total Orders] - Prev, Prev )
```

### Running and ranking

```dax
Sales YTD = TOTALYTD ( [Total Sales], 'Date'[Date] )

Sales Running Total =
CALCULATE (
    [Total Sales],
    FILTER ( ALLSELECTED ( 'Date'[Date] ), 'Date'[Date] <= MAX ( 'Date'[Date] ) )
)

Product Rank =
RANKX ( ALLSELECTED ( superstore_features[product_name] ), [Total Sales],, DESC, DENSE )

Customer Rank =
RANKX ( ALLSELECTED ( superstore_features[customer_name] ), [Total Sales],, DESC, DENSE )
```

### Share-of-total (for the donut labels)

```dax
% of Total Sales =
DIVIDE ( [Total Sales], CALCULATE ( [Total Sales], ALLSELECTED ( superstore_features ) ) )
```

### Discount analysis — the insight measures

```dax
Deep Discount Loss =
CALCULATE ( [Total Profit], superstore_features[discount] > 0.30 )

Deep Discount Line Share =
DIVIDE (
    CALCULATE ( COUNTROWS ( superstore_features ), superstore_features[discount] > 0.30 ),
    COUNTROWS ( superstore_features )
)
```

### Conditional colour (red bar for loss-making months)

```dax
Profit Bar Colour =
IF ( [Total Profit] < 0, "#E03131", "#16A888" )
```

Apply it: select the column chart → **Format → Columns → Colour → fx** →
*Format style* `Field value` → *Based on field* `Profit Bar Colour`.

---

## 4. Page layout

Canvas: **View → Page view → Actual size**, custom size **1536 × 1024 px**.

| Region | Visual | Fields |
|---|---|---|
| Left rail | Buttons + shape | Page navigation |
| Header | Text box + slicers | `Date[Date]`, `region`, `category`, `segment` |
| Row 1 | 5 × **Card** | The core KPI measures |
| Row 2a | **Area chart** | Axis `Date[Year Month]`, Values `[Total Sales]` |
| Row 2b | **Donut** | Legend `category`, Values `[Total Sales]` |
| Row 2c | **Filled map** | Location `state`, Colour saturation `[Total Sales]` |
| Row 3a | **Clustered bar** | Axis `product_name`, Values `[Total Sales]`, Top-N filter 5 |
| Row 3b | **Column chart** | Axis `Date[Month Name]`, Values `[Total Profit]` |
| Row 3c | **Donut** | Legend `segment`, Values `[Total Sales]` |
| Row 4a | **Clustered bar** | Axis `customer_name`, Values `[Total Sales]`, Top-N filter 5 |
| Row 4b | **Table** | `region` + sales, profit, orders, customers, margin |
| Row 4c | **Clustered bar** | Axis `sub_category`, Values `[Total Profit]`, Top-N filter 5 |

**Top-N filter:** select the visual → *Filters* pane → the axis field → *Filter type* `Top N`
→ Show items `Top` `5` → *By value* `[Total Sales]` → **Apply filter**.

**Filled map not rendering?** *File → Options → Global → Security* → tick
**Use Map and Filled Map visuals**. Also set `state` → *Column tools → Data category* →
**State or Province** so Bing geocodes it correctly.

---

## 5. Theme

**View → Themes → Browse for themes** and load this as `theme.json`:

```json
{
  "name": "Retail Sales Intelligence",
  "dataColors": ["#2F6FED", "#16A888", "#F5B820", "#7B45C9", "#14A3C7", "#F6921E", "#E03131"],
  "background": "#EEF1F6",
  "foreground": "#1F2937",
  "tableAccent": "#2F6FED",
  "visualStyles": {
    "*": {
      "*": {
        "background": [{ "color": { "solid": { "color": "#FFFFFF" } } }],
        "border":     [{ "show": true, "radius": 8, "color": { "solid": { "color": "#E5E7EB" } } }],
        "title":      [{ "fontColor": { "solid": { "color": "#374151" } },
                         "fontSize": 11, "bold": true }]
      }
    }
  }
}
```

---

## 6. Formatting details that make it look finished

- **Cards:** Format → Callout value → Display units `Auto`, decimals `2`. Turn the category
  label off and use a separate text box, so the label sits above the number as in the design.
- **KPI delta:** a text box will not read a measure. Use a second small **Card** bound to
  `[Sales YoY %]`, format as percentage, and set conditional font colour
  (`fx` → *Rules* → `≥ 0` green `#16A34A`, `< 0` red `#E03131`).
- **Donut:** Format → Slices → Inner radius `58%`. Detail labels → `Percent of total`.
- **Table totals:** Format → Total → On, bold.
- **Turn off** every visual's shadow, and set all titles to sentence case at 11pt.

---

## 7. Publish

1. **File → Save** as `dashboard/PowerBI.pbix`.
2. **Home → Publish** → choose *My workspace* (needs a free Power BI account with a
   work or school email; personal Gmail/Outlook addresses are rejected).
3. In Power BI Service: **File → Embed report → Publish to web (public)**.

> **Publish to web is disabled on most tenants**, and it makes the report fully public.
> If it is unavailable, do this instead — it works everywhere and looks better to a reviewer:
>
> - Export a high-resolution screenshot to `images/dashboard.png`.
> - Record a 60-second walkthrough clicking through the slicers, and link it in the README.
> - Commit the `.pbix` so anyone can open it themselves.
>
> A recruiter without a Power BI licence cannot open a `.pbix` — the screenshot and video are
> what they will actually look at. The live web dashboard in `dashboard/web/` covers the
> "give me a URL" case.


---

## 9. Advanced DAX

### Month-over-month

```dax
Sales PM = CALCULATE ( [Total Sales], PREVIOUSMONTH ( 'Date'[Date] ) )

Sales MoM % =
VAR Prev = [Sales PM]
RETURN DIVIDE ( [Total Sales] - Prev, Prev )
```

### Average basket size

```dax
Avg Basket Size = DIVIDE ( [Units Sold], [Total Orders], 0 )

Avg Lines Per Order =
DIVIDE ( COUNTROWS ( superstore_features ), [Total Orders], 0 )
```

### Dynamic ranking that respects slicers

```dax
Dynamic Rank =
IF (
    ISINSCOPE ( superstore_features[product_name] ),
    RANKX ( ALLSELECTED ( superstore_features[product_name] ), [Total Sales],, DESC, DENSE )
)
```

`ISINSCOPE` stops the measure returning a meaningless rank on a total row.

### Discount exposure

```dax
Deep Discount Loss = CALCULATE ( [Total Profit], superstore_features[discount] > 0.30 )

Recoverable Profit = -1 * [Deep Discount Loss]

Loss Making Lines =
CALCULATE ( COUNTROWS ( superstore_features ), superstore_features[is_loss] = TRUE )
```

---

## 10. What-if parameter: discount cap simulator

The interactive version of the simulation on slide 8 of the deck.

1. **Modeling → New parameter → Numeric range**
   - Name `Discount Cap`, Minimum `0`, Maximum `100`, Increment `5`, Default `30`
   - Tick **Add slicer to this page**

2. Power BI generates the table and `Discount Cap Value = SELECTEDVALUE('Discount Cap'[Discount Cap])`.

3. Add the simulation measure:

```dax
Simulated Profit =
VAR Cap = [Discount Cap Value] / 100
RETURN
SUMX (
    superstore_features,
    VAR Disc      = superstore_features[discount]
    VAR Capped    = MIN ( Disc, Cap )
    VAR ListPrice = DIVIDE ( superstore_features[sales], 1 - Disc, superstore_features[sales] )
    VAR NewSales  = ListPrice * ( 1 - Capped )
    -- Cost per line is unchanged, so profit moves with the recovered revenue.
    RETURN superstore_features[profit] + ( NewSales - superstore_features[sales] )
)

Profit Uplift = [Simulated Profit] - [Total Profit]

Profit Uplift % = DIVIDE ( [Profit Uplift], [Total Profit] )
```

4. Put `[Simulated Profit]`, `[Profit Uplift]` and `[Profit Uplift %]` on cards beside the slicer.

At 30% the cards should read **$432,855** and **+51%**. If they do not, the model is wrong —
this is the fastest end-to-end check in the report.

> State the assumption on the page itself: the simulation holds volume constant, so it is an
> upper bound. A caption saying so is the difference between an analyst's report and a
> salesperson's.

---

## 11. Dynamic Top N selector

1. **Modeling → New parameter → Numeric range**: `Top N`, 3 to 25, increment 1, default 5.
2. Add the measure:

```dax
Top N Filter =
VAR N = SELECTEDVALUE ( 'Top N'[Top N], 5 )
RETURN IF ( [Dynamic Rank] <= N, 1, 0 )
```

3. On the bar chart's **Filters** pane, drag `[Top N Filter]` into *Filters on this visual*,
   set it to `is 1`, and apply. The chart now grows and shrinks with the slicer.

---

## 12. Drill-through pages

Create a page named `Product Detail`, then:

1. Drag `product_name` into **Drill through → Add drill-through fields here**.
2. Power BI adds a back button automatically — keep it.
3. Build the page: a card row for that product's sales, profit, margin and discount, a
   monthly trend line, and a table of the orders containing it.
4. On any main-page visual, right-click a bar → **Drill through → Product Detail**.

Repeat for `Customer Detail` (drill field `customer_name`) and `State Detail` (`state`).

---

## 13. Tooltip pages

1. New page → **Format → Page information → Allow use as tooltip: On**.
2. **Canvas settings → Type: Tooltip** (320 × 240 px).
3. Add two or three small visuals — a sparkline of monthly sales and a margin card work well.
4. On the target visual: **Format → Tooltips → Type: Report page →** pick the tooltip page.

Hovering a state on the map now shows its trend rather than a bare number.

---

## 14. Bookmarks and navigation

1. **View → Bookmarks → Add** for each page state you want to return to.
2. For a show/hide toggle: put both visuals in the same spot, use the **Selection** pane to
   hide one, then bookmark each arrangement.
3. **Insert → Buttons → Blank**, then **Action → Type: Bookmark** to wire them up.
4. Untick **Data** on each bookmark so it only restores layout, not filters — otherwise a
   bookmark silently resets the user's slicers, which is the commonest complaint about
   bookmark navigation.

---

## 15. Conditional formatting on KPI cards

For the red/green indicators:

1. Select the card → **Format → Callout value → Colour → fx**
2. *Format style*: `Rules`, *Based on field*: `[Sales YoY %]`
3. Rules: `>= 0` → `#16A34A`, `< 0` → `#E03131`

On the region table, use **Format → Cell elements → Data bars** on the Sales column and a
**Background colour** rule on Profit Margin (red below 10%, green above).

---

## 16. Mobile layout

**View → Mobile layout.** Drag only the five KPI cards, the sales trend, and the region table
onto the phone canvas, stacked one per row. Leave the map and donuts off — they are unreadable
at 320px wide. The mobile view is a separate arrangement of the same visuals, so no measures
need changing.

---

## 17. Executive insights page

The page that separates a portfolio project from a chart gallery. Use text boxes, not visuals,
and write findings rather than descriptions:

> **Discounting above 30% destroys $125,007 in profit** — 44% of everything the business
> earns, from 11.7% of order lines. Margin is +29.5% at full price and −119.2% above a 50%
> discount.
>
> **Furniture is 32% of revenue at a 2.5% margin.** Tables lose $17,725 and carry the deepest
> discounts in the catalogue.
>
> **Ten states operate at a loss**, every one of them discounting at 28–40% against West's
> 10.9%. Philadelphia is the fifth-largest city by revenue and loses $13,838.
>
> **Growth is real but recent**: −2.8% in 2016, then +29.5% and +20.4%.

Pair each with the single visual that proves it, and end the page with the recommendation
table from the README.

---

## 18. Checks before you call it done

- [ ] Total Sales reads **$2,296,919.49** with no slicers applied
- [ ] Total Profit reads **$286,409.08**, margin **12.47%**
- [ ] Orders **5,009**, Customers **793**
- [ ] Month axis runs Jan → Dec, not alphabetically
- [ ] Every slicer updates every visual
- [ ] The map shows 49 states, none blank
- [ ] The negative profit month renders red
- [ ] The what-if slicer at 30% shows **$432,855** simulated profit
- [ ] Drill-through works from a product bar to Product Detail
- [ ] Mobile layout has no map or donut
