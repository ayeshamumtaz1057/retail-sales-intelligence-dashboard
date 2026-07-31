# Case Study & Demo Assets

Copy-ready text for publishing the project. Replace `YOUR-USERNAME` throughout.

---

## LinkedIn post

> I analysed 9,993 retail transactions and found the company was destroying $125,007 in
> profit — 44% of everything it earned — through one policy.
>
> The pattern only showed up after banding the data.
>
> Margin by discount level:
> • No discount → +29.5%
> • 1–15% → +12.8%
> • 16–30% → +9.2%
> • 31–50% → −24.8%
> • 50%+ → −119.2%
>
> Margin doesn't decline gradually. It falls off a cliff at 30%.
>
> The correlation coefficient between discount and profit is only −0.22, which reads as a
> weak relationship. That number nearly buried the finding. Pearson measures *linear*
> association, and this isn't linear — it's a threshold. Banding the data was what exposed it.
>
> Only 11.7% of order lines sit above 30%. A single approval rule would recover most of that
> profit while touching about one order in nine.
>
> Two things I'd flag about my own analysis:
>
> 1. This is correlation. Deep discounts coincide with losses, but the data can't prove the
> discount caused it rather than both following from clearing slow stock. My recommendation
> is a 90-day pilot, not a rollout.
>
> 2. My simulation assumes every sale still closes at the lower discount. Some customers
> would walk. It's an upper bound, and I labelled it as one.
>
> What I built:
> → Python pipeline: 10,800 raw rows → 9,993 clean, 26 engineered features
> → SQL star schema with 30 analysis queries (window functions, CTEs, views)
> → Power BI dashboard with a what-if discount simulator
> → Excel workbook where every figure is a live formula
> → Totals reconciled independently across all three engines
>
> Repo: github.com/YOUR-USERNAME/retail-sales-intelligence-dashboard
>
> \#DataAnalytics #SQL #Python #PowerBI #BusinessIntelligence

**Why this structure works:** it opens with a business outcome rather than a tech stack,
shows one piece of real reasoning (the correlation trap), and volunteers two limitations.
The stack goes last, because a hiring manager scrolling a feed cares about the finding first.

Post the discount-cliff chart (`images/discount_impact.png`) as the image. It carries the
whole argument on its own.

---

## Demo video script — 2 minutes 30

Record at 1080p. Screen capture with voiceover; no webcam needed.

### 0:00–0:20 — The finding, immediately

> "This is a retail sales dashboard built on four years of transactions — $2.3 million in
> revenue, 9,993 orders. But the interesting part isn't the revenue. It's that the company
> is destroying $125,000 in profit through its discount policy, and nothing in the standard
> reporting shows it."

*On screen: the dashboard overview page.*

### 0:20–0:50 — How the data got here

> "The raw extract had 10,800 rows. 806 of them were empty shells — an order ID and nothing
> else — plus 504 exact duplicates. Cleaning those out gets to 9,993 real transactions,
> without changing a single revenue figure, because none of the dropped rows carried sales.
>
> I also found 11 rows missing postal codes, all Burlington, Vermont. Vermont ZIPs start with
> a zero, so it was stripped upstream. I left it documented rather than filling it from
> outside the dataset."

*On screen: `01_data_cleaning.ipynb`, scrolling to the validation table.*

### 0:50–1:30 — The finding

> "Here's the discount analysis. Margin holds up through a 30% discount, then collapses:
> minus 25%, then minus 119%.
>
> What almost hid this: the correlation between discount and profit is only −0.22. That
> reads as weak. But Pearson measures linear relationships, and this is a threshold effect.
> Banding the data exposed what the coefficient flattened out."

*On screen: correlation heatmap, then the discount cliff chart.*

### 1:30–2:00 — It shows up everywhere

> "The same pattern repeats across the business. Ten states operate at a loss and every one
> of them discounts between 28 and 40%, against West region's 11%. Furniture is a third of
> revenue at a 2.5% margin. And Philadelphia is the fifth-largest city by revenue while
> losing $13,800 — a revenue-only view ranks it as a success."

*On screen: the region and city charts.*

### 2:00–2:30 — The recommendation

> "The what-if slicer simulates a discount cap. At 30%, profit goes from $286,000 to
> $432,000.
>
> That's an upper bound — it assumes every sale still closes at the lower price, and some
> wouldn't. So the recommendation isn't to roll it out. It's a 90-day pilot in Central
> region, measured against the others.
>
> Everything's reproducible — one command runs the whole pipeline. Repo's in the
> description."

*On screen: the what-if slicer moving, then `python run_all.py` in a terminal.*

### Recording notes

- Do not open with "Hi, my name is…" — lead with the finding. Reviewers stop watching in
  the first fifteen seconds.
- Move the what-if slicer live on camera. Interactivity is the one thing a screenshot
  cannot show, so make it the visual climax.
- Say the limitation out loud. Most portfolio videos oversell; naming the upper bound is
  what makes the rest of the numbers believable.
- Keep it under 2:30. Upload to YouTube unlisted and link it at the top of the README.

---

## Freelance portfolio blurb

For Upwork, Fiverr, or a personal site. Around 120 words.

> **Retail Sales Intelligence Dashboard** — end-to-end analytics on 9,993 retail
> transactions, from raw extract to executive recommendation.
>
> Built a reproducible Python pipeline (cleaning, 26 engineered features, RFM segmentation),
> a SQL star schema with 30 business queries, an Excel model with live formulas, and an
> interactive Power BI dashboard including a what-if discount simulator.
>
> The analysis identified $125,007 in recoverable profit: margin holds through a 30%
> discount and collapses beyond it, a threshold effect that a correlation coefficient alone
> would have missed. The same pattern explained ten loss-making states and a 2.5%-margin
> product category.
>
> Totals were reconciled independently across Python, SQL and Excel. One command reproduces
> every output.
>
> [Live dashboard] · [GitHub repo]

---

## README screenshots to capture

| File | What to capture |
|---|---|
| `images/executive_dashboard.png` | Overview page, no filters applied |
| `images/sales_dashboard.png` | Sales analysis page with the trend and forecast |
| `images/product_dashboard.png` | Product page with the Top-N slicer visible |
| `images/customer_dashboard.png` | Customer page showing RFM segments |
| `images/regional_dashboard.png` | Regional page with the map and state table |
| `images/dashboard.png` | The single best full-page shot, for the README hero |

Use a 1920×1080 window so the images stay sharp when GitHub scales them down.
