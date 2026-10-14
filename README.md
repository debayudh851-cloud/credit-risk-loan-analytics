# Credora Credit Risk and Loan Approval Analytics

An end-to-end local data science project with governed PostgreSQL/SQLite ingestion, ten analytical SQL queries, four-algorithm comparisons, risk scoring, per-record SHAP explanations, ordered notebooks and an interactive Streamlit dashboard.

Version 2 separates **request-time applicant scoring** from **customer-profile scoring**. Applicant inputs exclude future bureau snapshots, undated customer attributes and underwriting outputs. Every customer is scored from their own actual profile; no hypothetical loan amount, term or product is generated.

## Measured acceptance

The strict request-time XGBoost model achieves **ROC-AUC 0.6670** and **recall 78.62%** on the frozen continuation holdout. Recall meets the 70% target; AUC does **not** meet 0.80. The customer-profile Random Forest model achieves AUC 0.6709 and recall 81.74% on a customer-disjoint holdout. Scores for customers without observed loan outcomes remain unvalidated extrapolations.

The source has no default-event dates, observation-end dates or defined default horizon, and every bureau snapshot is later than the historical applications. Request-time feature isolation is implemented and tested, but genuine prospective default validation still needs dated history and mature outcomes. No data are backdated or generated to manufacture acceptance. Read [the model cards](models/model_card.md) and [feature contracts](documentation/feature_contracts.md).

## Run locally

Use Python 3.10+; the delivered numerical results use Python 3.13 and requirements-lock.txt.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
python -m src.pipeline
streamlit run dashboard/app.py
```

On macOS/Linux use `source .venv/bin/activate`. For other compatible Python versions install requirements.txt; numerical identity across dependency versions is not guaranteed.

Provide the four original CSVs in datasets/ as customers.csv, credit_history.csv, loan_applications.csv and transactions.csv. The loader also recognises the original root filenames, including customers (1).csv, and copies them without changing their contents. Two duplicate optional email contacts are set to NULL only during database ingestion so the UNIQUE constraint remains enforced. Nullable target integers are serialised correctly in both SQL engines.

The default command uses a constrained SQLite database for portability. PostgreSQL is the reference PRD engine and was tested on the full data:

```powershell
$env:CREDORA_DATABASE_URL='postgresql://credora@127.0.0.1:6543/credora'
python -m src.pipeline
```

Use a dedicated database; reruns atomically replace rows in the project-owned raw tables and subsequently replace scores. The schema uses PK/FK/CHECK constraints and indexes. The provided original SQL seed script is retained locally but excluded from publication because it contains direct contacts and inconsistent seed foreign keys. The implemented SQL layer has no embedded PII or destructive DROP statements.

Use `docker compose up -d` for a private loopback development instance, or scripts/start_postgres.ps1 and scripts/stop_postgres.ps1 with installed PostgreSQL tools on Windows. Do not start both on port 6543. Development trust authentication is restricted to the private local database; shared installations require proper credentials.

## Two model contracts

| Population | Actual inputs | Target and meaning |
|---|---|---|
| Application | Submitted request fields, derived burden ratios, transactions strictly before application | Historical observed loan_default association using request-time features |
| Customer | Customer profile, June 30 bureau snapshot, actual account history | Latest recorded disbursed-loan default association, one labelled row per observed customer |

Both populations independently compare Logistic Regression, Decision Tree, Random Forest and XGBoost. Training-only five-fold search evaluates regularisation and class weighting. Imputation and encoding are fitted within folds. Only logistic regression scales numerics. Sigmoid calibration and the review threshold use training folds; test results do not choose the model or threshold. The review threshold maximises training OOF precision subject to at least 80% recall. The original application holdout is preserved and explicitly identified as previously reported, not fresh external validation. Borrower-disjoint and fixed-calendar sensitivity audits are also reported.

Customer IDs never enter model features. One latest observed loan label per borrower prevents duplicated customer targets. Unobserved outcomes stay missing. Customer probabilities do not describe an unspecified future loan; their score_basis records customer_profile_model. source_application_id is NULL because the model uses profile inputs rather than an application.

Risk score is round(probability ×100): Low 0–33, Medium 34–66, High 67–100. The review threshold is a separate policy. Complete signed SHAP rows reconstruct every applicant and customer base prediction. The recorded output-scale conversion and sigmoid mapping reconstruct the final probability. XGBoost raw margins first require expit before its probability-based calibration. Explanations are descriptive associations, not causal reasons or automated lending decisions.

## Batch new requests

```powershell
python -m src.score_requests --requests new_requests.csv --transactions history.csv --output artifacts/new_request_scores.csv
```

Required request fields: application_id, customer_id, application_date, requested_amount, loan_term_months, loan_type, loan_purpose, collateral_flag, applicant_monthly_income and existing_emi. Unknown customers can be scored without a bureau/profile table. Future transactions are excluded, absent history stays missing, and the scorer rejects a model with the wrong context. Date ordering alone cannot verify the provenance of supplied request fields or outcome maturity.

## Dashboard and notebooks

All eight required components are present: approval KPI/trend, default KPI/by-product bars, unique customer-risk distribution, credit histogram, geographic state bars, monthly application volumes, approval/rejection trends and a ranked filterable customer watchlist. State, loan type, application month and customer-risk filters select consistent borrower cohorts. Applicant and customer selectors show their respective predictions and signed drivers. The credit histogram describes a single snapshot; default lines show application cohorts because event dates are absent.

Run notebooks/01_eda.ipynb through 04_risk_scoring.ipynb after the pipeline. They cover EDA, the separate feature contracts, four-model evidence and risk handover, and execute against the actual output. Use `python scripts/execute_notebooks.py` to verify all cells. Published notebooks contain code and narrative; executed local copies contain the results.

## Verification

```powershell
python -m unittest discover -v
python scripts/verify_project.py
python scripts/check_reproducibility.py --use-existing-baseline
```

Twenty unit/dashboard checks passed. Integration checks cover PK/FK/CHECK rejection in PostgreSQL and SQLite, all ten queries, all 7,500 application scores and 5,000 customer scores, both model reloads, SHAP/calibration reconstruction, no direct PII in dashboard inputs and future-transaction isolation. Two complete v2 runs reproduced both models' metrics, probabilities and risk scores. Total training across both four-model workflows took under five minutes. Exact run timings, source hashes and packages live in artifacts/run_manifest.json.

The separate `python scripts/investigate_auc.py` uses only the frozen development partition to investigate wider retrospective models and domain transforms. It does not evaluate or select against the test set and does not replace failed held-out acceptance.

## Project map

| Location | Purpose |
|---|---|
| sql/ | Governed schema and ten curated queries |
| src/ | Ingestion, contract-specific features, training, customer scoring, batch scoring, explainability and reporting |
| notebooks/ | Four ordered analysis and handover notebooks |
| models/ | Local model binaries and published model cards |
| dashboard/ | Streamlit risk desk |
| artifacts/ | Local scores, metrics, figures, query exports, traces and verification evidence |
| documentation/ | Dictionary, feature contracts, results, quality findings and requirement status |
| scripts/ | Reproducibility, notebook execution and local PostgreSQL helpers |

Raw files, original contact-bearing SQL, PRD copies, private databases, binary models and per-record outputs are ignored by Git. The publication exporter strips notebook outputs and permits only source and aggregate documentation. The user-approved public repository is https://github.com/debayudh851-cloud/credit-risk-loan-analytics; its source-only handover excludes raw borrower data. Original v1 code and evidence are preserved privately in .local/v1_baseline.
