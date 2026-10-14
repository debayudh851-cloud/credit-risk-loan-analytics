# Credora version 2 results

The pipeline now scores applicants using request-time inputs and earlier transactions, and scores every customer using a distinct actual-profile model. All invented reference-loan scenarios have been removed from active scoring.

## Portfolio

Customers 5,000; applications 7,500; disbursed loans 3,403; pending 173. Approval rate 46.44% on decided applications. Observed default rate 23.42%. Disbursed value INR 441.23 crore.

## Applicant evaluation

Selected XGBoost; accuracy 0.4831; precision 0.2822; recall 0.7862; f1 0.4153; roc_auc 0.6670; average_precision 0.4006; brier_score 0.1657. Training-only threshold 0.16. AUC acceptance: not_met; recall acceptance: passed. These are measurements on the frozen continuation holdout, not fresh external validation. Four algorithms are compared under the strict feature contract.

## Customer evaluation

Selected Random Forest; accuracy 0.5216; precision 0.3197; recall 0.8174; f1 0.4597; roc_auc 0.6709; average_precision 0.3957; brier_score 0.1748. Every customer has actual-profile model features; zero hypothetical loan scenarios. Customers without observed outcomes remain an unvalidated extrapolation population. The model targets latest observed loan default association, not a defined future horizon.

## Operational checks

Engine PostgreSQL; all ten queries executed, slowest 0.0663 seconds. Applicant coverage 7,500; customer coverage 5,000. Total model training 91.7 seconds; full pipeline 171.2 seconds. Source hashes and feature contracts are persisted.

## Unresolved acceptance

Real prospective validation requires application-time bureau/profile history, default-event dates, observation-end dates and a formal outcome horizon. Current CSVs cannot supply those facts. AUC ≥0.80 is a measured acceptance target and is not marked passed unless the strict model achieves it. See acceptance_status.json and requirements_traceability.md for the current status.

## Demo

Run python -m src.pipeline; then streamlit run dashboard/app.py. Review portfolio KPIs and all eight required components. Use state, loan-type, month and risk filters. Select an application to inspect request-time probability and signed drivers. Select a customer to inspect its actual-profile score and contribution trace. Review Model evidence for both models, the fixed-calendar audit, source limitations and objective acceptance states. Batch new requests with python -m src.score_requests --requests INPUT.csv --transactions HISTORY.csv --output OUTPUT.csv.
