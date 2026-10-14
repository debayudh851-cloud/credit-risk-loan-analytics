"""Two separate scoring contracts: historical request-time and customer profile."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import time
import numpy as np
import pandas as pd
from .config import ROOT,OUT,DATA,prepare
from .data_load import read_raw,load,write_scores
from .features import strict_application_features,STRICT_FEATURES,PROFILE_FEATURES
from .modeling import train
from .customer_model import run as score_customers
from .risk_score import score
from .explain import explain
from .analytics import run_queries,charts
from .validation import temporal_audit,acceptance

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database-url',default=os.getenv('CREDORA_DATABASE_URL'))
    parser.add_argument('--skip-time-audit',action='store_true')
    args = parser.parse_args()
    prepare()
    started = time.perf_counter()
    baseline = ROOT/'.local/v1_baseline/artifacts/metrics.json'
    if baseline.exists() and not (OUT/'v1_metrics.json').exists():
        shutil.copy2(baseline,OUT/'v1_metrics.json')
    frozen = pd.read_csv(OUT/'split_manifest.csv') if (OUT/'split_manifest.csv').exists() else None
    frames = read_raw()
    quality = load(frames,args.database_url)
    print('Building request-time features without future bureau/profile fields...',flush=True)
    features = strict_application_features(frames)
    features.to_csv(OUT/'application_features.csv',index=False)
    model,base,result = train(features,features=STRICT_FEATURES,
        context='strict_application_time',frozen_split=frozen)
    p = model.predict_proba(features[STRICT_FEATURES])[:,1]
    applications = score(p)
    applications.insert(0,'customer_id',features.customer_id.values)
    applications.insert(0,'application_id',features.application_id.values)
    applications['predicted_default'] = (p >= result['threshold']).astype(int)
    applications['scoring_context'] = 'strict_application_time'
    applications.to_csv(OUT/'scored_applications.csv',index=False)
    print('Explaining request-time scores...',flush=True)
    info = explain(base,features,model,features=STRICT_FEATURES)
    print('Training actual customer-profile model; no reference loan scenarios...',flush=True)
    customers,customer_model,customer_result = score_customers(frames)
    customers = customers.sort_values('customer_id').reset_index(drop=True)
    customers.to_csv(OUT/'scored_customers.csv',index=False)
    write_scores(applications,customers,args.database_url)
    timings = run_queries(args.database_url)
    summary = charts(frames)
    audit = None
    if not args.skip_time_audit:
        print('Running fixed-calendar request-time sensitivity audit...',flush=True)
        audit = temporal_audit(features,{'model':model,'features':STRICT_FEATURES,
                                        'threshold':result['threshold']})
        (OUT/'application_time_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    public = frames['loan_applications'].merge(
        frames['customers'][['customer_id','state','city']],on='customer_id',validate='many_to_one')
    public = public.merge(applications,on=['application_id','customer_id'],validate='one_to_one')
    public.to_csv(OUT/'dashboard_applications.csv',index=False)
    watch = customers.merge(frames['customers'][['customer_id','state','city']],
        on='customer_id',validate='one_to_one').merge(
        frames['credit_history'][['customer_id','credit_score']],on='customer_id',validate='one_to_one')
    watch.to_csv(OUT/'dashboard_customers.csv',index=False)
    frames['credit_history'][['customer_id','as_of_date','credit_score']].to_csv(OUT/'dashboard_credit.csv',index=False)
    manifest = {
        'version':2,'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(DATA.glob('*.csv'))},
        'packages':{p:importlib.metadata.version(p) for p in ['pandas','numpy','scikit-learn','xgboost','shap','streamlit']},
        'total_seconds':time.perf_counter()-started,'engine':quality['engine'],
        'customer_scores':len(customers),'application_scores':len(applications),'sql_queries':len(timings),
        'hypothetical_applications':0,'application_context':'strict_application_time',
        'customer_context':'customer_profile_retrospective',
        'total_model_training_seconds':result['training_seconds']+customer_result['training_seconds']}
    (OUT/'run_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    status = acceptance(result,customer_result,manifest)
    from .reporting import write_reports
    write_reports(result,customer_result,summary,audit,manifest,info,timings,frames,status)
    print(json.dumps({'applicant_model':result['champion'],'applicant_test':result['test_metrics'],
                      'customer_model':customer_result['champion'],'customer_test':customer_result['test_metrics'],
                      'acceptance':status,'total_seconds':manifest['total_seconds']},indent=2),flush=True)

if __name__ == '__main__':
    main()
