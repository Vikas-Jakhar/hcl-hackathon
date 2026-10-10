# ShopSphere — Retail E-Commerce Order & Customer Analytics Platform

A bronze → silver → gold pipeline for the 7 provided source files, built in
Python + plain SQL (SQLite — no DuckDB, no external database server needed).

## 1. Setup (Windows, Anaconda)

```powershell
(base) PS C:\Users\91821\Desktop\HCL_Hackathon\hcl-hackathon> conda install pandas tabulate -y
```

That's the only dependency beyond the Python standard library (sqlite3 is built in).

Put the 7 source files in `data\raw\` exactly as given:
`customers.csv, suppliers.json, products.csv, orders.csv, order_items.csv, payments.csv, returns.csv`
(the suppliers file must be named `suppliers.json`, not `suppliers_json.txt`).

## 2. Run

```powershell
(base) PS C:\Users\91821\Desktop\HCL_Hackathon\hcl-hackathon> python run_pipeline.py
```

Every run rebuilds everything from scratch (it's idempotent — re-running never
doubles anything up). It produces:

```
data\warehouse\hackathon.db     SQLite warehouse: bronze_*, silver tables, dim_*/fact_* (gold), rules_log, rejects, row_counts
output\profiling_cleansing_report.md   Before/after counts, every rule applied, rejected-row summary
output\rules_log.csv, rejects.csv, row_counts.csv
output\kpis\*.csv                      The 8 KPIs + the margin-risk stretch goal, one CSV each
```

Two optional environment variables tune the run (defaults shown):
```powershell
$env:ASOF_DATE = "2026-10-10"      # "today"; a sign-up/order date after this is treated as invalid
$env:MIN_ORDER_DATE = "2023-01-01" # orders before this are treated as an outlier and quarantined
```

## 3. Pipeline layout

| Layer  | Where | What |
|---|---|---|
| Bronze | `bronze_*` tables | Untouched, string-typed copy of each raw file + `ingestion_log` |
| Silver | `src/clean_dimensions.py`, `src/clean_facts.py` | One function per entity; every fix is registered as a numbered rule (`rules_log`); unfixable rows go to `rejects` instead of being silently dropped |
| Gold | `src/build_gold.py` | Conformed star schema: `dim_date`, `dim_customer`, `dim_product`, `dim_supplier`, `dim_channel`, `fact_order`, `fact_order_item`, `fact_payment`, `fact_return` |
| KPI | `sql/kpis.sql` | Plain SQL (window functions: `LAG`, `RANK`) against the gold tables, run by `run_pipeline.py` |

## 4. Data model & the SCD note

Star schema, one fact per grain:
- `fact_order_item` (grain: order line) — quantity, unit price, discount, gross/net amount, refund, return flag
- `fact_order` (grain: order) — rolled-up revenue/refund/net revenue per order, for order-level KPIs
- `fact_payment` (grain: payment attempt) — for KPI 8 reconciliation
- `fact_return` (grain: return)

Every dimension has an **UNKNOWN member at surrogate key -1** (`dim_customer`,
`dim_product`, `dim_supplier`, `dim_channel`, `dim_date`), so a fact row whose
foreign key doesn't resolve (an orphan customer/product/etc.) still joins
cleanly and shows up as "Unknown" in a report instead of silently vanishing.

**`dim_customer` is SCD Type 2**: it carries `valid_from`, `valid_to`,
`is_current` columns. This run is the *first* load, so every row is
`is_current = 1` with `valid_to = NULL` — there's nothing to version yet.
On a second run with new customer data, a changed row (e.g. a different
`customer_segment`) would **not** overwrite the existing row; instead the
old row would be closed out (`valid_to` = the load date, `is_current = 0`)
and a new row inserted with a new surrogate key and `is_current = 1`. That
way a fact that happened under the *old* segment still reports against the
old segment, and `dim_customer` keeps the full history. The pipeline as
shipped implements the first load; the versioning step above is the design,
documented here rather than built, since the brief gives only one snapshot
of `customers.csv` and there's no second load to version against.

## 5. Assumptions (why the numbers are what they are)

- **Ambiguous slash dates** (`dd/mm` vs `mm/dd`, both parts ≤ 12) are read as
  **DD/MM** — this is an Indian retailer and shipping cities are all Indian
  cities; there's no cross-file signal that settles it either way, so this is
  a documented assumption, not a derived fact.
- **Orders dated before 2023-01-01** are treated as an out-of-scope outlier
  (the bulk of the data is 2024–2025) and quarantined rather than guessed at.
- **Payment timing is not checked against order timing** — the data shows no
  relationship between an order's date and its payment's date (payments can
  predate their order), so no "payment after order" rule is enforced.
- **All currency symbols (₹ / $ / "INR") are the same currency** — there's no
  FX/locale signal in the data, so amounts are treated as already comparable.
- **Revenue is recognised for `Completed` and `Returned` orders only**
  (`Pending`/`Cancelled` never count); only an **Approved** return nets a
  refund against revenue, and a return is assumed to cover its whole order
  line's quantity (there's no partial-quantity field to say otherwise).
- **KPI 2 (LTV) and KPI 7 (repeat purchase) use `Completed` orders only**, per
  the brief's own wording for those two KPIs.
- **Orphan customers/products/suppliers** (an id referenced by a fact but
  missing from its dimension file) are kept, mapped to the dimension's
  `UNKNOWN` member — the sale still counts in revenue totals, it's just
  excluded from the breakdowns that need the missing attribute (e.g. an
  order with an unknown customer still adds to `kpi1`'s revenue, but is
  excluded from `kpi2`/`kpi3`/`kpi7`, which need a real customer).
- **An order-item with no matching order, a payment with no matching order,
  or a return with no matching order-item are rejected to quarantine** —
  these can't be reconciled to anything and keeping them would misstate a
  total rather than just miss an attribute.
- **`quantity = 0` with a non-zero `line_total`, and `discount_pct` outside
  0–100%**, are treated as a corrupted input field and recomputed from
  `line_total` (treated as the authoritative amount actually charged) —
  see rules `OI-02`/`OI-03` in the rules log for the exact formula and the
  11 rows it touches.
- A **repeated `return_date` of 2023-01-01** (5 rows, all identical) is a
  placeholder, not a real date, and is set to NULL rather than counted as
  five returns genuinely happening on New Year's Day.

Every one of these is also logged as a rule in `output/rules_log.csv`
(`rationale` column), not just stated here.

## 6. Validation performed

- **Row-count identity**, per file: `raw_rows = exact_duplicates_removed +
  conflicting_duplicates_resolved + rejected_to_quarantine + silver_rows`
  (checked to hold exactly for all 7 files — see `output/row_counts.csv`).
- **Key uniqueness** in every silver/gold table on its natural/surrogate key.
- **Referential integrity**: every fact foreign key resolves to a real
  dimension row or to that dimension's `-1` UNKNOWN member — never to nothing.
- **KPI 8 is itself a validation**: it reconciles every order against its
  payment(s) and labels the anomaly type (no successful payment on a
  recognised order, a paid-but-cancelled order, multiple successful payments,
  or an amount that doesn't match — the amount mismatches are the majority
  case here, consistent with "payment timing/amount isn't tied to the order"
  above).

## 7. AI usage log

Built with Claude (Anthropic) as a pair-programming assistant for a 4-person
hackathon team. What Claude did:
- Proposed the bronze/silver/gold pipeline structure and the star schema.
- Profiled the 7 raw files (value distributions, duplicate ids, orphan
  foreign keys, date-format mix, discount/quantity anomalies) to find the
  data-quality issues listed in Section 5.
- Wrote `src/common.py`, `src/clean_dimensions.py`, `src/clean_facts.py`,
  `src/build_gold.py`, `sql/kpis.sql`, `run_pipeline.py`.
- Every rule the cleaning code applies is written into `rules_log` by the
  code itself at run time, so the rules log is generated evidence, not a
  hand-typed claim.

What the team should state in their own words for the evaluators: which
member owns which module (per the workflow doc), and any judgment call from
Section 5 the team wants to argue differently — these assumptions are
reasonable defaults, not the only defensible choice, and evaluators often
ask the team to defend exactly this kind of call.
