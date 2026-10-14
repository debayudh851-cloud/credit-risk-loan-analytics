# Credora model cards

Version 2 separates applicant scoring from customer-profile scoring. The applicant classifier uses submitted request inputs and transactions dated strictly before application. The customer classifier uses actual customer and bureau records, with no hypothetical loan request. Both estimate the supplied historical labels; neither establishes a certified future default probability because outcome horizons and maturity dates are absent.

## Applicant model

Selected algorithm: XGBoost. Target: observed loan_default, only on disbursed loans. Model inputs contain no bureau fields, undated customer profile fields, names, contacts, geography, gender, approval status, sanctioned amount, decision date, disbursal flag, offered interest rate or supplied underwriting DTI. Requested amount, term, purpose, loan type, collateral, declared monthly income and existing EMI are treated as submitted application inputs. Their field-level capture timestamps are not independently available. Request-to-income ratios, principal-only instalment burden, log transforms and a history-availability indicator are derived without an assumed interest rate. Earlier transaction history uses a trailing six-calendar-month window excluding the application day. Empty histories remain missing and imputation occurs inside training folds.

Four algorithms use training-only five-fold grid search including class weighting. Numeric median imputation and Unknown/one-hot categorical encoding are fitted per fold. Only logistic regression scales numeric fields. Winner selection uses CV AUC then CV recall. Sigmoid calibration uses three-fold training CV. Five-fold nested out-of-fold calibrated predictions select the largest-precision threshold subject to recall at least 80%. Threshold: 0.16. The final model remains fitted on 2722 training records; 681 holdout records remain excluded from its fit.

| Model | Training CV AUC | CV std | Test AUC |
|---|---:|---:|---:|
| XGBoost | 0.7075 | 0.0207 | 0.6670 |
| Logistic Regression | 0.7062 | 0.0200 | 0.6699 |
| Random Forest | 0.7047 | 0.0234 | 0.6596 |
| Decision Tree | 0.6826 | 0.0210 | 0.6175 |

Held-out metrics: accuracy 0.4831; precision 0.2822; recall 0.7862; f1 0.4153; roc_auc 0.6670; average_precision 0.4006; brier_score 0.1657.

| Actual versus predicted | No default | Default |
|---|---:|---:|
| No default | 204 | 318 |
| Default | 34 | 125 |

The v1 application partition is preserved rather than trying new seeds until targets pass. Fixed v1 holdout, previously reported; v2 is a continuation, not a fresh external validation. The application-level partition shares 294 customers. A customer-disjoint sensitivity audit yields accuracy 0.4868; precision 0.2857; recall 0.8627; f1 0.4293; roc_auc 0.7115; average_precision 0.4020; brier_score 0.1586. A fixed 2024 calendar sensitivity audit yields accuracy 0.5129; precision 0.2887; recall 0.7886; f1 0.4227; roc_auc 0.6867; average_precision 0.3920; brier_score 0.1615. Calendar partitioning does not establish historical label availability: the file contains no event date or observation-end date. Labels may not have matured at the cutoff.

## Customer profile model

Selected algorithm: Random Forest. Target: each observed customer's latest recorded disbursed loan_default label, determined by application_date then application_id. This creates one labelled row per customer and avoids treating unobserved customer outcomes as non-defaults. All 5,000 customers are scored using their own demographics, bureau indicators, actual cashflows and credit/income transforms. Application amount, term, type, collateral and other loan-request fields are absent from this model. No reference application is generated. The source_application_id is NULL because this score is produced from the profile rather than an individual application. score_basis is customer_profile_model.

This estimates the association between supplied profiles and the latest observed loan outcome, not the risk of a particular future loan. Bureau snapshots are all June 30 2024 and may include post-outcome deterioration. Undated profiles and the observed-loan selection process limit extrapolation to customers without outcomes. Scores for customers lacking applications are model estimates with unknown external validity, never observed outcomes. This limitation cannot be removed by eliminating the hypothetical scenario alone.

Customer rows are stratified 80/20 with seed 42, and no customer ID appears in both partitions. Four algorithms, calibration and threshold policy follow the same training-only protocol. Threshold: 0.19. Held-out customers: 462. Metrics: accuracy 0.5216; precision 0.3197; recall 0.8174; f1 0.4597; roc_auc 0.6709; average_precision 0.3957; brier_score 0.1748.

| Model | Training CV AUC | CV std | Test AUC |
|---|---:|---:|---:|
| Random Forest | 0.6732 | 0.0203 | 0.6709 |
| Logistic Regression | 0.6713 | 0.0201 | 0.6649 |
| XGBoost | 0.6680 | 0.0264 | 0.6560 |
| Decision Tree | 0.6542 | 0.0224 | 0.6285 |

## Risk and explanations

Scores follow round(100 × calibrated probability), with Low 0–33, Medium 34–66 and High 67–100. The review flag threshold is separate from these bands. Every application and every customer has complete signed SHAP traces and top-five driver summaries. Applicant SHAP scale is raw_log_odds; maximum reconstruction error is 1.1920929e-06. Traces reconstruct the selected base estimator. Its saved scale conversion and sigmoid mapping produce the final probability; XGBoost log margins first pass through expit; contributions are not additive calibrated percentage points. Global SHAP and native tree importances are retained for both model populations.

## Acceptance and limitations

Applicant AUC ≥0.80: not_met; recall ≥0.70: passed. A development-only retrospective challenger investigation explores log/threshold transforms and wider tuning without examining the test set. It does not establish future validity or replace failed acceptance metrics. Outcomes have no formal default definition, event dates or fixed follow-up horizon. Reject inference, temporal maturity validation and fairness certification remain unsupported. Scores advise manual investigation; no automated lending decision is implemented.

## Artefacts and repeatability

models/default_model.pkl is the request-time classifier; models/customer_model.pkl is the separate profile classifier. Only load trusted pickle files. Their exact feature contracts, models, thresholds, seeds and contexts are saved. artifacts/metrics.json, customer_model/metrics.json, split manifests, source hashes and package versions preserve provenance. Applicant training took 43.4 seconds; customer training 48.3 seconds; full pipeline 171.2 seconds. Use the locked Python 3.13 environment for numerical reproducibility.
