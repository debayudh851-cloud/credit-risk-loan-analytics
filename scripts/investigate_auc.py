"""Investigate the AUC gap on the frozen development partition only."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from src.config import ROOT,OUT
from src.data_load import read_raw
from src.features import retrospective_enhanced_features
from src.modeling import compare

frames = read_raw()
manifest = pd.read_csv(OUT/'split_manifest.csv')
ids = set(manifest.loc[manifest.split.eq('train'),'application_id'])
# Remove all holdout outcomes and records before feature construction.
frames['loan_applications'] = frames['loan_applications'].loc[
    frames['loan_applications'].application_id.isin(ids)].copy()
d,features = retrospective_enhanced_features(frames)
dest = OUT/'auc_investigation';dest.mkdir(exist_ok=True)
_,comparison = compare(d[features],d.loan_default.astype(int),features,dest)
result = {'population':'Frozen v1 development set only','development_rows':len(d),
          'features':features,'comparison':comparison,'test_set_used':False,
          'note':'CV scores are development estimates after tuning, not held-out acceptance results. Retrospective features cannot establish pre-disbursal validity.'}
(dest/'development_cv.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({'development_best_cv_auc':comparison[0]['cv_roc_auc'],
                  'champion':comparison[0]['model'],'comparison':comparison},indent=2))
