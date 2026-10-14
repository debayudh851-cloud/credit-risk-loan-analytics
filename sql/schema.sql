-- Portable relational DDL for PostgreSQL 14+ and SQLite 3.
-- No destructive DROP statements or embedded PII seed rows.
CREATE TABLE IF NOT EXISTS customers (
 customer_id VARCHAR(12) PRIMARY KEY NOT NULL, first_name VARCHAR(50) NOT NULL,
 last_name VARCHAR(50) NOT NULL, gender VARCHAR(10) CHECK(gender IN ('Male','Female','Other')),
 date_of_birth DATE NOT NULL, age INTEGER CHECK(age BETWEEN 18 AND 100),
 marital_status VARCHAR(15), dependents INTEGER CHECK(dependents>=0), education VARCHAR(30),
 employment_type VARCHAR(20), occupation VARCHAR(60), annual_income NUMERIC CHECK(annual_income>=0),
 city VARCHAR(50), state VARCHAR(50), residence_type VARCHAR(20),
 years_at_residence INTEGER CHECK(years_at_residence>=0), email VARCHAR(120) UNIQUE,
 phone VARCHAR(20), kyc_status VARCHAR(15) CHECK(kyc_status IN ('Verified','Pending','Rejected')),
 customer_since DATE NOT NULL
);
CREATE TABLE IF NOT EXISTS credit_history (
 credit_id VARCHAR(12) PRIMARY KEY NOT NULL,
 customer_id VARCHAR(12) NOT NULL UNIQUE REFERENCES customers(customer_id) ON DELETE CASCADE,
 as_of_date DATE NOT NULL, credit_score INTEGER CHECK(credit_score BETWEEN 300 AND 900),
 num_open_accounts INTEGER CHECK(num_open_accounts>=0), num_credit_inquiries_6m INTEGER CHECK(num_credit_inquiries_6m>=0),
 credit_utilization_ratio NUMERIC CHECK(credit_utilization_ratio BETWEEN 0 AND 1),
 num_late_payments_30d INTEGER CHECK(num_late_payments_30d>=0),
 num_late_payments_90d INTEGER CHECK(num_late_payments_90d>=0),
 num_defaults_prior INTEGER CHECK(num_defaults_prior>=0), bankruptcies INTEGER CHECK(bankruptcies>=0),
 total_credit_limit NUMERIC CHECK(total_credit_limit>=0), total_outstanding_debt NUMERIC CHECK(total_outstanding_debt>=0),
 oldest_account_age_months INTEGER CHECK(oldest_account_age_months>=0)
);
CREATE TABLE IF NOT EXISTS loan_applications (
 application_id VARCHAR(12) PRIMARY KEY NOT NULL,
 customer_id VARCHAR(12) NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
 application_date DATE NOT NULL, loan_type VARCHAR(20) NOT NULL,
 loan_purpose VARCHAR(50), requested_amount NUMERIC CHECK(requested_amount>0),
 loan_term_months INTEGER CHECK(loan_term_months>0), interest_rate NUMERIC CHECK(interest_rate>=0),
 applicant_monthly_income NUMERIC CHECK(applicant_monthly_income>=0), existing_emi NUMERIC CHECK(existing_emi>=0),
 debt_to_income_ratio NUMERIC CHECK(debt_to_income_ratio>=0), collateral_flag INTEGER CHECK(collateral_flag IN (0,1)),
 approval_status VARCHAR(15) NOT NULL CHECK(approval_status IN ('Approved','Rejected','Under Review')),
 approved_amount NUMERIC CHECK(approved_amount>=0), decision_date DATE,
 disbursed_flag INTEGER NOT NULL CHECK(disbursed_flag IN (0,1)),
 loan_default INTEGER CHECK(loan_default IN (0,1)),
 CHECK(decision_date IS NULL OR decision_date>=application_date),
 CHECK((disbursed_flag=1 AND loan_default IS NOT NULL AND approval_status='Approved') OR
       (disbursed_flag=0 AND loan_default IS NULL)),
 CHECK(approval_status='Approved' OR approved_amount=0)
);
CREATE TABLE IF NOT EXISTS transactions (
 transaction_id VARCHAR(14) PRIMARY KEY NOT NULL,
 customer_id VARCHAR(12) NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
 transaction_date DATE NOT NULL, transaction_type VARCHAR(10) CHECK(transaction_type IN ('Credit','Debit')),
 category VARCHAR(30), channel VARCHAR(20), amount NUMERIC CHECK(amount>=0), balance_after NUMERIC
);
CREATE TABLE IF NOT EXISTS scored_applications (
 application_id VARCHAR(12) PRIMARY KEY REFERENCES loan_applications(application_id) ON DELETE CASCADE,
 customer_id VARCHAR(12) NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
 default_probability NUMERIC NOT NULL CHECK(default_probability BETWEEN 0 AND 1),
 risk_score INTEGER NOT NULL CHECK(risk_score BETWEEN 0 AND 100),
 risk_category VARCHAR(20) NOT NULL CHECK(risk_category IN ('Low Risk','Medium Risk','High Risk')),
 predicted_default INTEGER NOT NULL CHECK(predicted_default IN (0,1)),
 scoring_context VARCHAR(40) NOT NULL,
 CHECK((risk_score<=33 AND risk_category='Low Risk') OR (risk_score BETWEEN 34 AND 66 AND risk_category='Medium Risk') OR
       (risk_score>=67 AND risk_category='High Risk'))
);
CREATE TABLE IF NOT EXISTS scored_customers (
 customer_id VARCHAR(12) PRIMARY KEY REFERENCES customers(customer_id) ON DELETE CASCADE,
 default_probability NUMERIC NOT NULL CHECK(default_probability BETWEEN 0 AND 1),
 risk_score INTEGER NOT NULL CHECK(risk_score BETWEEN 0 AND 100),
 risk_category VARCHAR(20) NOT NULL CHECK(risk_category IN ('Low Risk','Medium Risk','High Risk')),
 source_application_id VARCHAR(12) REFERENCES loan_applications(application_id) ON DELETE SET NULL,
 score_basis VARCHAR(40) NOT NULL,
 CHECK((risk_score<=33 AND risk_category='Low Risk') OR (risk_score BETWEEN 34 AND 66 AND risk_category='Medium Risk') OR
       (risk_score>=67 AND risk_category='High Risk'))
);
CREATE INDEX IF NOT EXISTS idx_credit_score ON credit_history(credit_score);
CREATE INDEX IF NOT EXISTS idx_loan_customer ON loan_applications(customer_id);
CREATE INDEX IF NOT EXISTS idx_loan_date ON loan_applications(application_date);
CREATE INDEX IF NOT EXISTS idx_loan_status ON loan_applications(approval_status);
CREATE INDEX IF NOT EXISTS idx_loan_default ON loan_applications(loan_default);
CREATE INDEX IF NOT EXISTS idx_txn_customer_date ON transactions(customer_id,transaction_date);
CREATE INDEX IF NOT EXISTS idx_txn_category ON transactions(category);
CREATE INDEX IF NOT EXISTS idx_risk_category ON scored_customers(risk_category);
