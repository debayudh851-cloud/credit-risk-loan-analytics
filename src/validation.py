"""Time audit and objective acceptance status, never synthetic validation claims."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.base import clone
from .config import OUT
from .features import STRICT_FEATURES,BUREAU,DEMOGRAPHICS
from .modeling import metrics

def temporal_audit(features,artifact):
    observed = features.loc[features.loan_default.notna()].sort_values(['application_date','application_id'])
    # Fixed calendar cutoff chosen before inspecting audit outcomes.
    train = observed.loc[observed.application_date.lt('2024-01-01')]
    test = observed.loc[observed.application_date.ge('2024-01-01')]
    model = clone(artifact['model']).fit(train[artifact['features']],train.loan_default.astype(int))
    p = model.predict_proba(test[artifact['features']])[:,1]
    result = metrics(test.loan_default.astype(int),p,artifact['threshold'])
    result.update({'context':'strict_application_time','train_before':'2024-01-01',
                   'n_train':len(train),'n_test':len(test),
                   'note':'Calendar holdout sensitivity check; outcome-event dates and maturity horizons are absent. Training labels may not have matured by the cutoff, so this is not real historical deployment validation.'})
    (OUT/'temporal_audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result

def acceptance(main,customer,manifest):
    investigation = OUT/'auc_investigation/development_cv.json'
    cv = json.loads(investigation.read_text()) if investigation.exists() else None
    result = {
        'request_time_feature_implementation':{'status':'implemented',
            'evidence':'Applicant model excludes bureau, undated profiles, offered rate, underwriting DTI and all decision outcomes; transaction window strictly precedes application.'},
        'genuine_forward_default_validation':{'status':'blocked_by_missing_data',
            'needed':['application-time bureau/profile snapshots','default-event dates','repayment observation end dates','defined default horizon'],
            'evidence':'No software change can reconstruct source history or establish outcome maturity.'},
        'roc_auc_at_least_0_80':{'status':'passed' if main['test_metrics']['roc_auc']>=.8 else 'not_met',
            'measured':main['test_metrics']['roc_auc'],'required':.8,
            'development_only_challenger_auc':None if cv is None else cv['comparison'][0]['cv_roc_auc']},
        'recall_at_least_0_70':{'status':'passed' if main['test_metrics']['recall']>=.7 else 'not_met',
            'measured':main['test_metrics']['recall'],'required':.7},
        'actual_customer_profile_scores':{'status':'implemented', 'customers':manifest['customer_scores'],
            'hypothetical_application_rows':0,'held_out_customer_auc':customer['test_metrics']['roc_auc'],
            'note':'Customer model estimates latest observed loan label association from supplied profiles. It is retrospective and not certified for unobserved borrowers.'},
        'version_control':{'status':'prepared'},'github_publication':{'status':'pending_publication'}
    }
    handover_path=OUT/'git_handover.json'
    if handover_path.exists():
        handover=json.loads(handover_path.read_text())
        result['version_control']={'status':'committed','commit':handover['local_commit']}
        result['github_publication']={'status':handover.get('publication_status','awaiting_approval'),
                                      'destination':handover.get('repository_url')}
    (OUT/'acceptance_status.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
