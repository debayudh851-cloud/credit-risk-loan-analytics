"""Contract-aware four-model comparison with training-only selection."""
import json
import time
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import (train_test_split, StratifiedKFold, GridSearchCV,
                                    cross_val_predict, GroupShuffleSplit)
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
                            roc_auc_score, confusion_matrix, brier_score_loss, average_precision_score)
from xgboost import XGBClassifier
from .features import FEATURES, CATEGORICAL
from .config import ROOT, OUT, SEED

def preprocessing(scaled=False, features=None):
    features = FEATURES if features is None else list(features)
    categorical = [c for c in features if c in CATEGORICAL or c == 'loan_purpose']
    numeric = [c for c in features if c not in categorical]
    numeric_steps = [('impute',SimpleImputer(strategy='median',keep_empty_features=True))]
    if scaled:
        numeric_steps.append(('scale',StandardScaler()))
    return ColumnTransformer([
        ('numeric',Pipeline(numeric_steps),numeric),
        ('category',Pipeline([
            ('impute',SimpleImputer(strategy='constant',fill_value='Unknown')),
            ('encode',OneHotEncoder(handle_unknown='ignore',sparse_output=False))]),categorical)
    ],sparse_threshold=0,verbose_feature_names_out=False)

def metrics(y,p,threshold):
    pred = np.asarray(p) >= threshold
    return {
        'accuracy':float(accuracy_score(y,pred)),
        'precision':float(precision_score(y,pred,zero_division=0)),
        'recall':float(recall_score(y,pred,zero_division=0)),
        'f1':float(f1_score(y,pred,zero_division=0)),
        'roc_auc':float(roc_auc_score(y,p)),
        'average_precision':float(average_precision_score(y,p)),
        'brier_score':float(brier_score_loss(y,p)),
        'confusion_matrix':confusion_matrix(y,pred).tolist()
    }

def choose_threshold(y,p):
    rows = []
    for threshold in np.linspace(0,1,101):
        pred = p >= threshold
        rows.append({'threshold':float(threshold),
                     'precision':float(precision_score(y,pred,zero_division=0)),
                     'recall':float(recall_score(y,pred,zero_division=0)),
                     'f1':float(f1_score(y,pred,zero_division=0)),
                     'accuracy':float(accuracy_score(y,pred))})
    curve = pd.DataFrame(rows)
    eligible = curve.loc[curve.recall >= .8]
    selected = eligible.sort_values(['precision','threshold'],ascending=False).iloc[0]
    return float(selected.threshold),curve

def candidates(y):
    imbalance = float((y == 0).sum() / (y == 1).sum())
    return {
        'Logistic Regression': (
            LogisticRegression(max_iter=2000,random_state=SEED),
            {'model__C':[.05,.5,5.0],'model__class_weight':[None,'balanced']},True),
        'Decision Tree': (
            DecisionTreeClassifier(random_state=SEED,min_samples_leaf=25),
            {'model__max_depth':[2,4,6],'model__class_weight':[None,'balanced']},False),
        'Random Forest': (
            RandomForestClassifier(n_estimators=160,min_samples_leaf=10,n_jobs=1,random_state=SEED),
            {'model__max_depth':[4,8,None],'model__class_weight':[None,'balanced']},False),
        'XGBoost': (
            XGBClassifier(n_estimators=160,learning_rate=.04,min_child_weight=8,
                          reg_lambda=5,n_jobs=1,random_state=SEED,eval_metric='logloss',
                          subsample=.9,colsample_bytree=.9),
            {'model__max_depth':[1,2,4],'model__scale_pos_weight':[1,imbalance]},False)
    }

def compare(X,y,features,output_dir):
    cv = StratifiedKFold(5,shuffle=True,random_state=SEED)
    trained,comparison = {},[]
    for name,(estimator,grid,scaled) in candidates(y).items():
        print(f'Tuning {name}: {len(features)} features, training-only 5-fold CV',flush=True)
        pipeline = Pipeline([('preprocess',preprocessing(scaled,features)),('model',estimator)])
        search = GridSearchCV(pipeline,grid,cv=cv,scoring={'auc':'roc_auc','recall':'recall'},
                              refit='auc',n_jobs=2)
        search.fit(X,y)
        best = search.best_estimator_
        trained[name] = best
        idx = search.best_index_
        comparison.append({'model':name,'cv_roc_auc':float(search.best_score_),
                           'cv_auc_std':float(search.cv_results_['std_test_auc'][idx]),
                           'cv_recall_at_0_5':float(search.cv_results_['mean_test_recall'][idx]),
                           'parameters':search.best_params_})
        fitted = best.named_steps['model']
        if hasattr(fitted,'feature_importances_'):
            pd.DataFrame({'feature':best.named_steps['preprocess'].get_feature_names_out(),
                          'importance':fitted.feature_importances_}).sort_values('importance',ascending=False).to_csv(
                output_dir / (name.lower().replace(' ','_')+'_feature_importance.csv'),index=False)
    comparison.sort(key=lambda row:(row['cv_roc_auc'],row['cv_recall_at_0_5']),reverse=True)
    return trained,comparison

def train(d,features=None,context='retrospective',output_dir=None,
          artifact_name='default_model.pkl',frozen_split=None,key='application_id'):
    started = time.perf_counter()
    features = FEATURES if features is None else list(features)
    output_dir = OUT if output_dir is None else Path(output_dir)
    output_dir.mkdir(parents=True,exist_ok=True)
    observed = d.loc[d.loan_default.notna()].copy().reset_index(drop=True)
    X = observed[features]
    y = observed.loan_default.astype(int)
    if frozen_split is not None:
        assignments = observed[[key]].merge(frozen_split,on=key,how='left',validate='one_to_one')
        if assignments.split.isna().any():
            raise ValueError('Frozen split lacks labelled records')
        tr = np.flatnonzero(assignments.split.eq('train'))
        te = np.flatnonzero(assignments.split.eq('test'))
    else:
        tr,te = train_test_split(np.arange(len(X)),test_size=.2,stratify=y,random_state=SEED)
    Xtr,Xte,ytr,yte = X.iloc[tr],X.iloc[te],y.iloc[tr],y.iloc[te]
    trained,comparison = compare(Xtr,ytr,features,output_dir)
    name = comparison[0]['model']
    base = trained[name]
    cv = StratifiedKFold(5,shuffle=True,random_state=SEED)
    calibrated = CalibratedClassifierCV(base,method='sigmoid',cv=3,ensemble=False,n_jobs=2)
    oof = cross_val_predict(calibrated,Xtr,ytr,cv=cv,method='predict_proba',n_jobs=2)[:,1]
    threshold,curve = choose_threshold(ytr,oof)
    calibrated.fit(Xtr,ytr)
    # Holdout results do not influence the feature contract, model or threshold.
    for row in comparison:
        row['test_at_0_5'] = metrics(yte,trained[row['model']].predict_proba(Xte)[:,1],.5)
    ptest = calibrated.predict_proba(Xte)[:,1]
    result = {'champion':name,'threshold':threshold,'test_metrics':metrics(yte,ptest,threshold),
              'train_oof_metrics':metrics(ytr,oof,threshold),'comparison':comparison,
              'n_train':len(tr),'n_test':len(te),'seed':SEED,'context':context,
              'feature_contract':features,
              'test_customer_overlap':len(set(observed.iloc[tr].customer_id)&set(observed.iloc[te].customer_id)),
              'holdout_note':('Fixed v1 holdout, previously reported; v2 is a continuation, not a fresh external validation.'
                              if frozen_split is not None else 'Stratified held-out entity rows; selection and threshold use training only.')}
    if key == 'application_id':
        gt,ge = next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=SEED).split(X,y,observed.customer_id))
        group_model = clone(calibrated).fit(X.iloc[gt],y.iloc[gt])
        result['group_holdout_audit'] = metrics(y.iloc[ge],group_model.predict_proba(X.iloc[ge])[:,1],threshold)
    else:
        result['group_holdout_audit'] = result['test_metrics']
    result['training_seconds'] = time.perf_counter()-started
    result['success_targets'] = {
        'roc_auc_at_least_0_80':result['test_metrics']['roc_auc'] >= .8,
        'recall_at_least_0_70':result['test_metrics']['recall'] >= .7,
        'training_under_300_seconds':result['training_seconds'] < 300}
    pd.DataFrame({key:observed.iloc[te][key].values,'actual_default':yte.values,
                  'default_probability':ptest,'predicted_default':(ptest>=threshold).astype(int)}).to_csv(
        output_dir/'test_predictions.csv',index=False)
    pd.DataFrame({key:observed[key],'split':np.where(np.isin(np.arange(len(X)),te),'test','train')}).to_csv(
        output_dir/'split_manifest.csv',index=False)
    curve.to_csv(output_dir/'threshold_curve.csv',index=False)
    (output_dir/'metrics.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    joblib.dump({'model':calibrated,'base_model':base,'features':features,'threshold':threshold,
                 'context':context,'seed':SEED},ROOT/'models'/artifact_name)
    return calibrated,base,result
