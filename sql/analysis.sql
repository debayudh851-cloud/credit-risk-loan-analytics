-- Q01 Credit score analysis
SELECT CASE WHEN credit_score>=750 THEN 'Excellent' WHEN credit_score>=650 THEN 'Good'
 WHEN credit_score>=550 THEN 'Fair' ELSE 'Poor' END AS score_band,
 COUNT(*) AS customers, AVG(credit_score) AS average_score
FROM credit_history GROUP BY 1 ORDER BY average_score DESC;
-- Q02 Approval trends by loan type (exclude pending from denominator)
SELECT loan_type, COUNT(*) AS applications,
 SUM(CASE WHEN approval_status='Approved' THEN 1 ELSE 0 END) AS approved,
 100.0*SUM(CASE WHEN approval_status='Approved' THEN 1 ELSE 0 END)/
 NULLIF(SUM(CASE WHEN approval_status!='Under Review' THEN 1 ELSE 0 END),0) AS approval_rate_pct
FROM loan_applications GROUP BY loan_type;
-- Q03 Customer segmentation, preserve customer grain
SELECT c.employment_type, COUNT(*) AS customers, AVG(c.annual_income) AS average_income,
 AVG(h.credit_score) AS average_credit_score FROM customers c
JOIN credit_history h USING(customer_id) GROUP BY c.employment_type;
-- Q04 Model high risk watchlist without contact fields
SELECT s.customer_id,c.state,c.city,s.default_probability,s.risk_score,s.score_basis,
 h.credit_score FROM scored_customers s JOIN customers c USING(customer_id)
JOIN credit_history h USING(customer_id) WHERE s.risk_category='High Risk'
ORDER BY s.default_probability DESC,s.customer_id;
-- Q05 Observed default rates only where outcome exists
SELECT loan_type, COUNT(*) AS disbursed, SUM(loan_default) AS defaults,
 100.0*AVG(loan_default) AS default_rate_pct FROM loan_applications
WHERE disbursed_flag=1 AND loan_default IS NOT NULL GROUP BY loan_type;
-- Q06 Requested amount distribution
SELECT loan_type, MIN(requested_amount) AS minimum, MAX(requested_amount) AS maximum,
 AVG(requested_amount) AS mean, AVG(approved_amount) AS mean_sanctioned_all_apps
FROM loan_applications GROUP BY loan_type;
-- Q07 Monthly applications and decisions (application cohort)
SELECT SUBSTR(CAST(application_date AS VARCHAR(20)),1,7) AS month, COUNT(*) AS applications,
 SUM(CASE WHEN approval_status='Approved' THEN 1 ELSE 0 END) AS approved,
 SUM(CASE WHEN approval_status='Rejected' THEN 1 ELSE 0 END) AS rejected,
 SUM(CASE WHEN approval_status='Under Review' THEN 1 ELSE 0 END) AS pending,
 SUM(approved_amount) AS sanctioned_value FROM loan_applications GROUP BY 1 ORDER BY 1;
-- Q08 Model customer risk categorisation
SELECT risk_category,COUNT(*) AS customers,AVG(risk_score) AS average_risk_score
FROM scored_customers GROUP BY risk_category;
-- Q09 Transaction behaviour, aggregate before joining
WITH behavior AS (SELECT customer_id,COUNT(*) AS transaction_count,
 SUM(CASE WHEN transaction_type='Credit' THEN amount ELSE 0 END) AS inflow,
 SUM(CASE WHEN transaction_type='Debit' THEN amount ELSE 0 END) AS outflow,
 AVG(balance_after) AS average_balance FROM transactions GROUP BY customer_id)
SELECT c.employment_type,COUNT(*) AS customers,AVG(b.inflow) AS mean_inflow,
 AVG(b.outflow) AS mean_outflow,AVG(b.inflow-b.outflow) AS mean_net_cashflow,
 AVG(b.average_balance) AS average_balance FROM customers c LEFT JOIN behavior b USING(customer_id)
GROUP BY c.employment_type;
-- Q10 Default driver associations (retrospective, not causal importance)
SELECT CASE WHEN h.credit_score<650 THEN 'Below 650' ELSE '650 or above' END AS credit_band,
 CASE WHEN l.debt_to_income_ratio>0.5 THEN 'DTI above 0.5' ELSE 'DTI at most 0.5' END AS dti_band,
 CASE WHEN h.num_defaults_prior>0 THEN 'Prior defaults' ELSE 'No prior defaults' END AS history_band,
 c.employment_type,COUNT(*) AS observed_loans,AVG(l.loan_default)*100.0 AS default_rate_pct
FROM loan_applications l JOIN credit_history h USING(customer_id) JOIN customers c USING(customer_id)
WHERE l.disbursed_flag=1 AND l.loan_default IS NOT NULL GROUP BY 1,2,3,4 ORDER BY default_rate_pct DESC;
