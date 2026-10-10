# ShopSphere --- Retail E-Commerce Order & Customer Analytics Platform

A data engineering case study that transforms seven raw retail source
files into a curated analytics model and produces eight business KPIs
plus an optional margin-risk report.

> **Current implementation status:** The supplied project code runs a
> local Python/SQLite pipeline. The team has created the Azure
> Databricks workspace `dbw-shopsphere`, uploaded the source files to
> Azure Storage, and enabled a managed identity on an Access Connector.
> The end-to-end Databricks-to-Storage read/write test and cloud
> pipeline deployment are still pending. Do not describe the pipeline as
> deployed to Databricks until that test succeeds.

## Table of contents

-   [Business objective](#business-objective)
-   [Source data](#source-data)
-   [Architecture](#architecture)
-   [Repository structure](#repository-structure)
-   [Team responsibilities](#team-responsibilities)
-   [Run the current local pipeline](#run-the-current-local-pipeline)
-   [Data model](#data-model)
-   [KPIs](#kpis)
-   [Data-quality approach and
    assumptions](#data-quality-approach-and-assumptions)
-   [Validation](#validation)
-   [Azure Databricks implementation
    plan](#azure-databricks-implementation-plan)
-   [Outputs](#outputs)
-   [AI usage log](#ai-usage-log)

## Business objective

ShopSphere's operational data comes from e-commerce, CRM, payment, and
procurement systems. The source extracts contain data-quality issues
such as duplicates, missing values, inconsistent formats,
referential-integrity gaps, and conflicting records.

The goal is to profile and cleanse the data, model it for analytics, and
calculate reliable metrics for finance, marketing, and supply-chain
teams.

## Source data

Place the seven source files in `data/raw/` for the local pipeline:

  File                Contents                         Approximate rows
  ------------------- ------------------------------ ------------------
  `customers.csv`     Customer/CRM records                          163
  `suppliers.json`    Supplier/procurement records                   19
  `products.csv`      Product catalog                                75
  `orders.csv`        Order headers                                 323
  `order_items.csv`   Order line items                              800
  `payments.csv`      Payment transactions                          330
  `returns.csv`       Returns and refunds                            68

The supplier file must be named `suppliers.json` when running the
included local pipeline. Keep raw source files unchanged; apply
corrections in the transformation layer and log the decisions.

## Architecture

### Intended lakehouse layout

``` text
Azure Data Lake Storage Gen2
└── data/
    ├── bronze/   # original source files
    ├── silver/   # validated and cleansed entities
    └── gold/     # dimensional model and KPI-ready outputs

Azure Databricks
├── PySpark transformations
├── SQL KPI calculations
├── validation and reconciliation
└── scheduled workflow (after deployment)
```

-   **Bronze:** preserve source extracts for traceability.
-   **Silver:** standardize formats, resolve duplicates, validate keys,
    and quarantine records that cannot be safely repaired.
-   **Gold:** publish dimensions, facts, and KPI outputs for analytics.

The current code in this ZIP implements the pipeline locally using
Python and SQLite. The Azure layout above is the target deployment
architecture, not a claim that cloud execution is already complete.

## Repository structure

``` text
hcl-hackathon/
├── data/
│   └── raw/                      # seven source files (local run)
├── src/
│   ├── common.py                 # shared helpers and logging
│   ├── clean_dimensions.py       # dimension cleansing
│   ├── clean_facts.py            # fact cleansing
│   ├── build_gold.py             # dimensional model
│   └── run_pipeline.py           # pipeline orchestration
├── sql/
│   └── kpis.sql                  # KPI queries
├── output/
│   ├── profiling_cleansing_report.md
│   ├── row_counts.csv
│   ├── rules_log.csv
│   ├── rejects.csv
│   └── kpis/                     # KPI CSV outputs
├── run_pipeline.py               # root entry point
└── README.md
```

The local pipeline creates `data/warehouse/hackathon.db` when it runs.

## Team responsibilities

  -----------------------------------------------------------------------
  Role                    Main responsibilities   Suggested deliverables
  ----------------------- ----------------------- -----------------------
  Cloud and integration   Azure setup, secure     Cloud connection test,
  lead                    storage access,         orchestration,
                          repository integration, deployment notes, final
                          pipeline orchestration, README
                          end-to-end tests and    
                          submission              

  Member 1 --- Profiling  Profile all seven       Profiling report,
  and cleansing           files, define quality   cleansing code, rules
                          rules, document         log
                          corrections and         
                          quarantined records     

  Member 2 ---            Design star schema,     DDL/model diagram,
  Dimensional modeling    facts/dimensions,       modeling code,
                          surrogate keys, and     data-model notes
                          customer SCD Type 2     
                          approach                

  Member 3 --- KPI        Implement and test all  SQL/PySpark KPI logic,
  analytics               eight KPIs and prepare  tests, KPI
                          dashboard-ready outputs CSVs/dashboard
  -----------------------------------------------------------------------

Agree on table names, column names, and grain before integrating
modules. Use Git branches and pull requests to avoid overwriting one
another's work.

## Run the current local pipeline

### Requirements

-   Python 3.10+ recommended
-   `pandas`
-   `tabulate`
-   SQLite is included with Python

Install the dependencies:

``` powershell
python -m pip install pandas tabulate
```

Ensure the seven files are present in `data/raw/`, then run from the
repository root:

``` powershell
python run_pipeline.py
```

The pipeline rebuilds the local warehouse and outputs on each run. It is
intended to be repeatable; review the logs and row counts after each
execution.

Optional environment variables:

``` powershell
$env:ASOF_DATE = "2026-10-10"
$env:MIN_ORDER_DATE = "2023-01-01"
python run_pipeline.py
```

-   `ASOF_DATE`: reference date for validating future-dated records.
-   `MIN_ORDER_DATE`: lower date boundary for flagging/quarantining old
    order dates.

Use a date appropriate to the evaluation run when changing `ASOF_DATE`.

## Data model

The current local implementation builds a star schema with:

-   `dim_date`
-   `dim_customer`
-   `dim_product`
-   `dim_supplier`
-   `dim_channel`
-   `fact_order`
-   `fact_order_item`
-   `fact_payment`
-   `fact_return`

### Fact-table grain

  Table               Grain
  ------------------- -----------------------------------------
  `fact_order`        One row per order
  `fact_order_item`   One row per order line
  `fact_payment`      One row per payment transaction/attempt
  `fact_return`       One row per return record

Dimensions include an `UNKNOWN` member with surrogate key `-1` so
orphaned references can remain visible without silently disappearing
from reports.

### Customer SCD Type 2

The customer dimension is designed with `valid_from`, `valid_to`, and
`is_current` columns. The supplied implementation supports the initial
snapshot; it documents the SCD Type 2 approach, but a subsequent-load
change-detection/version-insertion process is not implemented in the
provided first-load pipeline. If incremental snapshots are added, close
the old row and insert a new surrogate-key row when tracked attributes
change.

## KPIs

The pipeline produces CSV outputs for all eight required KPIs:

1.  **Net revenue by product category and month** --- line revenue after
    discount less approved refunds.
2.  **Top 10 customers by net lifetime value** --- completed-order spend
    net of returns.
3.  **Customer segment profile** --- standardized segment counts and
    average order value.
4.  **Month-over-month orders and revenue by channel** --- order-volume
    and revenue growth by Web/App/Store.
5.  **Top/bottom product return rates** --- returned quantity divided by
    ordered quantity, with a minimum-volume threshold.
6.  **Supplier performance scorecard** --- revenue contribution, product
    return performance, and normalized supplier rating.
7.  **90-day repeat-purchase rate** --- customers with another completed
    order within 90 days of their first completed order.
8.  **Payment reconciliation and anomalies** --- compare payment totals
    with computed order totals; flag mismatches, duplicate/conflicting
    payments, and missing successful payments.

**Optional stretch KPI:** margin-risk report for products where cost
exceeds the effective selling price after discount.

Review the SQL and output definitions before presenting results. State
the inclusion rules, denominator, thresholds, and treatment of ambiguous
records in the final report.

## Data-quality approach and assumptions

The local README and generated `output/profiling_cleansing_report.md`
document the current implementation's detailed decisions. Important
assumptions include:

-   Ambiguous slash-formatted dates are interpreted as DD/MM where the
    code's rule applies.
-   Orders before `MIN_ORDER_DATE` are treated as outliers and
    quarantined.
-   Currency symbols are treated as comparable amounts because no
    reliable exchange-rate metadata is supplied.
-   Revenue is recognized for `Completed` and `Returned` orders;
    pending/cancelled orders do not contribute to revenue.
-   Only approved returns reduce revenue.
-   Orphan customer/product/supplier references map to an `UNKNOWN`
    dimension member; records that cannot be reconciled to a parent
    order/order item are quarantined.
-   Invalid quantity/discount combinations are handled according to the
    specific rules recorded by the pipeline; inspect
    `output/rules_log.csv` and the cleansing report before changing
    these decisions.
-   Supplier rating values require normalization before combining them
    in a scorecard. The chosen normalization and score weights must be
    explained in the KPI documentation.

These are documented implementation assumptions, not universal business
rules. Confirm them with the team and defend them during evaluation.

## Validation

Before accepting a run, check:

-   Raw, deduplicated, rejected, and silver row counts reconcile for
    each source.
-   Natural keys are unique where required.
-   Fact foreign keys resolve to a dimension row or the `UNKNOWN`
    member.
-   Rejected records have a reason in `output/rejects.csv`.
-   Applied cleansing rules are recorded in `output/rules_log.csv`.
-   KPI outputs are checked against hand-calculated examples and
    join-grain checks.
-   Payment reconciliation flags match the documented order-total and
    payment-status rules.
-   Rerunning the pipeline does not duplicate prior output rows.

Do not report validation as complete unless the current run's outputs
support it.

## Azure Databricks implementation plan

The Azure resources created for this project are:

-   Databricks workspace: `dbw-shopsphere`
-   Storage account: `stshopsphere26abc`
-   Source container: `data`, with raw files under `bronze/`
-   Access Connector: `unity-catalog-access-connector` (system-assigned
    managed identity enabled)

A role assignment has been made for the connector, but the end-to-end
storage connection must still be tested. Complete these steps before
calling the cloud deployment ready:

1.  Confirm the connector's `Storage Blob Data Contributor` role
    assignment at the intended storage scope.
2.  Configure or verify the Unity Catalog storage credential and
    external location that use this connector.
3.  Test listing
    `abfss://data@stshopsphere26abc.dfs.core.windows.net/bronze/` from
    Databricks.
4.  Read a source file and compare its schema/row count with the local
    pipeline.
5.  Write a small test output to a controlled `silver` or test path and
    read it back.
6.  Port/adapt the local SQLite-specific orchestration and SQL to
    Databricks/PySpark/Delta as required; SQLite SQL should not be
    assumed to run unchanged on Spark.
7.  Run the full pipeline, validate all eight KPIs, and capture run
    instructions and screenshots/logs for the submission.
8.  Configure a Databricks Workflow only after manual execution
    succeeds.

Never commit storage keys, tokens, passwords, or other secrets to GitHub
or notebooks. Prefer managed identity/Unity Catalog and secret scopes
where appropriate. Do not make the storage container public to simplify
access.

## Outputs

After a successful local run, expected outputs include:

``` text
data/warehouse/hackathon.db
output/profiling_cleansing_report.md
output/row_counts.csv
output/rules_log.csv
output/rejects.csv
output/kpis/
├── kpi1_revenue_by_category_month.csv
├── kpi2_top10_customers_by_net_ltv.csv
├── kpi3_segment_profile.csv
├── kpi4_mom_growth_by_channel.csv
├── kpi5_product_return_rate.csv
├── kpi6_supplier_scorecard.csv
├── kpi7_90day_repeat_purchase_rate.csv
├── kpi8_payment_reconciliation.csv
└── stretch_margin_risk.csv
```

The actual output set depends on a successful pipeline run. Commit
documentation and code, but avoid committing raw data or generated
database files to a public repository unless permitted by the assessment
rules.

## AI usage log

The assessment asks for the AI tools used, representative prompts, and
evidence of validation. Fill in this section truthfully based on the
team's actual work.

  -----------------------------------------------------------------------
  Tool                    Representative prompt   How output was
                                                  validated
  ----------------------- ----------------------- -----------------------
  ChatGPT / other         "Profile the source     Compare suggested
  assistant (fill in      files and identify      issues with actual
  actual tool used)       duplicate keys, missing profiling output and
                          values, inconsistent    inspect edge cases.
                          formats, and            
                          referential-integrity   
                          gaps."                  

  ChatGPT / coding        "Review the KPI SQL for Hand-calculate sample
  assistant (fill in      correct grain,          orders and compare SQL
  actual tool used)       return/refund           outputs; inspect joins
                          treatment, and payment  for double-counting.
                          reconciliation."        

  ChatGPT / coding        "Review the star schema Check grain, key
  assistant (fill in      and explain the         relationships,
  actual tool used)       customer SCD Type 2     unknown-member
                          approach."              handling, and whether
                                                  the implementation
                                                  supports incremental
                                                  versioning.
  -----------------------------------------------------------------------

Record what the team accepted, corrected, or rejected. Do not claim that
AI-generated code or cloud deployment was validated unless the team
performed the corresponding tests.
