"""Launch: streamlit run dashboard/app.py"""
import json
import textwrap
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts'
st.set_page_config(page_title='Credora Risk Desk',page_icon='📊',layout='wide')
st.markdown('''<style>
.stApp {background:#f6f8fc}
[data-testid="stMetric"] {background:white;padding:18px;border-radius:12px;border:1px solid #e4e9f2}
h1 {color:#102647}
@media (max-width: 1100px) {
 [data-testid="stHorizontalBlock"] {flex-wrap:wrap}
 [data-testid="stColumn"] {flex:1 1 260px!important;min-width:240px!important}
 [data-testid="stMetricValue"] {font-size:1.8rem}
}
</style>''',unsafe_allow_html=True)
st.title('Credora Risk Desk')
st.caption('Retail lending portfolio • Data through June 2024 • Decision support')
st.warning('Applicant scores use submitted request fields and strictly earlier transactions. Customer risk is a separate profile model using the supplied bureau snapshot. Outcome horizons and event dates are absent, so prospective validation remains incomplete.')
if not (OUT/'dashboard_applications.csv').exists():
    st.info('Run python -m src.pipeline to build dashboard data.');st.stop()

@st.cache_data
def get_data(signature):
    return (pd.read_csv(OUT/'dashboard_applications.csv'),pd.read_csv(OUT/'dashboard_customers.csv'),
            pd.read_csv(OUT/'dashboard_credit.csv'),json.loads((OUT/'metrics.json').read_text()),
            json.loads((OUT/'prediction_explanations.json').read_text()))

apps,customers,credit,metrics,explanations=get_data((OUT/'run_manifest.json').stat().st_mtime_ns)
apps['month']=apps.application_date.str[:7]
colors={'Low Risk':'#16a085','Medium Risk':'#e9a23b','High Risk':'#d64f67'}
st.sidebar.header('Portfolio filters')
states=st.sidebar.multiselect('Region / state',sorted(customers.state.unique()))
loan_types=st.sidebar.multiselect('Loan type',sorted(apps.loan_type.unique()))
months=st.sidebar.multiselect('Application month',sorted(apps.month.unique()))
risk=st.sidebar.multiselect('Customer risk category',['Low Risk','Medium Risk','High Risk'])
a=apps.copy()
if states:a=a.loc[a.state.isin(states)]
if loan_types:a=a.loc[a.loan_type.isin(loan_types)]
if months:a=a.loc[a.month.isin(months)]
c=customers.copy()
if states:c=c.loc[c.state.isin(states)]
if risk:c=c.loc[c.risk_category.isin(risk)]
if risk:a=a.loc[a.customer_id.isin(c.customer_id)]
if loan_types or months:c=c.loc[c.customer_id.isin(a.customer_id)]
if a.empty:
    st.info('No applications match these filters. Customer profiles may still appear in the watchlist.')
decided=a.approval_status.ne('Under Review');obs=a.loc[a.disbursed_flag.eq(1)&a.loan_default.notna()]
approved=a.approval_status.eq('Approved').sum()
cols=st.columns(5)
cols[0].metric('Applications',f'{len(a):,}')
cols[1].metric('Approval rate',f'{approved/decided.sum():.1%}' if decided.sum() else 'No decisions')
cols[2].metric('Observed default rate',f'{obs.loan_default.mean():.1%}' if len(obs) else 'No observed outcomes')
cols[3].metric('Disbursed value',f'INR {obs.approved_amount.sum()/1e7:,.1f} crore')
cols[4].metric('High-risk customers',f'{c.risk_category.eq("High Risk").sum():,}')
st.caption('Approval denominator: approved + rejected. Default denominator: disbursed loans with observed outcomes. Customer mix uses a separate actual-profile model; customer-risk filters select the corresponding borrower cohort.')
tab1,tab2,tab3=st.tabs(['Portfolio overview','Underwriter and watchlist','Model evidence'])

def chart(fig):
    title = '<br>'.join(textwrap.wrap(fig.layout.title.text or '',width=32))
    labels = {'month':'Application month','approval_rate_pct':'Approval rate (%)',
              'default_rate_pct':'Default rate (%)','loan_type':'Loan type',
              'credit_score':'Credit score','count':'Customers','applications':'Applications',
              'state':'State','approval_status':'Decision','contribution':'SHAP contribution',
              'feature':'Feature','mean_absolute_shap':'Mean absolute SHAP'}
    legend = any(trace.showlegend for trace in fig.data)
    fig.update_layout(template='plotly_white',margin=dict(l=15,r=15,t=75,b=80 if legend else 40),
                      height=390 if legend else 350,
                      title=dict(text=title,font=dict(size=14),x=.02,xanchor='left',y=.97))
    if legend:fig.update_layout(legend=dict(orientation='h',y=-.3,x=0,title_text=''))
    for axis_name in ['xaxis','yaxis']:
        axis = getattr(fig.layout,axis_name)
        if axis.title.text in labels: axis.title.text=labels[axis.title.text]
    st.plotly_chart(fig,width='stretch')

with tab1:
    left,right=st.columns(2)
    monthly=a.groupby('month').agg(applications=('application_id','size'),approved=('approval_status',lambda x:x.eq('Approved').sum()),decided=('approval_status',lambda x:x.ne('Under Review').sum())).reset_index()
    monthly['approval_rate_pct']=100*monthly.approved/monthly.decided.replace(0,float('nan'))
    with left:chart(px.line(monthly,x='month',y='approval_rate_pct',markers=True,title='Loan approval rate by application month'))
    with right:
        defaults=obs.groupby('loan_type').loan_default.agg(['mean','count']).reset_index();defaults['default_rate_pct']=defaults['mean']*100
        chart(px.bar(defaults,x='loan_type',y='default_rate_pct',hover_data=['count'],title='Observed default rate by loan type'))
    left,right=st.columns(2)
    with left:
        mix=c.risk_category.value_counts().rename_axis('risk_category').reset_index(name='customers')
        chart(px.pie(mix,names='risk_category',values='customers',hole=.65,color='risk_category',color_discrete_map=colors,title='Customer risk distribution'))
    with right:
        h=credit.loc[credit.customer_id.isin(c.customer_id)]
        chart(px.histogram(h,x='credit_score',nbins=35,title='Credit score distribution • June 30 snapshot'))
        st.caption('One bureau snapshot per customer; a longitudinal credit-score trend cannot be inferred.')
    left,right=st.columns(2)
    with left:
        geo=a.groupby('state').agg(applications=('application_id','size'),approved=('approval_status',lambda x:x.eq('Approved').sum()),decided=('approval_status',lambda x:x.ne('Under Review').sum()),disbursed_value=('approved_amount','sum')).reset_index()
        geo['approval_rate_pct']=geo.approved/geo.decided.replace(0,float('nan'))*100
        chart(px.bar(geo.sort_values('applications'),x='applications',y='state',orientation='h',hover_data=['approval_rate_pct','disbursed_value'],title='Geographic loan distribution'))
    with right:chart(px.bar(monthly,x='month',y='applications',title='Monthly loan applications'))
    left,right=st.columns(2)
    with left:
        decisions=a.groupby(['month','approval_status']).size().reset_index(name='applications')
        chart(px.bar(decisions,x='month',y='applications',color='approval_status',barmode='stack',title='Approval vs rejection trends'))
    with right:
        trend=obs.groupby(['month','loan_type']).loan_default.mean().mul(100).reset_index(name='default_rate_pct')
        chart(px.line(trend,x='month',y='default_rate_pct',color='loan_type',title='Observed defaults by application cohort'))
        st.caption('Cohorts refer to application month. Default-event dates and repayment horizons are unavailable.')
with tab2:
    st.subheader('Customer watchlist')
    only_high=st.checkbox('Show high risk only',value=True)
    watch=c.loc[c.risk_category.eq('High Risk')] if only_high else c
    cols=['customer_id','state','city','credit_score','default_probability','risk_score','risk_category','score_basis']
    watch=watch.sort_values(['default_probability','customer_id'],ascending=[False,True])
    st.dataframe(watch[cols],hide_index=True,width='stretch')
    st.download_button('Download filtered watchlist',watch[cols].to_csv(index=False),'credora_watchlist.csv','text/csv')
    if len(c) and (OUT/'customer_model/prediction_explanations.json').exists():
        st.subheader('Customer profile evidence')
        customer_id=st.selectbox('Customer profile',sorted(c.customer_id.unique()))
        selected_customer=c.loc[c.customer_id.eq(customer_id)].iloc[0]
        profile_cols=st.columns(3)
        profile_cols[0].metric('Profile default association',f'{selected_customer.default_probability:.1%}')
        profile_cols[1].metric('Customer risk score',f'{int(selected_customer.risk_score)} / 100')
        profile_cols[2].metric('Customer risk category',selected_customer.risk_category)
        customer_traces=json.loads((OUT/'customer_model/prediction_explanations.json').read_text())
        customer_trace=next(e for e in customer_traces if e['customer_id']==customer_id)
        chart(px.bar(pd.DataFrame(customer_trace['top_drivers']),x='contribution',y='feature',
                     orientation='h',title='Signed actual-profile risk contributions'))
        st.caption('Uses the customer’s actual profile and account history, without assumed loan terms. It estimates retrospective latest-observed-loan default association; unobserved borrowers remain an extrapolation population.')
    if len(a):
        st.subheader('Applicant evidence')
        app_id=st.selectbox('Application',a.application_id.sort_values())
        selected=a.loc[a.application_id.eq(app_id)].iloc[0]
        x,y,z=st.columns(3)
        x.metric('Default probability',f'{selected.default_probability:.1%}')
        y.metric('Risk score',f'{int(selected.risk_score)} / 100')
        z.metric('Risk category',selected.risk_category)
        st.caption(f"Flag threshold {metrics['threshold']:.2f}. Scores advise review; final decisions stay with the underwriter.")
        e=next(e for e in explanations if e['application_id']==app_id)
        drivers=pd.DataFrame(e['top_drivers'])
        chart(px.bar(drivers,x='contribution',y='feature',orientation='h',title='Top signed SHAP contributions for selected applicant'))
        st.caption(f"Contributions add to the base estimator in {e['output_scale']} units. The displayed final probability uses sigmoid calibration.")

with tab3:
    st.subheader(f"Selected model: {metrics['champion']}")
    st.dataframe(pd.DataFrame([{k:v for k,v in row.items() if k not in ['parameters','test_at_0_5']} for row in metrics['comparison']]),hide_index=True)
    st.json({'held_out_test':metrics['test_metrics'],'targets':metrics['success_targets'],
             'group_holdout':metrics['group_holdout_audit'],'customer_overlap_in_primary_split':metrics['test_customer_overlap']})
    if (OUT/'application_time_audit.json').exists():
        st.subheader('Application-time availability audit');st.json(json.loads((OUT/'application_time_audit.json').read_text()))
    st.image(str(OUT/'figures/model_evaluation.png'))
    importance=pd.read_csv(OUT/'feature_importance.csv').head(15).iloc[::-1]
    chart(px.bar(importance,x='mean_absolute_shap',y='feature',orientation='h',title='Global feature importance'))
    st.caption('Outcome data exist only for approved, disbursed loans. Selection bias, undated outcomes, profile timestamps, and fairness validation limit use beyond this demonstration.')
    if (OUT/'customer_model/metrics.json').exists():
        st.subheader('Customer profile model evidence')
        st.json(json.loads((OUT/'customer_model/metrics.json').read_text()))
    if (OUT/'acceptance_status.json').exists():
        st.subheader('Objective acceptance status')
        st.json(json.loads((OUT/'acceptance_status.json').read_text()))
