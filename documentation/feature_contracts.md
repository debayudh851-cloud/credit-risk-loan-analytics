# Feature availability contracts

The two populations have distinct estimands. A current customer profile is never substituted into a historical application.

## Applicant features

Source: submitted request fields and strictly earlier transactions. Assumes request fields were captured at the application; field capture timestamps are unavailable.

- requested_amount
- loan_term_months
- loan_type
- loan_purpose
- collateral_flag
- applicant_monthly_income
- existing_emi
- existing_payment_to_income
- request_to_declared_annual_income
- principal_installment_to_income
- log_requested_amount
- log_monthly_income
- history_available
- total_inflow_6m
- total_outflow_6m
- net_cashflow_6m
- emi_outflow_6m
- average_balance_6m
- transaction_count_6m
- inflow_to_outflow_ratio

## Customer profile features

Source: actual customer and June 30 2024 bureau records plus January–June account transactions. Historical default association; no loan scenario or future-horizon claim.

- age_at_snapshot
- dependents
- employment_type
- education
- residence_type
- years_at_residence
- annual_income
- customer_tenure_months
- credit_score
- num_open_accounts
- num_credit_inquiries_6m
- credit_utilization_ratio
- num_late_payments_30d
- num_late_payments_90d
- num_defaults_prior
- bankruptcies
- total_credit_limit
- total_outstanding_debt
- oldest_account_age_months
- debt_to_limit
- total_inflow_6m
- total_outflow_6m
- net_cashflow_6m
- emi_outflow_6m
- average_balance_6m
- transaction_count_6m
- inflow_to_outflow_ratio
- credit_below_650
- credit_below_750
- utilization_above_70
- any_prior_default
- log_income
- log_outstanding_debt

## Historical data needed for prospective validation

Supply customer_id, effective_from and captured_at for profile history; bureau snapshots with pull timestamps; loan outcome event date, observation_end, default definition and horizon. A snapshot later than application is rejected or omitted rather than backdated.