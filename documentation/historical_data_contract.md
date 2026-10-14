# Historical data needed for prospective validation

This contract describes the missing evidence. It does not backdate current snapshots or certify the existing model as a forward forecast. The current request-time scorer is usable without bureau/profile inputs; the complete PRD feature set and genuine future-default validation require the history below.

## Profile history

One or more versions per customer with customer_id, effective_from, captured_at, annual_income, employment_type, dependents, education, residence_type and years_at_residence. Both effective_from and captured_at must be at or before application. The latest valid version is selected, never a later current value. If no version was available, the field remains missing rather than inferred from future history. Birth dates require validated application-date age and verified correction history for inconsistent records.

## Bureau history

customer_id, bureau_snapshot_id, as_of_date, captured_at and the PRD credit fields. A pull must have been captured before the decision; a later bureau snapshot cannot be retrospectively treated as available. One current June 30 2024 row per customer does not satisfy this contract for July 2022–June 2024 applications.

## Repayment outcomes

application_id, disbursement_date, default_event_date if any, observation_end, default_definition, outcome_horizon_months, reporting_cutoff and payment_history completeness. Define the default rule, such as a documented delinquency criterion, with risk officers. Use a fixed horizon and train only on mature observation windows. Non-default requires observation through the full horizon; a recent borrower without a default yet is not automatically a known non-default. Do not impute missing outcome dates.

## Transaction history

customer_id, transaction_id, transaction_date, captured_at, amount, direction, category and observed balance. Both event and capture time must be before application. Coverage start/end dates distinguish a zero-event complete window from unobserved history. The current file has event dates but no capture times and begins January 2024, so older applications lack observed coverage.

## Acceptance protocol

Freeze the outcome definition and input availability rules before model selection. Train on mature earlier cohorts; test on later mature cohorts and unseen customers. Tune, calibrate and choose review thresholds only inside development folds. Evaluate ROC-AUC, recall, precision, F1, calibration and subgroup stability on the locked external holdout. The requested 0.80 AUC remains an acceptance target, not a value to fabricate or guarantee before those data exist.
