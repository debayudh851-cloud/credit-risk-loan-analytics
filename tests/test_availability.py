import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from src.features import strict_application_features,STRICT_FEATURES,PROFILE_FEATURES,customer_profile_features
from src.data_load import read_raw
from src.score_requests import score_requests

class AvailabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frames=read_raw()

    def test_contract_excludes_future_and_undated_inputs(self):
        forbidden={'credit_score','annual_income','employment_type','age','age_at_application',
                   'interest_rate','debt_to_income_ratio','loan_default','decision_date','approved_amount','approval_status'}
        self.assertFalse(forbidden.intersection(STRICT_FEATURES))

    def test_request_features_do_not_read_customer_or_bureau_tables(self):
        source={'loan_applications':self.frames['loan_applications'].head(30),
                'transactions':self.frames['transactions']}
        actual=strict_application_features(source)
        self.assertEqual(len(actual),30)
        self.assertFalse({'credit_score','annual_income'}.intersection(actual.columns))

    def test_future_transactions_cannot_change_old_request_features(self):
        requests=self.frames['loan_applications'].head(30)
        before=strict_application_features({'loan_applications':requests,'transactions':self.frames['transactions']})
        transactions=self.frames['transactions'].copy()
        future=transactions.iloc[:20].copy()
        future['transaction_date']='2030-01-01'
        future['amount']=1e12
        future['balance_after']=-1e12
        after=strict_application_features({'loan_applications':requests,
                                          'transactions':pd.concat([transactions,future],ignore_index=True)})
        pd.testing.assert_frame_equal(before,after)

    def test_customer_profiles_need_no_loan_table(self):
        source={k:v for k,v in self.frames.items() if k!='loan_applications'}
        profiles=customer_profile_features(source)
        self.assertEqual(len(profiles),5000)
        self.assertTrue(profiles.customer_id.is_unique)
        self.assertFalse({'requested_amount','loan_type','loan_term_months','loan_to_income'}.intersection(PROFILE_FEATURES))

    def test_batch_rejects_retrospective_model(self):
        with self.assertRaisesRegex(ValueError,'strict request-time model'):
            score_requests(self.frames['loan_applications'].head(1),self.frames['transactions'],{'context':'retrospective'})

if __name__=='__main__':unittest.main()
