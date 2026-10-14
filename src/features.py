"""Application-grain features, with explicit retrospective/as-of contexts."""
import numpy as np
import pandas as pd
from .config import AS_OF

DEMOGRAPHICS = ['age_at_application', 'dependents', 'employment_type', 'education',
                'residence_type', 'years_at_residence', 'annual_income', 'customer_tenure_months']
BUREAU = ['credit_score', 'num_open_accounts', 'num_credit_inquiries_6m', 'credit_utilization_ratio',
          'num_late_payments_30d', 'num_late_payments_90d', 'num_defaults_prior', 'bankruptcies',
          'total_credit_limit', 'total_outstanding_debt', 'oldest_account_age_months', 'debt_to_limit']
APPLICATION = ['requested_amount', 'interest_rate', 'loan_term_months', 'debt_to_income_ratio',
               'loan_type', 'collateral_flag', 'applicant_monthly_income', 'existing_emi', 'loan_to_income']
BEHAVIOR = ['total_inflow_6m', 'total_outflow_6m', 'net_cashflow_6m', 'emi_outflow_6m',
            'average_balance_6m', 'transaction_count_6m', 'inflow_to_outflow_ratio']
CATEGORICAL = ['employment_type', 'education', 'residence_type', 'loan_type']
FEATURES = DEMOGRAPHICS + BUREAU + APPLICATION + BEHAVIOR
STRICT_APPLICATION = ['requested_amount', 'loan_term_months', 'loan_type', 'loan_purpose',
                      'collateral_flag', 'applicant_monthly_income', 'existing_emi',
                      'existing_payment_to_income', 'request_to_declared_annual_income',
                      'principal_installment_to_income', 'log_requested_amount',
                      'log_monthly_income', 'history_available']
STRICT_FEATURES = STRICT_APPLICATION + BEHAVIOR
PROFILE_FEATURES = ['age_at_snapshot', 'dependents', 'employment_type', 'education',
                    'residence_type', 'years_at_residence', 'annual_income',
                    'customer_tenure_months'] + BUREAU + BEHAVIOR
PROFILE_FEATURES += ['credit_below_650', 'credit_below_750', 'utilization_above_70',
                     'any_prior_default', 'log_income', 'log_outstanding_debt']
EXCLUDED = ['first_name','last_name','email','phone','gender','city','state','approval_status',
            'approved_amount','decision_date','disbursed_flag','loan_default','customer_id','application_id']

def safe_divide(a, b):
    return a.div(b.where(b > 0)).replace([np.inf, -np.inf], np.nan)

def aggregate_transactions(transactions, key='customer_id'):
    t = transactions.copy()
    t['inflow'] = t.amount.where(t.transaction_type.eq('Credit'), 0)
    t['outflow'] = t.amount.where(t.transaction_type.eq('Debit'), 0)
    t['emi'] = t.amount.where(t.transaction_type.eq('Debit') & t.category.eq('EMI'), 0)
    a = t.groupby(key).agg(total_inflow_6m=('inflow','sum'),
        total_outflow_6m=('outflow','sum'), emi_outflow_6m=('emi','sum'),
        average_balance_6m=('balance_after','mean'), transaction_count_6m=('transaction_id','count')).reset_index()
    a['net_cashflow_6m'] = a.total_inflow_6m - a.total_outflow_6m
    a['inflow_to_outflow_ratio'] = safe_divide(a.total_inflow_6m, a.total_outflow_6m)
    return a

def build(frames, context='retrospective', applications=None):
    if context not in ['retrospective', 'application_time']:
        raise ValueError('Unknown feature context')
    loans = frames['loan_applications'] if applications is None else applications
    d = loans.merge(frames['customers'], on='customer_id', validate='many_to_one')
    d = d.merge(frames['credit_history'], on='customer_id', validate='many_to_one')
    dates = pd.to_datetime(d.application_date)
    dob = pd.to_datetime(d.date_of_birth)
    d['age_at_application'] = (dates-dob).dt.days / 365.25
    d['customer_tenure_months'] = (dates-pd.to_datetime(d.customer_since)).dt.days.div(30.4375).clip(lower=0)
    d['debt_to_limit'] = safe_divide(d.total_outstanding_debt, d.total_credit_limit)
    d['loan_to_income'] = safe_divide(d.requested_amount, d.annual_income)
    if context == 'retrospective':
        t = frames['transactions']
        cutoff = pd.Timestamp(AS_OF)
        tdates = pd.to_datetime(t.transaction_date)
        t = t.loc[(tdates >= cutoff-pd.DateOffset(months=6)) & (tdates < cutoff)]
        d = d.merge(aggregate_transactions(t), on='customer_id', how='left', validate='many_to_one')
    else:
        # Bureau snapshots newer than the decision cannot be used historically.
        unavailable = pd.to_datetime(d.as_of_date) > dates
        d.loc[unavailable, BUREAU] = np.nan
        # Intentional temporary application-transaction pairs, collapsed before
        # feature join. Vectorised date filtering avoids thousands of groupbys.
        pairs = d[['application_id','customer_id','application_date']].merge(
            frames['transactions'], on='customer_id', how='inner')
        application_dates = pd.to_datetime(pairs.application_date)
        transaction_dates = pd.to_datetime(pairs.transaction_date)
        pairs = pairs.loc[(transaction_dates < application_dates) &
                          (transaction_dates >= application_dates-pd.DateOffset(months=6))]
        aggregates = aggregate_transactions(pairs, key='application_id')
        d = d.merge(aggregates, on='application_id', how='left', validate='one_to_one')
    if len(d) != len(loans):
        raise AssertionError('Join changed application grain')
    return d

def strict_application_features(frames, applications=None):
    """Submitted request fields and strictly earlier transactions only.

    Offered rates, underwriting DTI and undated profiles never enter X.
    Request columns are assumed captured at application; the source lacks
    independent field capture timestamps and default observation horizons.
    """
    d = (frames['loan_applications'] if applications is None else applications).copy()
    if d.application_id.duplicated().any():
        raise ValueError('Request application IDs must be unique')
    pairs = d[['application_id','customer_id','application_date']].merge(
        frames['transactions'],on='customer_id',how='inner')
    ad = pd.to_datetime(pairs.application_date)
    td = pd.to_datetime(pairs.transaction_date)
    pairs = pairs.loc[(td < ad) & (td >= ad-pd.DateOffset(months=6))]
    aggregates = aggregate_transactions(pairs,key='application_id')
    d = d.merge(aggregates,on='application_id',how='left',validate='one_to_one')
    income = d.applicant_monthly_income
    d['existing_payment_to_income'] = safe_divide(d.existing_emi, income)
    d['request_to_declared_annual_income'] = safe_divide(d.requested_amount, income * 12)
    d['principal_installment_to_income'] = safe_divide(
        safe_divide(d.requested_amount, d.loan_term_months), income)
    d['log_requested_amount'] = np.log1p(d.requested_amount.clip(lower=0))
    d['log_monthly_income'] = np.log1p(income.clip(lower=0))
    d['history_available'] = d.transaction_count_6m.notna().astype(int)
    keep = ['application_id','customer_id','application_date'] + STRICT_FEATURES
    keep += [c for c in ['loan_default','disbursed_flag'] if c in d]
    return d[keep].copy()

def customer_profile_features(frames):
    """One actual profile per customer, without invented application fields."""
    d = frames['customers'].merge(frames['credit_history'],on='customer_id',validate='one_to_one')
    cutoff = pd.Timestamp(AS_OF)
    d['age_at_snapshot'] = (cutoff-pd.to_datetime(d.date_of_birth)).dt.days / 365.25
    d['customer_tenure_months'] = ((cutoff-pd.to_datetime(d.customer_since)).dt.days / 30.4375).clip(lower=0)
    d['debt_to_limit'] = safe_divide(d.total_outstanding_debt,d.total_credit_limit)
    t = frames['transactions']
    td = pd.to_datetime(t.transaction_date)
    t = t.loc[(td < cutoff) & (td >= cutoff-pd.DateOffset(months=6))]
    d = d.merge(aggregate_transactions(t),on='customer_id',how='left',validate='one_to_one')
    d['credit_below_650'] = d.credit_score.lt(650).astype(int)
    d['credit_below_750'] = d.credit_score.lt(750).astype(int)
    d['utilization_above_70'] = d.credit_utilization_ratio.gt(.7).astype(int)
    d['any_prior_default'] = d.num_defaults_prior.gt(0).astype(int)
    d['log_income'] = np.log1p(d.annual_income.clip(lower=0))
    d['log_outstanding_debt'] = np.log1p(d.total_outstanding_debt.clip(lower=0))
    return d[['customer_id',*PROFILE_FEATURES]].copy()

def retrospective_enhanced_features(frames):
    """Domain transforms for a development-only challenger investigation."""
    d = build(frames)
    columns = ['requested_amount','annual_income','total_outstanding_debt',
               'total_inflow_6m','total_outflow_6m','loan_to_income','debt_to_income_ratio']
    for col in columns:
        d['log_'+col] = np.log1p(d[col].clip(lower=0))
    d['credit_below_650'] = d.credit_score.lt(650).astype(int)
    d['credit_below_750'] = d.credit_score.lt(750).astype(int)
    d['dti_above_50'] = d.debt_to_income_ratio.gt(.5).astype(int)
    d['utilization_above_70'] = d.credit_utilization_ratio.gt(.7).astype(int)
    d['any_prior_default'] = d.num_defaults_prior.gt(0).astype(int)
    d['cashflow_negative'] = d.net_cashflow_6m.lt(0).astype(int)
    extra = ['log_'+col for col in columns]
    extra += ['credit_below_650','credit_below_750','dti_above_50','utilization_above_70',
              'any_prior_default','cashflow_negative']
    return d, FEATURES + extra
