# Requirements traceability and acceptance

Version 2 implements the local decision-support platform from the supplied PRD, with distinct request-time and customer-profile models. Implementation status is separate from statistically validated acceptance. No failed target is marked passed by changing labels, choosing a favourable test seed or inventing history.

| Requirement | Implementation and evidence | Status |
|---|---|---|
| FR-01 Normalised four-table schema | PostgreSQL and SQLite PK/FK/CHECK constraints, indexes and invalid-value probes | Implemented and tested |
| FR-02 CSV bulk ingestion | COPY in PostgreSQL; transaction-based SQLite load; duplicate optional contacts corrected without changing raw files | Implemented and tested |
| FR-03 Ten risk analyses | sql/analysis.sql; full-book query exports and correct denominators | Implemented and tested |
| FR-04 Default probability every disbursed loan | Request-time model scores every application, probability bounded [0,1] | Implemented; prospective validation incomplete |
| FR-05 Risk score 0–100 and category | Exact bands; 5,000 actual-profile customer scores; zero invented application scenarios | Implemented and tested; unobserved borrowers remain extrapolations |
| FR-06 Missingness and categorical encoding | Fold-local median, Unknown, one-hot; scaling only for logistic regression | Implemented and tested |
| FR-07 Five held-out evaluation metrics | Separate applicant and customer confusion matrices, accuracy, precision, recall, F1 and AUC | Implemented and reported |
| FR-08 Ranked importance | Global SHAP and native tree importance for both populations | Implemented; exact per-record traces checked |
| FR-09 Eight dashboard components | Portfolio KPI/trends, default-by-product, customer risk donut, credit histogram, state distribution, volumes, decision trends, watchlist | Implemented and tested |
| FR-10 Risk and region filters | Customer-risk and state filters, consistent borrower cohorts and empty states | Implemented and tested |
| FR-11 Model persistence | default_model.pkl and customer_model.pkl; context and exact feature contracts saved | Implemented; reload probabilities checked |
| FR-12 Single-command repeatability | python -m src.pipeline; two complete v2 runs compared | Implemented and reproduced |
| Four algorithms | Logistic Regression, Decision Tree, Random Forest, XGBoost independently compared for both populations | Implemented |
| 80/20 stratified split | Fixed seed 42; original application holdout retained; customer entity split has no overlap | Implemented; application holdout is a continuation, not fresh external data |
| Five-fold CV | Training-only grid search and OOF threshold policy | Implemented |
| Pre-disbursal input availability | No future bureau, undated profile, offered rate, underwriting DTI or decision output in applicant features; earlier transactions only | Implemented under submitted-request field assumptions |
| Genuine future default validation | Needs historical snapshots, event dates, observation ends and a defined horizon | Blocked by missing source data |
| ROC-AUC ≥0.80 | Strict applicant held-out AUC 0.6670; development-only wider retrospective investigation best CV 0.7371 | Not met |
| Recall ≥0.70 | Strict applicant recall 0.7862 | Passed |
| SQL <2 seconds | Ten full-dataset PostgreSQL and SQLite queries | Passed in tested environment |
| Full model training <5 minutes | Total training across both four-model workflows approximately 92 seconds in first v2 run | Passed; explainability and notebook time are additional |
| Maintainability and portability | Modular src, relative paths, four ordered notebooks and locked environment | Implemented |
| No direct PII in dashboards/commits | Raw files and artefacts ignored; source-only exporter strips notebook outputs | Tested; publication manifest controls handover |
| Every score traceable | 7,500 application and 5,000 customer SHAP rows; exact base and calibrated probability reconstruction | Implemented and verified |
| README, dictionary, model card | Run guide, field semantics, separate population/model cards and provenance contract | Delivered |
| Version control and GitHub | Project-only local commit and private repository handover for supplied account | See documentation/git_handover.md and local acceptance evidence |

## Missing evidence and interpretation

The June 30 2024 bureau snapshot cannot be retrospectively assigned to July 2022–June 2024 application dates. The applicant model therefore omits that data entirely. The customer model uses the actual snapshot for a retrospective profile association, never as historical applicant input. The source lacks default events and observation maturity, so even a fixed-calendar audit cannot prove that labels were known at its training cutoff. The PRD-allowed credit histogram is used because one bureau snapshot cannot establish a longitudinal trend.

The customer model replaces invented loan scenarios but cannot validate outcomes for borrowers who have no observed loans. Its target is the latest observed disbursed-loan default label per borrower, not an unspecified future loan. Historical_data_contract.md identifies the records needed for a future-horizon model. acceptance_status.json keeps the AUC and prospective-validation gaps explicit.
