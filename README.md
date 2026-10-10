# RetailBank — Customer Transaction Analytics

**HCLTech AI–Cloud Data Engineering Hackathon | Working project**

RetailBank is a synthetic retail-banking data engineering project designed to demonstrate source ingestion, data profiling, cleansing, dimensional modelling, banking KPI analytics, and incremental processing across two batch runs.

> **Data disclaimer:** All records generated for this project are fictional synthetic data. They do not represent real customers, accounts, branches, or transactions. The current dataset is a development/demo dataset, not a production banking system.

## 1. Problem statement

Retail banking data arrives from multiple operational sources and may contain missing values, inconsistent formats, duplicate records, invalid dates and amounts, or references to entities that do not exist. Analytics built directly on this data can be inaccurate.

This project is intended to build a repeatable pipeline that:
- Ingests source files while preserving raw inputs.
- Profiles and validates data and records rejection reasons.
- Standardizes data and creates curated customer, product, branch, and transaction tables.
- Produces the 13 KPIs specified in the RetailBank case study.
- Processes a second batch containing new records, dimension updates and transaction corrections without unintended duplicate facts.
- Provides test evidence, reconciliation outputs and documentation.

**Implementation status:** The synthetic source-data generator has been created and run. The profiling and analytics pipeline, curated model, all 13 KPIs, and robust Day 2 processing are planned next and must not be considered complete until implemented and tested.

## 2. Architecture

```text
Day 1 CSV/JSON + Day 2 update CSV/JSON
                  |
                  v
        Ingestion and metadata
                  |
                  v
           Bronze / Raw
       (preserve original data)
                  |
                  v
       Profiling and cleansing
       /                    \
Clean records             Quarantine
       |
       v
Customer / Product / Branch dimensions
              + Transaction fact
                  |
                  v
         KPI calculations 1–10
                  |
                  v
      Day 2 upserts and corrections
       + SCD Type 2 where applicable
                  |
                  v
         KPI calculations 11–13
                  |
                  v
     Reconciliation, tests and reports
```

### Proposed technology stack

- **Python** for synthetic data generation, orchestration helpers and validation.
- **SQL** for dimensional modelling and KPI calculations.
- **PySpark / Azure Databricks** for scalable processing, if the team's environment supports it.
- **Azure Data Lake Storage Gen2** for cloud raw and curated storage, if Azure access is available.
- **Git and GitHub** for collaboration, review and version control.

The case study permits a cloud-platform choice. Azure is the proposed implementation; cloud resources must be configured and verified before the project is described as deployed.

## 3. Repository contents

```text
retailbank-customer-transaction-analytics/
├── README.md
├── generate_retailbank_data.py
├── profile_retailbank_data.py
├── RetailBank_SourceData/
│   ├── branches.csv
│   ├── customers.csv
│   ├── products.json
│   └── transactions.csv
└── RetailBank_SourceData_Day2/
    ├── branches_day2.csv
    ├── customer_updates_day2.csv
    ├── products_day2.json
    └── transactions_day2.csv
```

As the project grows, add implementation folders such as `src/`, `sql/`, `tests/`, `config/`, `docs/`, and `outputs/`. Only include files that exist and are maintained.

## 4. Generated data

The current generator uses Python's standard library and a fixed seed (`20261010`) to make generated data reproducible.

| File | Current generated row/object count | Purpose |
|---|---:|---|
| `RetailBank_SourceData/branches.csv` | 16 rows | Branch master records with intentional quality issues |
| `RetailBank_SourceData/customers.csv` | 601 rows | Customer/account records with intentional quality issues |
| `RetailBank_SourceData/products.json` | 13 objects | Product records with intentional quality issues |
| `RetailBank_SourceData/transactions.csv` | 2,002 rows | 2,000 generated transactions plus two duplicate-like injected rows |
| `RetailBank_SourceData_Day2/branches_day2.csv` | 2 rows | New branch and existing branch update |
| `RetailBank_SourceData_Day2/customer_updates_day2.csv` | 3 rows | Customer update and newly onboarded customers |
| `RetailBank_SourceData_Day2/products_day2.json` | 2 objects | Existing product update and new product |
| `RetailBank_SourceData_Day2/transactions_day2.csv` | 123 rows | New transactions, a correction and a duplicate resend |

Counts are the generator's current output and may change if the generator is edited.

### Intentionally injected data-quality scenarios

- Blank/missing fields.
- Inconsistent text casing and whitespace.
- Invalid dates and timestamps.
- Negative, zero, currency-formatted and unusually large amounts.
- Duplicate-like records and conflicting business keys.
- Invalid customer, branch and product references.
- Inconsistent payment method, status, currency and refund representations.
- Day 2 additions, updates and a correction to an existing transaction ID.

Not every unusual record should be deleted. For example, a high-value transaction is a monitoring signal, not proof of fraud. Negative amounts, non-INR transactions, conflicting IDs and missing references should be handled using documented business rules and may require quarantine or review.

## 5. Generate the datasets

Requirements: Python 3.10+ is recommended; the generator uses only the Python standard library.

Run from the repository root:

```powershell
python generate_retailbank_data.py
```

If Windows does not recognize `python`, use the installed executable path or configure Python on PATH. For the current Windows setup, this command has been verified:

```powershell
& "$env:LOCALAPPDATA\Python\bin\python.exe" .\generate_retailbank_data.py
```

The script creates both dataset folders beside the script.

## 6. Profile the datasets

The read-only profiling script reports columns, blank values, exact duplicate rows, duplicate business-key values and a sample of the data.

```powershell
python profile_retailbank_data.py
```

On the current Windows setup:

```powershell
& "$env:LOCALAPPDATA\Python\bin\python.exe" .\profile_retailbank_data.py
```

The profile output should be saved as evidence after it has been reviewed. Profiling does not clean or modify the source data.

## 7. Planned processing stages

1. **Inspect and profile:** Verify schemas, row counts, candidate keys, nulls, duplicates and malformed values.
2. **Ingest:** Preserve source files and capture batch/run metadata.
3. **Clean and validate:** Normalize formats, apply field-level and referential-integrity rules, and route rejected records to quarantine with reason codes.
4. **Model:** Build customer, product and branch dimensions plus a transaction fact table. Document the fact grain and keys.
5. **Baseline KPIs:** Calculate KPIs 1–10 on the Day 1 curated data.
6. **Incremental processing:** Process Day 2 additions, dimension updates and transaction corrections. Make reruns idempotent and preserve meaningful history using SCD Type 2 where appropriate.
7. **Incremental KPIs:** Produce KPIs 11–13 and refresh metrics affected by Day 2 changes.
8. **Test and reconcile:** Verify row counts, key uniqueness, references, KPI calculations, corrections and rerun behaviour.
9. **Submit:** Include architecture, business rules, data dictionary, quality/rejection report, curated tables, KPI outputs, tests and a short demo.

## 8. Required KPI coverage

The implementation should cover the case study's 13 KPIs:

1. Top 5 customers by net transaction volume.
2. Monthly transaction trend by branch and region.
3. Product-wise revenue contribution.
4. Dormant/inactive accounts.
5. High-value/suspicious transaction monitoring.
6. Customer segmentation (RFM-lite).
7. Branch performance ranking within region.
8. KYC risk exposure.
9. Refund rate by product and branch.
10. Data quality scorecard.
11. Day-over-day incremental reconciliation.
12. Customer KYC status transition report.
13. New account activation.

Exact formulas, tie-breakers, refund treatment, thresholds and date-window definitions must be documented from the case study and confirmed against the actual source schemas before final KPI results are claimed.

## 9. Testing and acceptance criteria

Before submission, verify at least the following:

- All source files can be read and their observed schemas are documented.
- Raw inputs are preserved.
- Invalid records have explicit rejection reasons.
- Duplicate handling distinguishes exact duplicates from conflicting keys.
- Dimension keys and transaction references are valid or explicitly quarantined.
- KPI calculations are tested against small, hand-checkable examples.
- Day 2 inserts and updates are applied to the correct business keys.
- A correction updates the intended existing transaction rather than creating a duplicate fact.
- Re-running the same Day 2 batch does not create unintended duplicate facts.
- Baseline and incremental KPI outputs are saved and reproducible.

## 10. Team workflow

Use a shared repository and feature branches. Each team member should commit their own meaningful work under their own GitHub account, open pull requests, review teammates' changes and merge tested changes into the default branch. Do not commit passwords, cloud keys, tokens or other secrets.

Suggested areas of ownership:
- **Member 1:** Ingestion, source schemas and profiling.
- **Member 2:** Cleansing, validation rules, quarantine and quality scorecard.
- **Member 3:** Curated model and KPI SQL/analytics.
- **Member 4:** Incremental processing, orchestration, reconciliation and integration tests.

Coordinate the contracts between modules before implementation so column names and output formats remain consistent.

## 11. Limitations

- All current data is synthetic and designed for a hackathon demonstration.
- Synthetic patterns do not establish real-world banking behaviour or fraud.
- Cloud deployment is not implied by local execution of the generator.
- KPI correctness depends on validated source semantics and documented business rules.
- This project is not intended for real customer data or production banking decisions.

## License

Add a license only after the team agrees on the repository's intended license and ownership.
