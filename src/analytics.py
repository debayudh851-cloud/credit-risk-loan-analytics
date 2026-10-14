import json
import time
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import RocCurveDisplay, PrecisionRecallDisplay
from .config import ROOT, OUT
from .data_load import connect

def run_queries(url=None):
    statements=(ROOT/'sql/analysis.sql').read_text(encoding='utf-8').split(';')
    timing=[]; conn=connect(url)
    try:
        for i,sql in enumerate([x for x in statements if x.strip()],1):
            start=time.perf_counter()
            cur=conn.cursor();cur.execute(sql)
            rows=cur.fetchall();columns=[col[0] for col in cur.description]
            df=pd.DataFrame(rows,columns=columns)
            elapsed=time.perf_counter()-start
            df.to_csv(OUT/'sql'/f'q{i:02d}.csv',index=False)
            timing.append({'query':i,'rows':len(df),'seconds':elapsed,'under_2_seconds':elapsed<2})
    finally: conn.close()
    (OUT/'sql_timings.json').write_text(json.dumps(timing,indent=2),encoding='utf-8')
    return timing

def portfolio(frames):
    l=frames['loan_applications']; c=frames['customers']; h=frames['credit_history']
    decided=l.approval_status.ne('Under Review')
    observed=l.loc[l.disbursed_flag.eq(1) & l.loan_default.notna()]
    return {'customers':len(c),'applications':len(l),'disbursed':len(observed),
            'pending':int((~decided).sum()),'approval_rate':float(l.approval_status.eq('Approved').sum()/decided.sum()),
            'default_rate':float(observed.loan_default.mean()),
            'disbursed_value_inr':float(observed.approved_amount.sum()),
            'credit_snapshot_count':int(h.as_of_date.nunique()),'data_as_of':'2024-06-30'}

def charts(frames):
    sns.set_theme(style='whitegrid',palette='deep')
    l=frames['loan_applications'];h=frames['credit_history'];c=frames['customers']
    observed=l.loc[l.loan_default.notna()]
    plots=[('credit_score',h.credit_score,'Bureau credit score distribution'),
           ('requested_amount',l.requested_amount,'Requested loan amount INR'),
           ('debt_to_income',l.debt_to_income_ratio,'Debt to income ratio')]
    for file,series,title in plots:
        fig,ax=plt.subplots(figsize=(8,4));sns.histplot(series,bins=35,ax=ax)
        ax.set_title(title);fig.tight_layout();fig.savefig(OUT/'figures'/f'{file}.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4))
    observed.groupby('loan_type').loan_default.mean().sort_values().mul(100).plot.barh(ax=ax,color='#2563eb')
    ax.set_title('Observed default rate by loan type');ax.set_xlabel('Default rate %')
    fig.tight_layout();fig.savefig(OUT/'figures/default_by_loan.png',dpi=160);plt.close(fig)
    joined=observed.merge(h,on='customer_id',validate='many_to_one')
    fig,ax=plt.subplots(figsize=(8,5));sns.heatmap(joined[['loan_default','credit_score','debt_to_income_ratio','credit_utilization_ratio','num_defaults_prior','requested_amount']].corr(),annot=True,fmt='.2f',cmap='vlag',center=0,ax=ax)
    ax.set_title('Retrospective numeric associations');fig.tight_layout();fig.savefig(OUT/'figures/correlations.png',dpi=160);plt.close(fig)
    monthly=l.assign(month=l.application_date.str[:7]).groupby('month').approval_status.value_counts().unstack(fill_value=0)
    fig,ax=plt.subplots(figsize=(10,4));monthly.plot.bar(stacked=True,ax=ax)
    ax.set_title('Application decisions by application month');fig.tight_layout();fig.savefig(OUT/'figures/monthly_decisions.png',dpi=160);plt.close(fig)
    test=pd.read_csv(OUT/'test_predictions.csv');m=json.loads((OUT/'metrics.json').read_text())
    fig,axes=plt.subplots(1,3,figsize=(15,4))
    RocCurveDisplay.from_predictions(test.actual_default,test.default_probability,ax=axes[0])
    PrecisionRecallDisplay.from_predictions(test.actual_default,test.default_probability,ax=axes[1])
    sns.heatmap(m['test_metrics']['confusion_matrix'],annot=True,fmt='d',cmap='Blues',ax=axes[2],xticklabels=['No default','Default'],yticklabels=['No default','Default'])
    axes[2].set(xlabel='Predicted',ylabel='Actual',title=f"Threshold {m['threshold']:.2f}")
    fig.tight_layout();fig.savefig(OUT/'figures/model_evaluation.png',dpi=160);plt.close(fig)
    importance=pd.read_csv(OUT/'feature_importance.csv').head(15).iloc[::-1]
    fig,ax=plt.subplots(figsize=(9,6));ax.barh(importance.feature,importance.mean_absolute_shap,color='#0d9488')
    ax.set_title('Top 15 default drivers by mean absolute SHAP');fig.tight_layout();fig.savefig(OUT/'figures/feature_importance.png',dpi=160);plt.close(fig)
    summary=portfolio(frames)
    (OUT/'portfolio_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    return summary
