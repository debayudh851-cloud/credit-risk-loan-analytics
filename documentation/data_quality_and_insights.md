# Data quality and portfolio interpretation

The supplied files were profiled before modelling and loaded with database constraints. Raw source files remain unchanged. All customer foreign keys are valid and all entity primary keys are unique.

| Issue | Measured count | Treatment and consequence |
|---|---:|---|
| Repeated optional email contacts | 2 repeated rows | Keep the first contact; NULL the repeated optional contacts during ingestion. Preserve original CSVs. UNIQUE remains enforced. |
| Historical application before bureau snapshot | 7,500 applications | Label primary models retrospective. Mask unavailable bureau fields in the application-time audit. |
| Relationship start after application | 935 applications | Flag inconsistent profile timing; clip relationship tenure to zero. Historical profile provenance remains unresolved. |
| Computed age below 18 at application | 124 applications | Retain records for supplied-label analysis; flag age/date inconsistency. No lending eligibility decision is inferred. |
| Default outcome missing on non-disbursed applications | 4,097 | Structural missingness. Exclude from supervised training; do not label as repaid. |
| Decision date absent | 173 | Pending decisions. Exclude from approval-rate denominator. |
| Customers without any application | 1,096 | Version 2 uses each actual profile in a separate customer model, with no assumed loan request. Outcomes for these borrowers are unobserved. |

Transaction data run from January 1 through June 29 2024 and are incomplete for most historical application windows. The bureau has exactly one snapshot date, June 30 2024. Profiles do not have effective-from dates, outcomes lack event dates and maturity horizons, and the supplied age field does not consistently describe age at application. These limitations cannot be repaired by imputation or a stronger algorithm.

## Segment findings

Home loans have a 31.60% observed default rate over 326 disbursed loans, followed by Business at 29.66% over 290 loans. Personal loans have the largest disbursed sample, 1,395, and a 20.29% observed default rate. Education is 27.38% over 336 loans, Gold 23.32% over 386, and Auto 21.34% over 670. These rates describe observed approved borrowers, not rejected applicants or causal effects of product choice.

Gold has the highest approval rate among decided applications, 64.23%; Home has the lowest, 26.83%. Compare risk and approval together: a low approval rate alone has not eliminated high observed default risk in Home lending. An analyst should investigate underwriting inputs, collateral and cohort maturity rather than assume a product-level causal explanation.

The original v1 retrospective held-out test caught 123 of 159 defaults and misses 36 at the chosen threshold. It also flags 251 of 522 observed non-defaults. The 77.36% recall meets the PRD recall target, but 32.89% precision indicates a substantial manual-review burden. Raising the threshold trades recall for fewer false flags; the delivered threshold is selected on training-only predictions and must not be tuned against the test outcomes.

The original v1 Logistic Regression model achieved ROC-AUC 0.7045 on the historical retrospective test, below the requested 0.80. Its customer-disjoint audit AUC is 0.6844. A baseline that masks future bureau and transaction information achieves AUC 0.6784. These results support further data collection and validation, not a claim that the source can satisfy every model-quality target.

## Practical next steps

Acquire bureau pulls, income and profile attributes timestamped at application, complete historical cashflow windows, a formal default definition and a fixed observation horizon. Separate mature repayment cohorts from censored recent loans. Validate on future cohorts and unseen customers. Agree false-negative and false-positive costs with risk officers before setting an operational threshold. Retain underwriter review and test bias across customer groups before any lending use.


## Version 2 change

The active applicant XGBoost excludes future/undated attributes, achieving AUC 0.6670 and recall 78.62%. The actual-profile customer Random Forest achieves AUC 0.6709 and recall 81.74%; all 5,000 customer rows have observed profile inputs and zero hypothetical loan scenarios. These new population-specific results must not be confused with the original v1 retrospective benchmark above.
