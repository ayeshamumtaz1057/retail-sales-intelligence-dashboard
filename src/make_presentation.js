/**
 * make_presentation.js
 * --------------------
 * Builds presentation/Retail_Insights.pptx - the executive deck.
 *
 * Run:  node src/make_presentation.js
 *
 * Every figure is copied from outputs/sql/ and the notebooks. Nothing here is
 * invented; if a number changes upstream, update the FACTS block below.
 */

const pptxgen = require("pptxgenjs");
const path = require("path");
const fs = require("fs");

// ── Palette: taken from the dashboard so deck and report read as one artefact.
const NAVY = "101F4F";
const BLUE = "2F6FED";
const TEAL = "16A888";
const AMBER = "F5B820";
const PURPLE = "7B45C9";
const RED = "E03131";
const WHITE = "FFFFFF";
const INK = "1F2937";
const MUTED = "6B7280";
const LIGHT = "EEF1F6";

const HEAD = "Cambria";   // safe serif, ships with Office
const BODY = "Calibri";   // safe sans

const ROOT = path.resolve(__dirname, "..");
const OUT = path.join(ROOT, "presentation", "Retail_Insights.pptx");

// ── Every number used in the deck, in one place.
const F = {
  sales: "$2.30M", salesFull: "$2,296,919",
  profit: "$286,409", margin: "12.47%",
  orders: "5,009", customers: "793", aov: "$458.56",
  period: "Jan 2015 – Dec 2018", rows: "9,993",
  destroyed: "$125,007", deepPct: "11.7%",
  capProfit: "$432,855", capUplift: "+51%", removeUplift: "+44%",
  mape: "18.8%",
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";           // 13.3 x 7.5 in
pres.author = "Data Analytics";
pres.title = "Retail Sales Intelligence";

const W = 13.3, H = 7.5, M = 0.6;

/* ─────────────────────────────── helpers ─────────────────────────────── */

function titleSlide(slide, kicker, title, sub) {
  slide.background = { color: NAVY };
  slide.addText(kicker, {
    x: M, y: 1.55, w: W - 2 * M, h: 0.34, fontFace: BODY, fontSize: 13,
    color: AMBER, bold: true, charSpacing: 3,
  });
  slide.addText(title, {
    x: M, y: 2.0, w: W - 2 * M, h: 1.9, fontFace: HEAD, fontSize: 48,
    color: WHITE, bold: true, lineSpacing: 52,
  });
  slide.addText(sub, {
    x: M, y: 4.1, w: W - 2 * M - 1.2, h: 0.9, fontFace: BODY, fontSize: 16,
    color: "C0CBE6",
  });
}

// Section heading used on every light slide.
function heading(slide, title, sub) {
  slide.addText(title, {
    x: M, y: 0.45, w: W - 2 * M, h: 0.62, fontFace: HEAD, fontSize: 32,
    color: NAVY, bold: true, margin: 0,
  });
  if (sub) {
    slide.addText(sub, {
      x: M, y: 1.08, w: W - 2 * M, h: 0.4, fontFace: BODY, fontSize: 14,
      color: MUTED, margin: 0,
    });
  }
}

// The deck's motif: a stat in a soft rounded card. Repeated on every slide
// that carries numbers, so the deck reads as one system.
function statCard(slide, { x, y, w, h, value, label, note, accent }) {
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.09,
    fill: { color: LIGHT }, line: { color: "E1E6F0", width: 1 },
  });
  slide.addShape(pres.ShapeType.roundRect, {
    x: x + 0.3, y: y + 0.34, w: 0.1, h: 0.34, rectRadius: 0.05,
    fill: { color: accent }, line: { width: 0 },
  });
  slide.addText(value, {
    x: x + 0.52, y: y + 0.24, w: w - 0.7, h: 0.56, fontFace: HEAD,
    fontSize: 30, bold: true, color: NAVY, margin: 0,
  });
  slide.addText(label, {
    x: x + 0.52, y: y + 0.82, w: w - 0.7, h: 0.3, fontFace: BODY,
    fontSize: 12, color: INK, bold: true, margin: 0, charSpacing: 1,
  });
  if (note) {
    slide.addText(note, {
      x: x + 0.52, y: y + 1.1, w: w - 0.7, h: 0.3, fontFace: BODY,
      fontSize: 11, color: MUTED, margin: 0,
    });
  }
}

function bulletRows(slide, rows, { x, y, w, gap = 0.92 }) {
  rows.forEach((r, i) => {
    const yy = y + i * gap;
    slide.addShape(pres.ShapeType.ellipse, {
      x, y: yy + 0.04, w: 0.42, h: 0.42,
      fill: { color: r.accent }, line: { width: 0 },
    });
    slide.addText(String(i + 1), {
      x, y: yy + 0.04, w: 0.42, h: 0.42, fontFace: BODY, fontSize: 15,
      bold: true, color: WHITE, align: "center", valign: "middle", margin: 0,
    });
    slide.addText(r.head, {
      x: x + 0.62, y: yy, w: w - 0.62, h: 0.32, fontFace: BODY, fontSize: 15,
      bold: true, color: NAVY, margin: 0,
    });
    slide.addText(r.body, {
      x: x + 0.62, y: yy + 0.32, w: w - 0.62, h: 0.5, fontFace: BODY,
      fontSize: 12.5, color: MUTED, margin: 0,
    });
  });
}

function footnote(slide, text) {
  slide.addText(text, {
    x: M, y: H - 0.62, w: W - 2 * M, h: 0.3, fontFace: BODY, fontSize: 10,
    color: MUTED, italic: true, margin: 0,
  });
}

const CHART_BASE = {
  showTitle: false, showLegend: false,
  catAxisLabelColor: INK, valAxisLabelColor: MUTED,
  catAxisLabelFontFace: BODY, valAxisLabelFontFace: BODY,
  catAxisLabelFontSize: 11, valAxisLabelFontSize: 10,
  valGridLine: { color: "E5E7EB", size: 1 },
  catGridLine: { style: "none" },
  dataLabelFontFace: BODY, dataLabelFontSize: 11, dataLabelFontBold: true,
};

/* ─────────────────────────────── slides ──────────────────────────────── */

// 1 ─ Title
{
  const s = pres.addSlide();
  titleSlide(s, "RETAIL SALES INTELLIGENCE",
    "Where the profit\nis going",
    `An analysis of ${F.rows} transactions · ${F.period}`);
  s.addText(`${F.sales} revenue     ${F.profit} profit     ${F.margin} margin`, {
    x: M, y: 5.5, w: W - 2 * M, h: 0.4, fontFace: BODY, fontSize: 14,
    color: AMBER, bold: true,
  });
  s.addNotes("Four years of transactions. The headline is that the business is growing " +
    "but giving away more profit than it needs to. One policy change is worth more than " +
    "any growth initiative on the table.");
}

// 2 ─ The bottom line
{
  const s = pres.addSlide();
  heading(s, "The bottom line",
    "One finding accounts for more profit than any growth initiative under consideration.");

  s.addShape(pres.ShapeType.roundRect, {
    x: M, y: 1.75, w: W - 2 * M, h: 1.75, rectRadius: 0.12,
    fill: { color: NAVY }, line: { width: 0 },
  });
  s.addText(`Discounts above 30% destroy ${F.destroyed} in profit`, {
    x: M + 0.5, y: 2.0, w: W - 2 * M - 1, h: 0.7, fontFace: HEAD, fontSize: 30,
    bold: true, color: WHITE, margin: 0,
  });
  s.addText(`That is 44% of everything the business earns — from just ${F.deepPct} of order lines.`, {
    x: M + 0.5, y: 2.72, w: W - 2 * M - 1, h: 0.5, fontFace: BODY, fontSize: 15,
    color: "C0CBE6", margin: 0,
  });

  const cw = (W - 2 * M - 3 * 0.28) / 4;
  [
    { value: F.sales, label: "REVENUE", note: "+20.4% vs 2017", accent: BLUE },
    { value: F.profit, label: "PROFIT", note: `${F.margin} margin`, accent: TEAL },
    { value: F.orders, label: "ORDERS", note: `${F.customers} customers`, accent: AMBER },
    { value: F.destroyed, label: "PROFIT LOST", note: "to deep discounts", accent: RED },
  ].forEach((c, i) => statCard(s, {
    x: M + i * (cw + 0.28), y: 3.85, w: cw, h: 1.6, ...c,
  }));

  footnote(s, `Source: ${F.rows} cleaned transactions, ${F.period}. Figures reconciled across Python, SQL and Excel.`);
  s.addNotes("Lead with the number. The rest of the deck is evidence for this slide.");
}

// 3 ─ The discount cliff
{
  const s = pres.addSlide();
  heading(s, "Margin does not decline. It falls off a cliff.",
    "Profit margin by discount band — the threshold sits at 30%.");

  s.addChart(pres.ChartType.bar, [{
    name: "Margin %",
    labels: ["No discount", "1–15%", "16–30%", "31–50%", "50%+"],
    values: [29.5, 12.8, 9.2, -24.8, -119.2],
  }], {
    ...CHART_BASE, x: M, y: 1.65, w: 7.5, h: 4.5,
    barDir: "col", barGrouping: "clustered",
    chartColors: [TEAL, TEAL, TEAL, RED, RED],
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: '0.0"%"',
    valAxisMaxVal: 60, valAxisMinVal: -140,
    valAxisLabelFormatCode: '0"%"', barGapWidthPct: 55,
  });

  s.addText("Everything up to 30% is a\nnormal commercial trade-off.", {
    x: 8.4, y: 2.0, w: 4.2, h: 0.8, fontFace: BODY, fontSize: 14,
    color: INK, margin: 0,
  });
  statCard(s, {
    x: 8.4, y: 3.0, w: 4.2, h: 1.5, value: "−119%", label: "MARGIN ABOVE 50% OFF",
    note: "Each sale costs more than it earns", accent: RED,
  });
  s.addText("Only 11.7% of order lines sit past the\nthreshold — a narrow, fixable problem.", {
    x: 8.4, y: 4.75, w: 4.2, h: 0.8, fontFace: BODY, fontSize: 14,
    color: INK, margin: 0,
  });

  footnote(s, "Query 14, analysis_queries.sql. Bands cut at 0 / 15 / 30 / 50 per cent.");
  s.addNotes("The key point: this is a threshold, not a gradient. A single approval rule " +
    "at 30% captures nearly all of the value.");
}

// 4 ─ Furniture
{
  const s = pres.addSlide();
  heading(s, "Furniture is a third of revenue and none of the profit",
    "Share of sales against realised margin, by category.");

  s.addChart(pres.ChartType.bar, [
    { name: "Share of sales %", labels: ["Technology", "Furniture", "Office Supplies"],
      values: [36.4, 32.3, 31.3] },
    { name: "Profit margin %", labels: ["Technology", "Furniture", "Office Supplies"],
      values: [17.4, 2.5, 17.0] },
  ], {
    ...CHART_BASE, x: M, y: 1.7, w: 7.4, h: 4.3,
    barDir: "col", barGrouping: "clustered",
    chartColors: [BLUE, TEAL],
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: '0.0"%"',
    showLegend: true, legendPos: "b", legendFontFace: BODY, legendFontSize: 11,
    valAxisMaxVal: 45, barGapWidthPct: 60,
  });

  s.addText("Two sub-categories lose money outright", {
    x: 8.3, y: 1.75, w: 4.4, h: 0.4, fontFace: BODY, fontSize: 14,
    bold: true, color: NAVY, margin: 0,
  });
  statCard(s, { x: 8.3, y: 2.25, w: 4.4, h: 1.45, value: "−$17,725",
    label: "TABLES", note: "26% average discount — deepest in catalogue", accent: RED });
  statCard(s, { x: 8.3, y: 3.85, w: 4.4, h: 1.45, value: "−$3,473",
    label: "BOOKCASES", note: "21% average discount", accent: RED });
  s.addText("Same root cause as slide 3.", {
    x: 8.3, y: 5.45, w: 4.4, h: 0.4, fontFace: BODY, fontSize: 13,
    italic: true, color: MUTED, margin: 0,
  });

  footnote(s, "Queries 6 and 7, analysis_queries.sql.");
  s.addNotes("Furniture is not a bad business - it is a badly priced one. The discount " +
    "depth explains the margin gap almost entirely.");
}

// 5 ─ Geography
{
  const s = pres.addSlide();
  heading(s, "The geography of the problem is the same problem",
    "Every loss-making region and state discounts far harder than the profitable ones.");

  s.addChart(pres.ChartType.bar, [
    { name: "Avg discount %", labels: ["West", "East", "South", "Central"],
      values: [10.9, 14.5, 14.7, 24.0] },
    { name: "Profit margin %", labels: ["West", "East", "South", "Central"],
      values: [14.94, 13.49, 11.93, 7.92] },
  ], {
    ...CHART_BASE, x: M, y: 1.7, w: 7.4, h: 4.3,
    barDir: "col", barGrouping: "clustered",
    chartColors: [AMBER, TEAL],
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: '0.0"%"',
    showLegend: true, legendPos: "b", legendFontFace: BODY, legendFontSize: 11,
    valAxisMaxVal: 32, barGapWidthPct: 60,
  });

  bulletRows(s, [
    { head: "Central discounts twice as hard as West",
      body: "24.0% vs 10.9% — and earns half the margin.", accent: AMBER },
    { head: "10 states operate at a loss",
      body: "All discount between 28% and 40%.", accent: RED },
    { head: "Philadelphia is 5th by revenue and loses $13,838",
      body: "Revenue rank and profit contribution are not the same thing.", accent: PURPLE },
  ], { x: 8.3, y: 1.85, w: 4.4, gap: 1.28 });

  footnote(s, "Queries 11, 24 and 25, analysis_queries.sql.");
  s.addNotes("Philadelphia is the slide that lands with a sales leader - a city everyone " +
    "considers a success is destroying value.");
}

// 6 ─ Growth
{
  const s = pres.addSlide();
  heading(s, "The business is growing — that is not the issue",
    "Annual revenue, with margin improving every year.");

  s.addChart(pres.ChartType.bar, [{
    name: "Sales", labels: ["2015", "2016", "2017", "2018"],
    values: [483966, 470533, 609206, 733215],
  }], {
    ...CHART_BASE, x: M, y: 1.7, w: 7.4, h: 4.3,
    barDir: "col", chartColors: [BLUE],
    showValue: true, dataLabelPosition: "outEnd",
    dataLabelFormatCode: '$#,##0,"K"', barGapWidthPct: 55,
    valAxisLabelFormatCode: '$#,##0,"K"',
  });

  const cw2 = 4.4;
  statCard(s, { x: 8.3, y: 1.85, w: cw2, h: 1.45, value: "+20.4%",
    label: "2018 GROWTH", note: "after +29.5% in 2017", accent: TEAL });
  statCard(s, { x: 8.3, y: 3.45, w: cw2, h: 1.45, value: "10.2% → 12.7%",
    label: "MARGIN, 2015 TO 2018", note: "improving, but well below potential", accent: BLUE });
  s.addText("Growth is not being bought with discounts\nin aggregate — the damage is concentrated\nin a narrow band of deep discounts.", {
    x: 8.3, y: 5.05, w: cw2, h: 1.0, fontFace: BODY, fontSize: 12.5,
    color: MUTED, margin: 0,
  });

  footnote(s, "Query 3, analysis_queries.sql. 2016 declined 2.8% before recovery.");
}

// 7 ─ Customers
{
  const s = pres.addSlide();
  heading(s, "Where the customer value sits",
    "RFM segmentation of all 793 customers by recency, frequency and monetary value.");

  s.addChart(pres.ChartType.bar, [
    { name: "% of customers", labels: ["Champion", "Loyal", "Potential", "At Risk"],
      values: [15.6, 32.0, 27.6, 24.7] },
    { name: "% of revenue", labels: ["Champion", "Loyal", "Potential", "At Risk"],
      values: [28.2, 42.8, 20.6, 8.4] },
  ], {
    ...CHART_BASE, x: M, y: 1.75, w: 7.4, h: 4.2,
    barDir: "col", barGrouping: "clustered",
    chartColors: [PURPLE, TEAL],
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: '0.0"%"',
    showLegend: true, legendPos: "b", legendFontFace: BODY, legendFontSize: 11,
    valAxisMaxVal: 55, barGapWidthPct: 60,
  });

  bulletRows(s, [
    { head: "Champions and Loyal are 71% of revenue",
      body: "378 accounts. This is the retention list.", accent: TEAL },
    { head: "At Risk is 197 customers, 8.4% of revenue",
      body: "Average 329 days since last order — automate, don't staff it.", accent: RED },
    { head: "Top 20% produce 48% of revenue",
      body: "Real concentration, but not the 80/20 usually assumed.", accent: BLUE },
  ], { x: 8.3, y: 1.9, w: 4.4, gap: 1.28 });

  footnote(s, "Query 22, analysis_queries.sql. RFM scored 1–5 per dimension.");
  s.addNotes("The last point matters: a pure key-account strategy would leave more than " +
    "half the revenue unmanaged.");
}

// 8 ─ What it is worth
{
  const s = pres.addSlide();
  heading(s, "What a discount cap is worth",
    "Simulated total profit at each maximum discount level.");

  s.addChart(pres.ChartType.line, [{
    name: "Simulated profit",
    labels: ["No cap", "70%", "50%", "40%", "30%", "20%", "10%"],
    values: [286409, 294891, 340596, 376562, 432855, 505560, 675460],
  }], {
    ...CHART_BASE, x: M, y: 1.7, w: 7.4, h: 4.3,
    chartColors: [PURPLE], lineSize: 3, lineSmooth: false,
    showValue: true, dataLabelPosition: "t", dataLabelFormatCode: '$#,##0,"K"',
    valAxisLabelFormatCode: '$#,##0,"K"',
    valAxisMinVal: 200000, valAxisMaxVal: 750000,
  });

  statCard(s, { x: 8.3, y: 1.85, w: 4.4, h: 1.6, value: F.capProfit,
    label: "PROFIT AT A 30% CAP", note: `${F.capUplift} against today`, accent: TEAL });
  s.addText("Why 30% and not lower", {
    x: 8.3, y: 3.65, w: 4.4, h: 0.35, fontFace: BODY, fontSize: 14,
    bold: true, color: NAVY, margin: 0,
  });
  s.addText([
    { text: "The curve flattens at 30%. Tightening further returns less per order affected while touching far more of the book.", options: { bullet: true, breakLine: true } },
    { text: "A 30% rule affects one line in nine. A 20% rule affects nearly half.", options: { bullet: true } },
  ], {
    x: 8.3, y: 4.05, w: 4.4, h: 1.6, fontFace: BODY, fontSize: 12.5,
    color: INK, paraSpaceAfter: 8, margin: 0,
  });

  footnote(s, "Upper bound: assumes each sale still closes at the lower discount. Some would not — see method.");
  s.addNotes("Be explicit that this is an upper bound. The pilot on slide 9 is what " +
    "converts the estimate into a real number.");
}

// 9 ─ Recommendations
{
  const s = pres.addSlide();
  heading(s, "Recommendations",
    "Ordered by value against effort. The first one carries most of the benefit.");

  bulletRows(s, [
    { head: "Require approval for any discount above 30%",
      body: `Worth ${F.removeUplift} to ${F.capUplift} of profit. Affects 11.7% of order lines. Pilot in Central first.`, accent: RED },
    { head: "Reprice or discontinue Tables and Bookcases",
      body: "Removes a $21K annual loss. Tables carry the deepest discounts in the catalogue.", accent: AMBER },
    { head: "Audit pricing authority in Central region",
      body: "24.0% average discount against West's 10.9%, for half the margin.", accent: PURPLE },
    { head: "Review the 10 loss-making states and Philadelphia",
      body: "Philadelphia is 5th by revenue and loses $13,838. Revenue rank is hiding it.", accent: BLUE },
    { head: "Weight inventory and campaign spend to Sep–Dec",
      body: "November and December peak in all four years; January and February trail.", accent: TEAL },
  ], { x: M, y: 1.7, w: 8.2, gap: 1.05 });

  statCard(s, { x: 9.2, y: 1.9, w: 3.5, h: 1.7, value: F.destroyed,
    label: "AT STAKE", note: "recoverable profit", accent: RED });
  statCard(s, { x: 9.2, y: 3.8, w: 3.5, h: 1.7, value: "1 in 9",
    label: "ORDER LINES AFFECTED", note: "by the 30% rule", accent: TEAL });

  s.addNotes("If the meeting only gets through one slide, make it this one.");
}

// 10 ─ Method and limits
{
  const s = pres.addSlide();
  heading(s, "Method and limitations",
    "What was done, and what these numbers cannot tell you.");

  s.addText("How it was built", {
    x: M, y: 1.6, w: 5.9, h: 0.35, fontFace: BODY, fontSize: 15,
    bold: true, color: NAVY, margin: 0,
  });
  s.addText([
    { text: "10,800 raw rows cleaned to 9,993: removed 806 empty records and 504 duplicates.", options: { bullet: true, breakLine: true } },
    { text: "26 engineered features; star schema in SQL with 30 analysis queries.", options: { bullet: true, breakLine: true } },
    { text: "Totals reconciled independently across Python, SQL and Excel.", options: { bullet: true, breakLine: true } },
    { text: "15 of 15 automated validation rules pass.", options: { bullet: true } },
  ], {
    x: M, y: 2.0, w: 5.9, h: 2.4, fontFace: BODY, fontSize: 13,
    color: INK, paraSpaceAfter: 10, margin: 0,
  });

  s.addText("What it cannot tell you", {
    x: 7.0, y: 1.6, w: 5.7, h: 0.35, fontFace: BODY, fontSize: 15,
    bold: true, color: NAVY, margin: 0,
  });
  s.addText([
    { text: "Correlation, not causation. Deep discounts coincide with losses; the data cannot prove the discount caused it rather than both following from clearing slow stock.", options: { bullet: true, breakLine: true } },
    { text: "The cap simulation assumes every sale still closes at the lower discount. Some customers would walk, so treat it as an upper bound.", options: { bullet: true, breakLine: true } },
    { text: "No COGS column, so margin uses the supplied profit figure at face value.", options: { bullet: true, breakLine: true } },
    { text: `The 3-month forecast has ${F.mape} backtest error — usable for direction, not for committing budget.`, options: { bullet: true } },
  ], {
    x: 7.0, y: 2.0, w: 5.7, h: 3.4, fontFace: BODY, fontSize: 13,
    color: INK, paraSpaceAfter: 10, margin: 0,
  });

  s.addShape(pres.ShapeType.roundRect, {
    x: M, y: 5.55, w: W - 2 * M, h: 1.0, rectRadius: 0.1,
    fill: { color: LIGHT }, line: { color: "E1E6F0", width: 1 },
  });
  s.addText("Recommended next step: run the 30% cap as a 90-day pilot in Central region and measure realised margin against the control regions. That converts an estimate into a decision.", {
    x: M + 0.35, y: 5.72, w: W - 2 * M - 0.7, h: 0.7, fontFace: BODY,
    fontSize: 13.5, color: INK, margin: 0,
  });

  s.addNotes("Volunteering the limitations is what makes the rest of the numbers " +
    "credible. Never present the simulation as a promise.");
}

// 11 ─ Close
{
  const s = pres.addSlide();
  titleSlide(s, "IN ONE LINE",
    "The business does not\nhave a growth problem.",
    "It has a discounting problem — and it is worth $125,007 a year to fix.");
  s.addText("Full analysis, SQL and reproducible pipeline: github.com/YOUR-USERNAME/retail-sales-intelligence-dashboard", {
    x: M, y: 6.3, w: W - 2 * M, h: 0.4, fontFace: BODY, fontSize: 12,
    color: "8FA0C8",
  });
  s.addNotes("Close on the reframe. Growth is fine; the leak is the story.");
}

fs.mkdirSync(path.dirname(OUT), { recursive: true });
pres.writeFile({ fileName: OUT }).then(() => {
  console.log(`Saved -> ${path.relative(ROOT, OUT)}  (11 slides)`);
});
