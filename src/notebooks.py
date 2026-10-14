"""Author ordered notebooks for the two distinct scoring contracts."""
import nbformat as nbf
from .config import ROOT

SETUP = '''from pathlib import Path
import sys, json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from IPython.display import display, Image
ROOT = Path.cwd() if (Path.cwd() / 'src').exists() else Path.cwd().parent
sys.path.insert(0,str(ROOT))
OUT = ROOT / 'artifacts'
assert json.loads((OUT / 'run_manifest.json').read_text())['version'] == 2, 'Run python -m src.pipeline first'
'''

def save(name,cells):
    notebook = nbf.v4.new_notebook(cells=[
        nbf.v4.new_markdown_cell(text) if kind=='md' else nbf.v4.new_code_cell(text)
        for kind,text in cells])
    notebook.metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},
                       'language_info':{'name':'python','version':'3.13'}}
    nbf.write(notebook,ROOT/'notebooks'/name)

def main():
    (ROOT/'notebooks').mkdir(exist_ok=True)
    save('01_eda.ipynb',[
        ('md','# Credora portfolio exploration\n\nExplore source integrity, observed outcomes and lending segments. Personal contacts and names are never displayed. All default rates use observed disbursed outcomes; non-disbursed NULLs are not negative labels.'),
        ('code',SETUP+"\nfrom src.data_load import read_raw\nframes = read_raw()\ndisplay(pd.DataFrame({name:{'rows':len(d),'columns':len(d.columns),'missing_cells':int(d.isna().sum().sum())} for name,d in frames.items()}).T)"),
        ('md','## Observed outcome population\nApproval denominator excludes pending decisions. Default denominator includes only disbursed records with observed outcomes. Timing issues and duplicate optional contacts are recorded in the quality report.'),
        ('code',"loans=frames['loan_applications']\ndisplay(loans.groupby(['approval_status','disbursed_flag']).agg(applications=('application_id','size'),observed_outcomes=('loan_default','count'),observed_default_rate=('loan_default','mean')))\nprint(json.loads((OUT/'data_quality.json').read_text())['timing'])\nprint(json.loads((OUT/'portfolio_summary.json').read_text()))"),
        ('md','## Exploratory distributions\nBureau associations use the single June 30 snapshot and are retrospective. They are not historical inputs to the strict applicant model.'),
        ('code',"for file in ['credit_score.png','requested_amount.png','debt_to_income.png','default_by_loan.png','correlations.png','monthly_decisions.png']:\n    display(Image(filename=str(OUT/'figures'/file)))"),
        ('md','## SQL segment evidence\nInspect group counts alongside rates. A higher observed segment rate does not imply a causal effect of loan type or establish how rejected applicants would repay.'),
        ('code',"for i in [1,2,3,5,7,10]:\n    print(f'Query {i:02d}')\n    display(pd.read_csv(OUT/'sql'/f'q{i:02d}.csv').head(12))"),
        ('md','## Data limitations\nBureau history cannot be backdated. Customer profiles lack effective dates, 124 applications imply an age below 18 from the supplied birth dates, and repayment outcomes lack event dates and maturity horizons. These are source limitations, not facts imputation can recover.')])
    save('02_feature_engineering.ipynb',[
        ('md','# Request-time and customer-profile feature contracts\n\nThe two models have different populations and different meanings. Applicant scoring must never substitute a current profile for historical request inputs. Customer scoring uses the supplied actual profile and never constructs a fictitious loan.'),
        ('code',SETUP+"\nfrom src.data_load import read_raw\nfrom src.features import strict_application_features, customer_profile_features, STRICT_FEATURES, PROFILE_FEATURES\nframes=read_raw()\nrequests=strict_application_features(frames)\nprofiles=customer_profile_features(frames)\nprint('Requests:',requests.shape,'Customer profiles:',profiles.shape)\nassert requests.application_id.is_unique and profiles.customer_id.is_unique"),
        ('md','## Strict request-time construction\nUse request amount, term, type, purpose, collateral, declared monthly income and existing EMI. Build existing-payment burden, request-to-income and principal-only instalment burden without inventing an interest rate. Earlier transaction windows are six calendar months and exclude the application day. Undated demographics, bureau values, offered rates and supplied underwriting DTI are excluded entirely.'),
        ('code',"blocked={'credit_score','annual_income','employment_type','interest_rate','debt_to_income_ratio','approval_status','approved_amount','decision_date','disbursed_flag','loan_default'}\nassert not blocked.intersection(STRICT_FEATURES)\ndisplay(requests[STRICT_FEATURES].isna().mean().sort_values(ascending=False).to_frame('missing_fraction'))\nprint('History available:',requests.history_available.value_counts().to_dict())"),
        ('md','## Verify future transaction isolation\nAppending a large future transaction must not alter historical feature vectors. This is an implementation property independent of reported test metrics.'),
        ('code',"sample=frames['loan_applications'].head(30)\nsource={'loan_applications':sample,'transactions':frames['transactions']}\nbefore=strict_application_features(source)\nfuture=frames['transactions'].head(20).copy();future['transaction_date']='2030-01-01';future['amount']=1e12\nsource['transactions']=pd.concat([frames['transactions'],future],ignore_index=True)\nafter=strict_application_features(source)\npd.testing.assert_frame_equal(before,after)\nprint('Future transaction isolation passed.')"),
        ('md','## Actual customer profiles\nEvery customer uses their own bureau, customer and account attributes. No loan amount, tenure or product is invented. The model is retrospective: its training target is the latest observed disbursed loan label per customer, and the bureau snapshot may be after that outcome.'),
        ('code',"assert not {'requested_amount','loan_type','loan_term_months','loan_to_income'}.intersection(PROFILE_FEATURES)\ndisplay(profiles.drop(columns='customer_id').describe().T)\nprint('Customer-only features:',PROFILE_FEATURES)"),
        ('md','## Fold-local preprocessing\nNumeric medians and Unknown/one-hot categorical encoding are learned inside each training fold. Only logistic regression standardises numeric features. Missing history is distinct from zero observed cashflow. The persisted artefact fixes the exact model input contract.'),
        ('code',"import joblib\nartifact=joblib.load(ROOT/'models/default_model.pkl')\nassert artifact['features']==STRICT_FEATURES\nprint('Applicant contract:',artifact['features'])\nprint((ROOT/'documentation/feature_contracts.md').read_text())")])
    save('03_modeling.ipynb',[
        ('md','# Four-model comparisons and honest acceptance\n\nCompare four algorithms independently for applicant risk and customer-profile association. Selection, calibration and thresholding use training-only folds. Preserve the original application holdout instead of trying favourable seeds.'),
        ('code',SETUP+"\nmain=json.loads((OUT/'metrics.json').read_text())\ncustomer=json.loads((OUT/'customer_model/metrics.json').read_text())\nfor name,result in [('Applicant',main),('Customer profile',customer)]:\n    print(name,result['champion'])\n    display(pd.DataFrame([{k:v for k,v in row.items() if k not in ['parameters','test_at_0_5']} for row in result['comparison']]))"),
        ('md','## Validation protocol\nThe applicant model uses the frozen 80/20 application partition, previously reported in v1, so the continuation test is not fresh external validation. Five-fold training CV selects hyperparameters and algorithm. Training-only sigmoid calibration uses three-fold folds; five-fold calibrated OOF probabilities select a threshold with at least 80% recall. The customer model has one latest observed label per borrower and a customer-disjoint stratified holdout.'),
        ('code',"for name,result in [('Applicant',main),('Customer',customer)]:\n    print(name,'threshold',result['threshold'],'shared test customers',result['test_customer_overlap'])\n    display(pd.DataFrame([{k:v for k,v in result['test_metrics'].items() if k!='confusion_matrix'}]))\n    print('Confusion matrix:',result['test_metrics']['confusion_matrix'])\n    print('Acceptance:',result['success_targets'])\ndisplay(Image(filename=str(OUT/'figures/model_evaluation.png')))"),
        ('code',"curve=pd.read_csv(OUT/'threshold_curve.csv')\ncurve.plot(x='threshold',y=['precision','recall','f1'],figsize=(9,4));plt.axvline(main['threshold'],color='black',linestyle='--');plt.title('Training-only review threshold');plt.show()"),
        ('md','## Calendar and borrower sensitivity\nThe borrower-disjoint audit reveals repeated-customer optimism. The fixed calendar audit trains before January 2024 and tests 2024 requests. Because outcome-event dates and observation ends are absent, this calendar split cannot prove that training labels had matured at the cutoff.'),
        ('code',"print('Borrower-disjoint audit:',main['group_holdout_audit'])\nprint('Calendar audit:',json.loads((OUT/'temporal_audit.json').read_text()))"),
        ('md','## AUC investigation\nThe separate wider retrospective search uses only the frozen development records. Log transforms, credit thresholds and wider regularisation are investigated without the holdout. Its CV estimate is not substituted for a failed held-out target and its snapshots remain unsuitable for historical request-time prediction.'),
        ('code',"path=OUT/'auc_investigation/development_cv.json'\nif path.exists():\n    study=json.loads(path.read_text());print('Test set used:',study['test_set_used']);display(pd.DataFrame(study['comparison']))\nprint(json.loads((OUT/'acceptance_status.json').read_text()))"),
        ('md','## Explanation scales\nEvery applicant and customer has complete signed SHAP traces. Contributions reconstruct the selected base estimator. Logistic regression uses log odds; tree probability output and XGBoost log margins are distinct. The saved conversion and calibration mapping produce final probability. XGBoost margins require an expit transformation before its probability-based calibrator.'),
        ('code',"for path in [OUT,OUT/'customer_model']:\n    display(pd.read_csv(path/'feature_importance.csv').head(15))\n    print(json.loads((path/'explainability.json').read_text()))\ndisplay(Image(filename=str(OUT/'figures/feature_importance.png')))")])
    save('04_risk_scoring.ipynb',[
        ('md','# Risk scoring without hypothetical loans\n\nAll 7,500 applications use the request-time classifier and all 5,000 customers use their actual profile classifier. The customer estimate describes latest-observed-loan label association, not the risk of a particular future loan.'),
        ('code',SETUP+"\nfrom src.risk_score import score\ndisplay(score([0,.33,.34,.66,.67,1]))\napps=pd.read_csv(OUT/'scored_applications.csv')\ncustomers=pd.read_csv(OUT/'scored_customers.csv')\nassert len(apps)==7500 and len(customers)==5000\nassert customers.score_basis.eq('customer_profile_model').all()\nassert customers.source_application_id.isna().all()\nprint('Hypothetical applications:',0)"),
        ('md','## Exact bands and separate review thresholds\nRound calibrated probability ×100 to an integer. Low is 0–33, Medium 34–66 and High 67–100. The classifier review threshold is selected on training folds and is separate from these fixed risk bands. Never label customers without outcomes as non-defaults.'),
        ('code',"display(customers.groupby(['risk_category','score_basis']).size().rename('customers').reset_index())\ncustomers.risk_category.value_counts().plot.pie(autopct='%1.1f%%',figsize=(6,6));plt.ylabel('');plt.title('Actual-profile customer risk distribution');plt.show()"),
        ('md','## Reload both model artefacts\nThe feature contracts and context guard prevent a retrospective model from being silently used for new request scoring. Saved models remain fitted on training partitions, so reported holdout metrics remain distinct from in-sample dashboard scores.'),
        ('code',"import joblib\nfrom src.score_requests import score_requests\nfrom src.data_load import read_raw\nframes=read_raw();artifact=joblib.load(ROOT/'models/default_model.pkl')\nrequests=score_requests(frames['loan_applications'].head(30),frames['transactions'],artifact)\nexpected=apps.loc[apps.application_id.isin(requests.application_id)]\nassert np.allclose(requests.default_probability,expected.default_probability)\nprint('Batch request scoring reproduces persisted probabilities.')"),
        ('md','## Geographic watchlist and complete traces\nThe dashboard filters customer risk categories and regions, shows actual-profile drivers, and provides a separate applicant selector. Data for borrowers without outcomes remain extrapolations, but no application is fabricated.'),
        ('code',"watch=pd.read_csv(OUT/'dashboard_customers.csv')\ndisplay(watch.groupby(['state','risk_category']).size().unstack(fill_value=0))\nprint('Applicant explanation rows:',len(json.loads((OUT/'prediction_explanations.json').read_text())))\nprint('Customer explanation rows:',len(json.loads((OUT/'customer_model/prediction_explanations.json').read_text())))"),
        ('md','## Handover and remaining acceptance\nRun streamlit run dashboard/app.py. Review all eight required components, both score populations and objective acceptance states. Historical bureau/profile snapshots and dated maturity outcomes are still required for true prospective validation; AUC is reported as measured rather than forced to meet the target.'),
        ('code',"print((ROOT/'documentation/results.md').read_text())\nprint(json.loads((OUT/'run_manifest.json').read_text()))")])
    print('Created four v2 notebooks.')
