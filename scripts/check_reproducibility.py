"""Run two full pipelines and compare deterministic metrics and predictions."""
import json
import argparse
import subprocess
import sys
from pathlib import Path
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts'

def capture():
    m=json.loads((OUT/'metrics.json').read_text())
    customer=json.loads((OUT/'customer_model/metrics.json').read_text())
    key_metrics={key:{name:result[name] for name in ['champion','threshold','test_metrics']} for key,result in [('application',m),('customer',customer)]}
    return key_metrics,pd.read_csv(OUT/'scored_applications.csv'),pd.read_csv(OUT/'scored_customers.csv')

parser=argparse.ArgumentParser()
parser.add_argument('--use-existing-baseline',action='store_true',help='Compare the existing full v2 run with one new full run')
args=parser.parse_args()
if not args.use_existing_baseline:
    subprocess.run([sys.executable,'-m','src.pipeline'],cwd=ROOT,check=True)
a,ap,ac=capture()
subprocess.run([sys.executable,'-m','src.pipeline'],cwd=ROOT,check=True)
b,bp,bc=capture()
assert a==b,'Metrics changed between identical seeded runs'
assert np.allclose(ap.default_probability,bp.default_probability,atol=1e-12)
assert ap[['application_id','risk_score','risk_category']].equals(bp[['application_id','risk_score','risk_category']])
assert np.allclose(ac.default_probability,bc.default_probability,atol=1e-12)
assert ac[['customer_id','risk_score','risk_category']].equals(bc[['customer_id','risk_score','risk_category']])
(OUT/'reproducibility.json').write_text(json.dumps({'applicant_metrics_identical':True,'customer_metrics_identical':True,'probabilities_equal_at_1e_12':True,'risk_scores_identical':True,'hypothetical_scenarios':0},indent=2))
print('Two full seeded runs reproduced metrics, probabilities and risk scores.')
