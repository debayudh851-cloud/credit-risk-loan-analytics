"""Batch pre-decision scoring: python -m src.score_requests --requests PATH --transactions PATH --output PATH."""
import argparse
from pathlib import Path
import joblib
import pandas as pd
from .config import ROOT
from .features import strict_application_features,STRICT_APPLICATION
from .risk_score import score

REQUIRED = ['application_id','customer_id','application_date','requested_amount',
            'loan_term_months','loan_type','loan_purpose','collateral_flag',
            'applicant_monthly_income','existing_emi']

def score_requests(requests,transactions,artifact):
    missing = set(REQUIRED)-set(requests.columns)
    if missing:
        raise ValueError(f'Missing request fields: {sorted(missing)}')
    if artifact['context'] != 'strict_application_time':
        raise ValueError('Pre-decision scoring requires the strict request-time model')
    if requests.application_id.isna().any() or requests.application_id.duplicated().any():
        raise ValueError('Request IDs must be non-null and unique')
    if not requests.requested_amount.gt(0).all() or not requests.loan_term_months.gt(0).all():
        raise ValueError('Requested amount and term must be positive')
    pd.to_datetime(requests.application_date,errors='raise')
    d = strict_application_features({'loan_applications':requests,'transactions':transactions})
    probabilities = artifact['model'].predict_proba(d[artifact['features']])[:,1]
    result = score(probabilities)
    result.insert(0,'application_id',d.application_id.values)
    result['customer_id'] = d.customer_id.values
    result['predicted_default'] = (probabilities >= artifact['threshold']).astype(int)
    result['scoring_context'] = artifact['context']
    result['features_as_of'] = d.application_date.values
    result['history_available'] = d.history_available.values
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--requests',type=Path,required=True)
    parser.add_argument('--transactions',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    model = joblib.load(ROOT/'models/default_model.pkl')
    scored = score_requests(pd.read_csv(args.requests),pd.read_csv(args.transactions),model)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    scored.to_csv(args.output,index=False)
    print(f'Scored {len(scored)} requests using request-time data only.')

if __name__ == '__main__':
    main()
