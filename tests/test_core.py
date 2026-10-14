import sqlite3
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from src.risk_score import score
from src.features import aggregate_transactions, safe_divide, FEATURES, EXCLUDED
from src.data_load import native

ROOT=Path(__file__).resolve().parents[1]

class RiskTests(unittest.TestCase):
    def test_nullable_numpy_integer_serializes_as_sql_integer(self):
        value=native(np.int64(1))
        self.assertIsInstance(value,int)
        self.assertIsNone(native(pd.NA))
    def test_risk_band_boundaries(self):
        s=score([0,.33,.34,.66,.67,1])
        self.assertEqual(s.risk_score.tolist(),[0,33,34,66,67,100])
        self.assertEqual(s.risk_category.tolist(),['Low Risk','Low Risk','Medium Risk','Medium Risk','High Risk','High Risk'])
    def test_reject_invalid_probabilities(self):
        for p in [[-0.1],[1.1],[np.nan],[np.inf]]:
            with self.assertRaises(ValueError):score(p)
    def test_no_target_decision_or_personal_features(self):
        self.assertFalse(set(FEATURES)&set(EXCLUDED))
    def test_zero_denominator_missing(self):
        self.assertTrue(np.isnan(safe_divide(pd.Series([1]),pd.Series([0])).iloc[0]))
    def test_customer_aggregation_prevents_row_multiplication(self):
        t=pd.DataFrame({'customer_id':['C1']*3,'transaction_id':['T1','T2','T3'],
            'transaction_type':['Credit','Debit','Debit'],'category':['Salary','EMI','Shopping'],
            'amount':[100,30,20],'balance_after':[100,70,50]})
        a=aggregate_transactions(t)
        self.assertEqual(len(a),1)
        self.assertEqual(a.total_inflow_6m.iloc[0],100)
        self.assertEqual(a.total_outflow_6m.iloc[0],50)
        self.assertEqual(a.emi_outflow_6m.iloc[0],30)
        self.assertEqual(a.net_cashflow_6m.iloc[0],50)

class ConstraintTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:');self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript((ROOT/'sql/schema.sql').read_text())
        self.db.execute("INSERT INTO customers(customer_id,first_name,last_name,date_of_birth,customer_since) VALUES ('C1','Test','Person','1990-01-01','2020-01-01')")
    def tearDown(self):self.db.close()
    def test_orphan_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO credit_history(credit_id,customer_id,as_of_date) VALUES ('CR1','MISSING','2024-01-01')")
    def test_score_range_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO credit_history(credit_id,customer_id,as_of_date,credit_score) VALUES ('CR1','C1','2024-01-01',999)")
    def test_duplicate_primary_key_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO customers(customer_id,first_name,last_name,date_of_birth,customer_since) VALUES ('C1','Test','Person','1990-01-01','2020-01-01')")
    def test_non_disbursed_label_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO loan_applications(application_id,customer_id,application_date,loan_type,approval_status,disbursed_flag,loan_default) VALUES ('A1','C1','2024-01-01','Personal','Rejected',0,1)")
    def test_reversed_decision_date_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO loan_applications(application_id,customer_id,application_date,loan_type,approval_status,disbursed_flag,decision_date) VALUES ('A1','C1','2024-01-02','Personal','Rejected',0,'2024-01-01')")
    def test_score_category_mismatch_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO scored_customers(customer_id,default_probability,risk_score,risk_category,score_basis) VALUES ('C1',.8,80,'Low Risk','test')")

if __name__=='__main__':unittest.main()
