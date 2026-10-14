"""Exact additive SHAP traces for the uncalibrated selected estimator."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import shap
from joblib import Parallel,delayed
from .config import OUT
from .features import FEATURES

def _binary_shap(explainer,X):
    values=explainer.shap_values(X)
    if isinstance(values,list):
        values=values[1]
    if values.ndim==3:
        values=values[:,:,1]
    return values

def explain(base, d, calibrated, features=None, output_dir=None, key='application_id'):
    features = FEATURES if features is None else list(features)
    output_dir = OUT if output_dir is None else Path(output_dir)
    output_dir.mkdir(parents=True,exist_ok=True)
    prep = base.named_steps['preprocess']; model = base.named_steps['model']
    X = prep.transform(d[features]); names = prep.get_feature_names_out()
    if hasattr(model, 'coef_'):
        explainer=shap.LinearExplainer(model,X[:100])
        values=explainer.shap_values(X)
        expected=float(np.asarray(explainer.expected_value).reshape(-1)[-1])
        output='raw_log_odds'
        raw=model.decision_function(X)
    else:
        explainer=shap.TreeExplainer(model)
        if model.__class__.__name__=='RandomForestClassifier' and len(X)>=2000:
            values=np.concatenate(Parallel(n_jobs=2)(
                delayed(_binary_shap)(explainer,part) for part in np.array_split(X,2)),axis=0)
        else:
            values=_binary_shap(explainer,X)
        expected=float(np.asarray(explainer.expected_value).reshape(-1)[-1])
        output='raw_log_odds' if model.__class__.__name__=='XGBClassifier' else 'uncalibrated_probability'
        raw=model.predict(X,output_margin=True) if output=='raw_log_odds' else model.predict_proba(X)[:,1]
    error=float(np.max(np.abs(expected+values.sum(axis=1)-raw)))
    if error>1e-4: raise AssertionError(f'SHAP additivity error: {error}')
    pd.DataFrame({'feature':names,'mean_absolute_shap':np.abs(values).mean(axis=0)}).sort_values('mean_absolute_shap',ascending=False).to_csv(output_dir/'feature_importance.csv',index=False)
    if hasattr(model,'feature_importances_'):
        pd.DataFrame({'feature':names,'importance':model.feature_importances_}).sort_values('importance',ascending=False).to_csv(output_dir/'native_feature_importance.csv',index=False)
    # Complete per-application trace is saved locally and excluded from Git.
    traces=pd.DataFrame(values,columns=names)
    traces.insert(0,key,d[key].values)
    traces.to_csv(output_dir/'shap_contributions.csv',index=False)
    rows=[]
    probabilities=calibrated.predict_proba(d[features])[:,1]
    for i,app in enumerate(d[key]):
        top=np.argsort(np.abs(values[i]))[-5:][::-1]
        rows.append({key:app,'base_value':expected,'uncalibrated_model_output':float(raw[i]),
                     'calibrated_probability':float(probabilities[i]),'output_scale':output,
                     'top_drivers':[{'feature':str(names[j]),'contribution':float(values[i,j])} for j in top]})
    (output_dir/'prediction_explanations.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    info={'output_scale':output,'base_value':expected,'max_additivity_error':error,
          'note':'SHAP exactly decomposes the selected base estimator. Final probability applies training-only sigmoid calibration; SHAP values are not additive in calibrated probability space.'}
    calibration = calibrated.calibrated_classifiers_[0].calibrators[0]
    input_scale='raw_log_odds' if hasattr(base,'decision_function') else 'uncalibrated_probability'
    info['base_model_type']=model.__class__.__name__
    info['sigmoid_calibration'] = {'a':float(calibration.a_),'b':float(calibration.b_),
        'input_scale':input_scale,
        'shap_output_conversion':('expit' if output=='raw_log_odds' and input_scale=='uncalibrated_probability' else 'identity'),
        'formula':'p = 1 / (1 + exp(a * calibration_input + b)); XGBoost raw SHAP margins first pass through expit'}
    (output_dir/'explainability.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
    return info
