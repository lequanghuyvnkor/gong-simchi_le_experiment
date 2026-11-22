"""Hypothetical CFO calculator; parameterized archived formulas, no policy retraining."""
from pathlib import Path
import argparse,json,sys,math
import numpy as np,pandas as pd
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
S='SRDQN-A';M='Meta-HQL-P';B='Prior weekday'
STATUS='HYPOTHETICAL_NOT_STORE_ACTUALS'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assumptions',type=Path,default=HERE/'assumptions.json')
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--verify-default',action='store_true')
    args=parser.parse_args()
    assume=json.loads(args.assumptions.read_text())
    validate(assume)
    O=args.output_dir.resolve()
    if (O.is_relative_to(REPO) and not O.is_relative_to(REPO/'local_checks')) or 'inputs' in O.parts:
        parser.error('Use a working output directory outside inputs/ and tracked paths')
    O.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(REPO/'benchmarks/beer_rossmann'))
    from run import load_metrics
    d=pd.concat([load_metrics(REPO/'results/beer_rossmann'/f'results_core_{i}.npz') for i in range(6)],ignore_index=True)
    d=d[d.checkpoint==21000]
    (O/'effective_assumptions.json').write_text(json.dumps(assume,indent=2),encoding='utf-8')
    scale=assume['mean_units_per_day']*assume['holding_vnd_per_unit_day']; K=int(assume['periods_per_year'])
    def saving_interval(frame,alpha,salt):
        q=frame.pivot_table(index='seed',columns='algorithm',values='frozen_cost',aggfunc='mean')
        z=(q[B]-q[M]).to_numpy();rng=np.random.default_rng(salt)
        vals=z[rng.integers(len(z),size=(20000,len(z)))].mean(1)
        return tuple(float(x*K*scale) for x in np.quantile(vals,[alpha/2,1-alpha/2]))
    rows=[]
    for (case,a,cv,p),g in d.groupby(['case','a','cv','p']):
        z=g.groupby('algorithm')[['online_cost','frozen_cost','frozen_fill','frozen_inventory']].mean()
        cs,cm,cb=[z.loc[x,'frozen_cost'] for x in [S,M,B]]
        ls,lm=[z.loc[x,'online_cost'] for x in [S,M]]
        lo,hi=saving_interval(g,.05/18,6100+len(rows))
        rows.append(dict(case=case,a=a,cv=cv,p=p,SRDQN_cost=cs,Meta_cost=cm,weekday_cost=cb,
            SRDQN_fill=z.loc[S,'frozen_fill'],Meta_fill=z.loc[M,'frozen_fill'],weekday_fill=z.loc[B,'frozen_fill'],
            SRDQN_end_inventory=z.loc[S,'frozen_inventory'],Meta_end_inventory=z.loc[M,'frozen_inventory'],
            weekday_end_inventory=z.loc[B,'frozen_inventory'],
            assumed_h_vnd=assume['holding_vnd_per_unit_day'],assumed_mu_units_day=assume['mean_units_per_day'],assumed_loss_vnd=p*assume['holding_vnd_per_unit_day'],
            SRDQN_annual_vnd=K*scale*cs,Meta_annual_vnd=K*scale*cm,weekday_annual_vnd=K*scale*cb,
            Meta_gross_annual_saving_vs_SRDQN_vnd=K*scale*(cs-cm),
            Meta_gross_annual_saving_vs_weekday_vnd=K*scale*(cb-cm),
            Meta_gross_saving_vs_weekday_CI_low_vnd=lo,Meta_gross_saving_vs_weekday_CI_high_vnd=hi,
            Meta_online21k_excess_vs_SRDQN_vnd=21000*scale*(lm-ls),
            frozen_break_even_after_21k_online_periods=21000*(lm-ls)/(cs-cm)))
    t=pd.DataFrame(rows).sort_values(['cv','a','p']);t.to_csv(O/'18_condition_financial_scenarios.csv',index=False)
    by=d.groupby(['p','algorithm'])[['online_cost','frozen_cost','frozen_fill','frozen_inventory']].mean()
    stats=[]
    for p in [1,5,10]:
        z=by.loc[p];cs,cm,cb=[z.loc[x,'frozen_cost'] for x in [S,M,B]]
        lo,hi=saving_interval(d[d.p==p],.05,6210+p)
        stats.append(dict(p=p,SRDQN=cs,Meta=cm,weekday=cb,
            SRDQN_annual=K*scale*cs,Meta_annual=K*scale*cm,weekday_annual=K*scale*cb,
            saving_vs_SRDQN=K*scale*(cs-cm),saving_vs_weekday=K*scale*(cb-cm),
            saving_vs_weekday_pooled95_low=lo,saving_vs_weekday_pooled95_high=hi,
            Meta_fill=z.loc[M,'frozen_fill'],weekday_fill=z.loc[B,'frozen_fill'],
            end_inventory_capital_release_proxy_vs_weekday=assume['purchase_vnd_per_unit']*assume['mean_units_per_day']*(z.loc[B,'frozen_inventory']-z.loc[M,'frozen_inventory'])))
    ps=pd.DataFrame(stats);ps.to_csv(O/'p_level_financial_scenarios.csv',index=False)
    gain=float(ps.loc[ps.p==assume['p'],'saving_vs_weekday'].iloc[0]);F=assume['meta_incremental_setup_vnd_vs_existing_baseline'];run=assume['meta_incremental_annual_running_vnd_vs_existing_baseline'];r=assume['discount_rate_assumed']
    annuity=sum(1/(1+r)**y for y in [1,2,3])
    portfolio=[]
    for n in assume['portfolio_skus']:
        annual=n*gain-run
        portfolio.append(dict(n_identical_independent_skus=n,gross_annual_saving=n*gain,
            annual_net_before_setup=annual,first_year_net=annual-F,NPV_3_year=-F+annual*annuity,
            simple_payback_year=F/annual if annual>0 else None))
    pd.DataFrame(portfolio).to_csv(O/'illustrative_portfolio_tco.csv',index=False)
    summary={'scenario_count':len(t),'Meta_lower_than_weekday_point_estimate_cells':int((t.Meta_cost<t.weekday_cost).sum()),
        'annual_saving_per_sku_vs_weekday':gain,'npv_annuity_3yr':annuity,
        'selected_p':assume['p'],'discount_rate':r,
        'first_year_n_break_even':(F+run)/gain if gain>0 else None,'recurring_n_break_even':run/gain if gain>0 else None,
        'npv3_n_break_even':(F/annuity+run)/gain if gain>0 else None,
        'sample_B_h':assume['sample_B']['purchase_vnd_per_unit']*assume['sample_B']['holding_annual_fraction']/K,'sample_B_p':assume['sample_B']['lost_contribution_vnd_per_unit']/(assume['sample_B']['purchase_vnd_per_unit']*assume['sample_B']['holding_annual_fraction']/K),
        'online_frozen_break_even_min':float(t.frozen_break_even_after_21k_online_periods.min()),
        'online_frozen_break_even_max':float(t.frozen_break_even_after_21k_online_periods.max()),
        'original_21000_training_unchanged':True,'supplementary_pilot_training':True,
        'no_store_invoice_costs':True,'post_hoc_analysis':True}
    # Retain historical field names only when their literal p/r labels apply.
    if assume['p']==10:summary['annual_p10_saving_per_sku_vs_weekday']=gain
    if r==.12:summary['npv_annuity_3yr_12pct']=annuity
    (O/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')

    pilot=load_metrics(REPO/'results/cfo/pilot_metrics.npz')
    pilot['total_cost_vnd_sample']=pilot.horizon*scale*pilot.mean_cost
    pilot.groupby(['horizon','p','algorithm'])[['mean_cost','fill','total_cost_vnd_sample']].mean().reset_index().to_csv(O/'pilot_financial_summary.csv',index=False)
    current=ps[ps.p==assume['p']].iloc[0]
    pd.DataFrame([dict(n_skus=n,baseline_operating_annual=n*current.weekday_annual,meta_operating_annual=n*current.Meta_annual,setup_once=F,system_annual=run,meta_first_year_TCO=n*current.Meta_annual+F+run,baseline_first_year_TCO=n*current.weekday_annual) for n in assume['portfolio_skus']]).to_csv(O/'tco_components.csv',index=False)
    for path in O.glob('*.csv'):
        frame=pd.read_csv(path);frame['assumption_status']=STATUS;frame.to_csv(path,index=False)
    if args.verify_default:
        default=json.loads((HERE/'assumptions.json').read_text())
        if assume!=default:parser.error('--verify-default requires the unchanged assumptions.json')
        for expected in (REPO/'results/cfo').glob('*.csv'):
            pd.testing.assert_frame_equal(pd.read_csv(O/expected.name),pd.read_csv(expected),check_dtype=False,rtol=1e-9,atol=1e-6)
        expected=json.loads((REPO/'results/cfo/summary.json').read_text())
        for k,v in expected.items():
            assert summary[k]==v if not isinstance(v,float) else np.isclose(summary[k],v,rtol=1e-9,atol=1e-6),(k,summary[k],v)
    record={'status':STATUS,'python':sys.version,'numpy':np.__version__,'pandas':pd.__version__,'verified_default':args.verify_default,'scope':'Financial recalculation of saved policies and saved pilot metrics; no full benchmark retraining'}
    (O/'validation.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    lines=['# CFO — giả định mẫu, không phải chi phí doanh nghiệp thật','',f"Nhu cầu mốc {assume['mean_units_per_day']} đơn vị/ngày; h={assume['holding_vnd_per_unit_day']} VND/đơn vị/ngày. Sample p={assume['p']}; hệ số tiền mỗi kỳ={scale} VND. Chính sách giữ nguyên; dữ liệu mô phỏng, chưa có hóa đơn doanh nghiệp.",'',f'Setup tăng thêm {F} VND; hệ thống mỗi năm {run} VND; discount={r}. Giá trị tồn kho là proxy vốn, không cộng như tiết kiệm lặp lại.','',f'Tiết kiệm vận hành mỗi SKU/năm so với weekday: {gain:.6f} VND.', '', 'TCO gồm vận hành sau học + setup + hệ thống. Không cộng chi phí vận hành giả lập trong train offline như tiền đã chi. Chi phí học trực tiếp 365 kỳ nằm riêng trong pilot_financial_summary.csv; chưa cộng vào TCO triển khai policy đã đóng băng. Bảng hòa vốn online dùng 21000 kỳ đã học, chưa gồm hệ thống. Các bảng CSV có nhãn HYPOTHETICAL_NOT_STORE_ACTUALS.', '', 'Xem effective_assumptions.json, 18_condition_financial_scenarios.csv, p_level_financial_scenarios.csv, illustrative_portfolio_tco.csv, tco_components.csv, pilot_financial_summary.csv và summary.json.']
    (O/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(record,indent=2))

def validate(a):
    if a['status']!=STATUS:raise ValueError('Hypothetical status must remain explicit')
    for k in ['mean_units_per_day','holding_vnd_per_unit_day','purchase_vnd_per_unit','periods_per_year']:
        if not math.isfinite(a[k]) or a[k]<=0:raise ValueError(k)
    for k in ['meta_incremental_setup_vnd_vs_existing_baseline','meta_incremental_annual_running_vnd_vs_existing_baseline','lost_contribution_vnd_per_unit']:
        if not math.isfinite(a[k]) or a[k]<0:raise ValueError(k)
    if a['periods_per_year']!=int(a['periods_per_year']):raise ValueError('periods_per_year must be integer')
    if not math.isfinite(a['discount_rate_assumed']) or a['discount_rate_assumed']<=-1:raise ValueError('Invalid discount rate')
    if a['p'] not in [1,5,10] or not np.isclose(a['lost_contribution_vnd_per_unit']/a['holding_vnd_per_unit_day'],a['p']):raise ValueError('Changed penalty ratio requires a matched policy experiment; choose p in {1,5,10}')
    if not np.isclose(a['selling_price_vnd']-a['purchase_vnd_per_unit']-a['avoidable_fulfilment_vnd'],a['lost_contribution_vnd_per_unit']):raise ValueError('Lost contribution must equal price minus purchase and avoidable fulfilment')
    if not np.isclose(a['physical_inventory_cap'],4*a['mean_units_per_day']):raise ValueError('Keep normalized capacity 4; changed model requires rerun')
    if a['policy_drift_assumed']:raise ValueError('Saved policies do not support a drift forecast')
    if not a['portfolio_skus'] or any(not isinstance(n,int) or isinstance(n,bool) or n<=0 for n in a['portfolio_skus']):raise ValueError('Positive integer SKU counts required')
    if any(not math.isfinite(v) or v<=0 for v in a['sample_B'].values()):raise ValueError('Invalid Sample B assumptions')

if __name__=='__main__':main()
