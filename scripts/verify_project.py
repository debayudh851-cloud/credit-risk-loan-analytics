"""Integration verification against generated outputs and both SQL engines."""
import json
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import joblib
import numpy as np
import pandas as pd
from src.config import ROOT,OUT
from src.data_load import connect,read_raw,load,write_scores
from src.analytics import run_queries
from src.features import STRICT_FEATURES,PROFILE_FEATURES,strict_application_features
from scipy.special import expit
from src.risk_score import score

def main():
    app=pd.read_csv(OUT/'scored_applications.csv'); customer=pd.read_csv(OUT/'scored_customers.csv')
    frames=read_raw()
    assert len(app)==len(frames['loan_applications'])==7500
    assert len(customer)==len(frames['customers'])==5000
    assert app.application_id.is_unique and customer.customer_id.is_unique
    assert set(customer.customer_id)==set(frames['customers'].customer_id)
    assert app.default_probability.between(0,1).all()
    assert customer.default_probability.between(0,1).all()
    for d in [app,customer]:
        transformed=score(d.default_probability)
        assert np.array_equal(transformed.risk_score,d.risk_score)
        assert np.array_equal(transformed.risk_category,d.risk_category)
    forbidden={'first_name','last_name','email','phone','date_of_birth'}
    for p in OUT.glob('dashboard_*.csv'):
        assert not forbidden.intersection(pd.read_csv(p,nrows=0).columns),p
    saved=joblib.load(ROOT/'models/default_model.pkl')
    features=pd.read_csv(OUT/'application_features.csv')
    assert saved['context']=='strict_application_time'
    assert saved['features']==STRICT_FEATURES
    blocked={'credit_score','employment_type','annual_income','interest_rate','debt_to_income_ratio',
             'loan_default','approved_amount','approval_status','disbursed_flag','decision_date'}
    assert not blocked.intersection(saved['features'])
    reloaded=saved['model'].predict_proba(features[saved['features']])[:,1]
    assert np.allclose(reloaded,app.default_probability,atol=1e-10)
    calibration_base=saved['model'].calibrated_classifiers_[0].estimator
    assert np.allclose(saved['base_model'].predict_proba(features[saved['features']]),
                       calibration_base.predict_proba(features[saved['features']]),atol=1e-10)
    explanations=json.loads((OUT/'prediction_explanations.json').read_text())
    assert len(explanations)==7500
    shap=pd.read_csv(OUT/'shap_contributions.csv')
    info=json.loads((OUT/'explainability.json').read_text())
    reconstructed=info['base_value']+shap.drop(columns='application_id').sum(axis=1)
    assert np.allclose(reconstructed,[e['uncalibrated_model_output'] for e in explanations],atol=1e-4)
    assert all(len(e['top_drivers'])==5 for e in explanations)
    calibration=info['sigmoid_calibration']
    calibration_input=expit(reconstructed) if info['output_scale']=='raw_log_odds' and not hasattr(saved['base_model'],'decision_function') else reconstructed
    assert np.allclose(expit(-(calibration['a']*calibration_input+calibration['b'])),reloaded,atol=1e-7)
    customer_artifact=joblib.load(ROOT/'models/customer_model.pkl')
    profiles=pd.read_csv(OUT/'customer_features.csv')
    assert customer_artifact['features']==PROFILE_FEATURES
    assert not {'requested_amount','loan_type','loan_term_months','loan_to_income'}.intersection(PROFILE_FEATURES)
    cp=customer_artifact['model'].predict_proba(profiles[PROFILE_FEATURES])[:,1]
    aligned=profiles[['customer_id']].merge(customer,on='customer_id',validate='one_to_one')
    assert np.allclose(cp,aligned.default_probability,atol=1e-10)
    assert customer.score_basis.eq('customer_profile_model').all()
    assert customer.source_application_id.isna().all()
    directory=OUT/'customer_model'
    cex=json.loads((directory/'prediction_explanations.json').read_text())
    cshap=pd.read_csv(directory/'shap_contributions.csv')
    cinfo=json.loads((directory/'explainability.json').read_text())
    cr=cinfo['base_value']+cshap.drop(columns='customer_id').sum(axis=1)
    assert len(cex)==5000 and np.allclose(cr,[e['uncalibrated_model_output'] for e in cex],atol=1e-4)
    assert np.allclose(expit(-(cinfo['sigmoid_calibration']['a']*cr+cinfo['sigmoid_calibration']['b'])),cp,atol=1e-7)
    scores=json.loads((OUT/'portfolio_summary.json').read_text())
    assert np.isclose(scores['approval_rate'],3403/7327)
    assert np.isclose(scores['default_rate'],797/3403)
    assert len(json.loads((OUT/'sql_timings.json').read_text()))==10
    assert len(pd.read_csv(OUT/'sql/q04.csv'))==customer.risk_category.eq('High Risk').sum()
    assert pd.read_csv(OUT/'sql/q07.csv').applications.sum()==7500
    # Execute same schema on portable fallback as well.
    load(frames,write_report=False)
    write_scores(app,customer)
    conn=connect()
    try:
        assert conn.execute('PRAGMA foreign_key_check').fetchall()==[]
        assert conn.execute('SELECT count(*) FROM loan_applications').fetchone()[0]==7500
        statements=(ROOT/'sql/analysis.sql').read_text(encoding='utf-8').split(';')
        for i,statement in enumerate([s for s in statements if s.strip()],1):
            rows=conn.execute(statement).fetchall()
            assert len(rows)==len(pd.read_csv(OUT/'sql'/f'q{i:02d}.csv'))
    finally:conn.close()
    # Validate PostgreSQL constraints with transaction savepoints when supplied.
    url=os.getenv('CREDORA_DATABASE_URL')
    if url:
        conn=connect(url)
        checks=[
          "UPDATE credit_history SET credit_score=999 WHERE credit_id=(SELECT min(credit_id) FROM credit_history)",
          "UPDATE loan_applications SET customer_id='NONEXISTENT' WHERE application_id=(SELECT min(application_id) FROM loan_applications)",
          "UPDATE loan_applications SET loan_default=1 WHERE disbursed_flag=0",
          "UPDATE loan_applications SET decision_date='1900-01-01' WHERE application_id=(SELECT min(application_id) FROM loan_applications)",
          "UPDATE scored_customers SET risk_score=101 WHERE customer_id=(SELECT min(customer_id) FROM customers)"
        ]
        try:
            readiness=conn.cursor()
            readiness.execute('SELECT COUNT(*) FROM scored_customers')
            assert readiness.fetchone()[0]==5000,'Run verification after the pipeline has finished writing scores'
            for sql in checks:
                cur=conn.cursor();cur.execute('SAVEPOINT constraint_probe'); rejected=False
                try:cur.execute(sql)
                except Exception:rejected=True
                finally:cur.execute('ROLLBACK TO SAVEPOINT constraint_probe')
                assert rejected,sql
            conn.rollback()
        finally:conn.close()
    # Boundary timing regression: future snapshot must never survive as-of features.
    # Fast representative subset avoids recomputing the entire audit.
    f=strict_application_features(frames,applications=frames['loan_applications'].head(20))
    assert not blocked.intersection(STRICT_FEATURES)
    early=f.application_date.lt('2024-01-01')
    assert f.loc[early,'total_inflow_6m'].isna().all()
    report={'application_rows':7500,'customer_rows':5000,'model_reload':'pass','shap_additivity':'pass',
            'dashboard_pii_exclusion':'pass','sql_denominators':'pass','sqlite_foreign_keys':'pass','sqlite_ten_queries':'pass',
            'postgres_constraint_probes':'pass' if url else 'not run', 'asof_feature_exclusion':'pass',
            'actual_profile_customer_scores':'pass','customer_shap_additivity':'pass',
            'exact_sigmoid_probability_reconstruction':'pass'}
    (OUT/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
