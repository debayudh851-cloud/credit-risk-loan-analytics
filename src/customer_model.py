"""Customer-specific risk without an invented loan request."""
import pandas as pd
from .config import OUT
from .features import PROFILE_FEATURES,customer_profile_features
from .modeling import train
from .risk_score import score
from .explain import explain

def run(frames):
    profiles = customer_profile_features(frames)
    observed = frames['loan_applications'].loc[frames['loan_applications'].loan_default.notna()]
    # One latest observed loan outcome per customer; outcome missing stays missing.
    latest = observed.sort_values(['application_date','application_id']).drop_duplicates('customer_id',keep='last')
    targets = latest[['customer_id','loan_default']]
    labelled = profiles.merge(targets,on='customer_id',how='left',validate='one_to_one')
    directory = OUT/'customer_model'
    model,base,result = train(labelled,features=PROFILE_FEATURES,
        context='customer_profile_retrospective',output_dir=directory,
        artifact_name='customer_model.pkl',key='customer_id')
    scored = score(model.predict_proba(profiles[PROFILE_FEATURES])[:,1])
    scored.insert(0,'customer_id',profiles.customer_id.values)
    scored['source_application_id'] = None
    scored['score_basis'] = 'customer_profile_model'
    profiles.to_csv(OUT/'customer_features.csv',index=False)
    labelled[['customer_id','loan_default']].to_csv(directory/'observed_targets.csv',index=False)
    explain(base,profiles,model,features=PROFILE_FEATURES,output_dir=directory,key='customer_id')
    return scored,model,result
