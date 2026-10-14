"""Evidence-based reports with distinct applicant and customer target semantics."""
import json
from .config import ROOT,OUT
from .features import STRICT_FEATURES,PROFILE_FEATURES

def comparison_table(result):
    rows = ['| Model | Training CV AUC | CV std | Test AUC |',
            '|---|---:|---:|---:|']
    rows.extend(f"| {r['model']} | {r['cv_roc_auc']:.4f} | {r['cv_auc_std']:.4f} | {r['test_at_0_5']['roc_auc']:.4f} |"
                for r in result['comparison'])
    return '\n'.join(rows)

def metric_text(m):
    return '; '.join(f'{name} {m[name]:.4f}' for name in ['accuracy','precision','recall','f1','roc_auc','average_precision','brier_score'])

def write_reports(main,customer,summary,audit,manifest,info,timing,frames,status):
    docs = ROOT/'documentation'
    m = main['test_metrics']
    cm = customer['test_metrics']
    tn,fp = m['confusion_matrix'][0]
    fn,tp = m['confusion_matrix'][1]
    audit_text = 'Skipped by explicit command-line option.' if audit is None else metric_text(audit)
    card = f'''# Credora model cards

Version 2 separates applicant scoring from customer-profile scoring. The applicant classifier uses submitted request inputs and transactions dated strictly before application. The customer classifier uses actual customer and bureau records, with no hypothetical loan request. Both estimate the supplied historical labels; neither establishes a certified future default probability because outcome horizons and maturity dates are absent.

## Applicant model

Selected algorithm: {main['champion']}. Target: observed loan_default, only on disbursed loans. Model inputs contain no bureau fields, undated customer profile fields, names, contacts, geography, gender, approval status, sanctioned amount, decision date, disbursal flag, offered interest rate or supplied underwriting DTI. Requested amount, term, purpose, loan type, collateral, declared monthly income and existing EMI are treated as submitted application inputs. Their field-level capture timestamps are not independently available. Request-to-income ratios, principal-only instalment burden, log transforms and a history-availability indicator are derived without an assumed interest rate. Earlier transaction history uses a trailing six-calendar-month window excluding the application day. Empty histories remain missing and imputation occurs inside training folds.

Four algorithms use training-only five-fold grid search including class weighting. Numeric median imputation and Unknown/one-hot categorical encoding are fitted per fold. Only logistic regression scales numeric fields. Winner selection uses CV AUC then CV recall. Sigmoid calibration uses three-fold training CV. Five-fold nested out-of-fold calibrated predictions select the largest-precision threshold subject to recall at least 80%. Threshold: {main['threshold']:.2f}. The final model remains fitted on {main['n_train']} training records; {main['n_test']} holdout records remain excluded from its fit.

{comparison_table(main)}

Held-out metrics: {metric_text(m)}.

| Actual versus predicted | No default | Default |
|---|---:|---:|
| No default | {tn} | {fp} |
| Default | {fn} | {tp} |

The v1 application partition is preserved rather than trying new seeds until targets pass. {main['holdout_note']} The application-level partition shares {main['test_customer_overlap']} customers. A customer-disjoint sensitivity audit yields {metric_text(main['group_holdout_audit'])}. A fixed 2024 calendar sensitivity audit yields {audit_text}. Calendar partitioning does not establish historical label availability: the file contains no event date or observation-end date. Labels may not have matured at the cutoff.

## Customer profile model

Selected algorithm: {customer['champion']}. Target: each observed customer's latest recorded disbursed loan_default label, determined by application_date then application_id. This creates one labelled row per customer and avoids treating unobserved customer outcomes as non-defaults. All {manifest['customer_scores']:,} customers are scored using their own demographics, bureau indicators, actual cashflows and credit/income transforms. Application amount, term, type, collateral and other loan-request fields are absent from this model. No reference application is generated. The source_application_id is NULL because this score is produced from the profile rather than an individual application. score_basis is customer_profile_model.

This estimates the association between supplied profiles and the latest observed loan outcome, not the risk of a particular future loan. Bureau snapshots are all June 30 2024 and may include post-outcome deterioration. Undated profiles and the observed-loan selection process limit extrapolation to customers without outcomes. Scores for customers lacking applications are model estimates with unknown external validity, never observed outcomes. This limitation cannot be removed by eliminating the hypothetical scenario alone.

Customer rows are stratified 80/20 with seed 42, and no customer ID appears in both partitions. Four algorithms, calibration and threshold policy follow the same training-only protocol. Threshold: {customer['threshold']:.2f}. Held-out customers: {customer['n_test']}. Metrics: {metric_text(cm)}.

{comparison_table(customer)}

## Risk and explanations

Scores follow round(100 × calibrated probability), with Low 0–33, Medium 34–66 and High 67–100. The review flag threshold is separate from these bands. Every application and every customer has complete signed SHAP traces and top-five driver summaries. Applicant SHAP scale is {info['output_scale']}; maximum reconstruction error is {info['max_additivity_error']:.8g}. Traces reconstruct the selected base estimator. Its saved scale conversion and sigmoid mapping produce the final probability; XGBoost log margins first pass through expit; contributions are not additive calibrated percentage points. Global SHAP and native tree importances are retained for both model populations.

## Acceptance and limitations

Applicant AUC ≥0.80: {status['roc_auc_at_least_0_80']['status']}; recall ≥0.70: {status['recall_at_least_0_70']['status']}. A development-only retrospective challenger investigation explores log/threshold transforms and wider tuning without examining the test set. It does not establish future validity or replace failed acceptance metrics. Outcomes have no formal default definition, event dates or fixed follow-up horizon. Reject inference, temporal maturity validation and fairness certification remain unsupported. Scores advise manual investigation; no automated lending decision is implemented.

## Artefacts and repeatability

models/default_model.pkl is the request-time classifier; models/customer_model.pkl is the separate profile classifier. Only load trusted pickle files. Their exact feature contracts, models, thresholds, seeds and contexts are saved. artifacts/metrics.json, customer_model/metrics.json, split manifests, source hashes and package versions preserve provenance. Applicant training took {main['training_seconds']:.1f} seconds; customer training {customer['training_seconds']:.1f} seconds; full pipeline {manifest['total_seconds']:.1f} seconds. Use the locked Python 3.13 environment for numerical reproducibility.
'''
    (ROOT/'models/model_card.md').write_text(card,encoding='utf-8')
    report = f'''# Credora version 2 results

The pipeline now scores applicants using request-time inputs and earlier transactions, and scores every customer using a distinct actual-profile model. All invented reference-loan scenarios have been removed from active scoring.

## Portfolio

Customers {summary['customers']:,}; applications {summary['applications']:,}; disbursed loans {summary['disbursed']:,}; pending {summary['pending']}. Approval rate {summary['approval_rate']:.2%} on decided applications. Observed default rate {summary['default_rate']:.2%}. Disbursed value INR {summary['disbursed_value_inr']/1e7:.2f} crore.

## Applicant evaluation

Selected {main['champion']}; {metric_text(m)}. Training-only threshold {main['threshold']:.2f}. AUC acceptance: {status['roc_auc_at_least_0_80']['status']}; recall acceptance: {status['recall_at_least_0_70']['status']}. These are measurements on the frozen continuation holdout, not fresh external validation. Four algorithms are compared under the strict feature contract.

## Customer evaluation

Selected {customer['champion']}; {metric_text(cm)}. Every customer has actual-profile model features; zero hypothetical loan scenarios. Customers without observed outcomes remain an unvalidated extrapolation population. The model targets latest observed loan default association, not a defined future horizon.

## Operational checks

Engine {manifest['engine']}; all ten queries executed, slowest {max(x['seconds'] for x in timing):.4f} seconds. Applicant coverage {manifest['application_scores']:,}; customer coverage {manifest['customer_scores']:,}. Total model training {manifest['total_model_training_seconds']:.1f} seconds; full pipeline {manifest['total_seconds']:.1f} seconds. Source hashes and feature contracts are persisted.

## Unresolved acceptance

Real prospective validation requires application-time bureau/profile history, default-event dates, observation-end dates and a formal outcome horizon. Current CSVs cannot supply those facts. AUC ≥0.80 is a measured acceptance target and is not marked passed unless the strict model achieves it. See acceptance_status.json and requirements_traceability.md for the current status.

## Demo

Run python -m src.pipeline; then streamlit run dashboard/app.py. Review portfolio KPIs and all eight required components. Use state, loan-type, month and risk filters. Select an application to inspect request-time probability and signed drivers. Select a customer to inspect its actual-profile score and contribution trace. Review Model evidence for both models, the fixed-calendar audit, source limitations and objective acceptance states. Batch new requests with python -m src.score_requests --requests INPUT.csv --transactions HISTORY.csv --output OUTPUT.csv.
'''
    (docs/'results.md').write_text(report,encoding='utf-8')
    contract = ['# Feature availability contracts','',
                'The two populations have distinct estimands. A current customer profile is never substituted into a historical application.','',
                '## Applicant features','',
                'Source: submitted request fields and strictly earlier transactions. Assumes request fields were captured at the application; field capture timestamps are unavailable.','']
    contract += [f'- {f}' for f in STRICT_FEATURES]
    contract += ['', '## Customer profile features','',
                 'Source: actual customer and June 30 2024 bureau records plus January–June account transactions. Historical default association; no loan scenario or future-horizon claim.','']
    contract += [f'- {f}' for f in PROFILE_FEATURES]
    contract += ['', '## Historical data needed for prospective validation','',
                 'Supply customer_id, effective_from and captured_at for profile history; bureau snapshots with pull timestamps; loan outcome event date, observation_end, default definition and horizon. A snapshot later than application is rejected or omitted rather than backdated.']
    (docs/'feature_contracts.md').write_text('\n'.join(contract),encoding='utf-8')
