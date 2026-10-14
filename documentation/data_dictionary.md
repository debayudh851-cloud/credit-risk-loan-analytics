# Data dictionary

Amounts are INR, dates are ISO 8601. Raw personal data remain local and are excluded from Git and dashboard exports.

## customers

| Field | CSV inferred type | Missing | Role |
|---|---|---:|---|
| customer_id | object | 0 | Application or entity key |
| first_name | object | 0 | Direct personal data; local raw database only |
| last_name | object | 0 | Direct personal data; local raw database only |
| gender | object | 0 | Source attribute |
| date_of_birth | object | 0 | Direct personal data; local raw database only |
| age | int64 | 0 | Source attribute |
| marital_status | object | 0 | Source attribute |
| dependents | int64 | 0 | Source attribute |
| education | object | 0 | Source attribute |
| employment_type | object | 0 | Source attribute |
| occupation | object | 0 | Source attribute |
| annual_income | int64 | 0 | Source attribute |
| city | object | 0 | Source attribute |
| state | object | 0 | Source attribute |
| residence_type | object | 0 | Source attribute |
| years_at_residence | int64 | 0 | Source attribute |
| email | object | 0 | Direct personal data; local raw database only |
| phone | object | 0 | Direct personal data; local raw database only |
| kyc_status | object | 0 | Source attribute |
| customer_since | object | 0 | Source attribute |

## credit_history

| Field | CSV inferred type | Missing | Role |
|---|---|---:|---|
| credit_id | object | 0 | Application or entity key |
| customer_id | object | 0 | Application or entity key |
| as_of_date | object | 0 | Source attribute |
| credit_score | int64 | 0 | Source attribute |
| num_open_accounts | int64 | 0 | Source attribute |
| num_credit_inquiries_6m | int64 | 0 | Source attribute |
| credit_utilization_ratio | float64 | 0 | Source attribute |
| num_late_payments_30d | int64 | 0 | Source attribute |
| num_late_payments_90d | int64 | 0 | Source attribute |
| num_defaults_prior | int64 | 0 | Source attribute |
| bankruptcies | int64 | 0 | Source attribute |
| total_credit_limit | int64 | 0 | Source attribute |
| total_outstanding_debt | int64 | 0 | Source attribute |
| oldest_account_age_months | int64 | 0 | Source attribute |

## loan_applications

| Field | CSV inferred type | Missing | Role |
|---|---|---:|---|
| application_id | object | 0 | Application or entity key |
| customer_id | object | 0 | Application or entity key |
| application_date | object | 0 | Source attribute |
| loan_type | object | 0 | Source attribute |
| loan_purpose | object | 0 | Source attribute |
| requested_amount | int64 | 0 | Source attribute |
| loan_term_months | int64 | 0 | Source attribute |
| interest_rate | float64 | 0 | Source attribute |
| applicant_monthly_income | int64 | 0 | Source attribute |
| existing_emi | int64 | 0 | Source attribute |
| debt_to_income_ratio | float64 | 0 | Source attribute |
| collateral_flag | int64 | 0 | Source attribute |
| approval_status | object | 0 | Source attribute |
| approved_amount | int64 | 0 | Source attribute |
| decision_date | object | 173 | Source attribute |
| disbursed_flag | int64 | 0 | Source attribute |
| loan_default | float64 | 4097 | Observed target only for disbursed loans |

## transactions

| Field | CSV inferred type | Missing | Role |
|---|---|---:|---|
| transaction_id | object | 0 | Application or entity key |
| customer_id | object | 0 | Application or entity key |
| transaction_date | object | 0 | Source attribute |
| transaction_type | object | 0 | Source attribute |
| category | object | 0 | Source attribute |
| channel | object | 0 | Source attribute |
| amount | float64 | 0 | Source attribute |
| balance_after | float64 | 0 | Source attribute |

## Engineered fields

| Feature | Construction |
|---|---|
| age_at_application | (application date − birth date) / 365.25 days |
| customer_tenure_months | max(0, application date − customer since) / 30.4375 days |
| debt_to_limit | outstanding debt / positive credit limit |
| loan_to_income | requested amount / positive annual income |
| total_inflow_6m | Sum of Credit amounts in six-month window |
| total_outflow_6m | Sum of Debit amounts in six-month window |
| net_cashflow_6m | Inflow minus outflow |
| emi_outflow_6m | Debit amounts categorised EMI |
| average_balance_6m | Mean observed balance_after; not daily average |
| transaction_count_6m | Number of observed transactions |
| inflow_to_outflow_ratio | Inflow / positive outflow |

Retrospective window: January 1 to June 29 2024. Application-time window: six calendar months before each application, excluding the application day. Absence of history is missing, not an invented zero cashflow.

## Scored tables

scored_applications has one row per application with probability, integer risk score, category, predicted_default at the chosen threshold and scoring_context. scored_customers has one row per customer, source_application_id and score_basis. Version 2 application scores use request-time inputs. Every customer score comes from the separate actual-profile model; source_application_id is NULL and score_basis is customer_profile_model. No loan scenario is generated. No names or contacts appear in these tables.

## SQL and dashboard denominator definitions

Approval rate = Approved / (Approved + Rejected). Default rate = sum(loan_default) / count(observed disbursed loans). Disbursed value = sum(approved_amount) on disbursed records. Customer mix = unique customer scores. Month is application cohort, not default-event month. State bars count applications and expose approval rate and value in hover details.

## Source field semantics

Credit score is the supplied CIBIL-style 300–900 value. Credit utilisation is outstanding balance divided by sanctioned limit, in [0,1]. Bureau late-payment counts distinguish 30-day and 90-day delinquency; num_defaults_prior and bankruptcies are historical counts at the snapshot. Inquiries refer to six months and oldest_account_age_months measures credit history length. Open accounts, limits and debt are bureau snapshot attributes.

Annual income and applicant monthly income are distinct supplied fields. Existing EMI is the existing monthly obligation, and DTI includes existing plus proposed loan EMI divided by monthly income. Requested amount and term describe the requested loan; approved_amount is the sanctioned amount and is excluded from modelling. Offered annual interest rate is expressed as percent, not a decimal rate. Collateral and disbursed flags are binary. Approval status distinguishes Approved, Rejected and Under Review; non-disbursed outcomes remain NULL.

Gender, marital status, education, employment type, occupation and dependents describe the supplied customer profile. Residence type and years_at_residence describe housing stability. city and state are geography for analytics. KYC status is the supplied verification state. Age is the supplied profile age and is replaced by application-date age for modelling. customer_since is the recorded relationship start date.

Transaction type marks Credit or Debit, category describes purpose, channel describes payment rail, amount is positive INR, and balance_after is the recorded resulting balance. Dates and record IDs identify the corresponding customer, bureau pull, loan application or transaction. Raw values such as transaction categories are retained rather than forced into the PRD illustrative sample list.


## Version 2 scoring contract

The active applicant feature set excludes all undated demographics, offered interest rate, supplied underwriting DTI and bureau fields. Derived payment burden uses existing EMI / declared monthly income; request-to-income uses monthly income ×12; principal instalment burden uses requested amount / term / declared income. Histories are strictly before application. Customer features use actual profiles and snapshots and are explicitly retrospective. See feature_contracts.md for the exact persisted feature lists and historical_data_contract.md for missing provenance.
