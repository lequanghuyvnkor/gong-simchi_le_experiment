"""Post-hoc 365-period cold-start learning simulation with financial sample costs."""
from pathlib import Path
import json,sys,time
import numpy as np
import pandas as pd
import os
ROOT=Path(os.environ['GONG_RUN_DIR']).resolve()
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'benchmarks/beer_rossmann'))
import condition_study as s
O=ROOT/'outputs/cfo_analysis';O.mkdir(exist_ok=True)
cfg={a:json.loads((ROOT/'outputs/condition_study'/f'selected_{a}.json').read_text())['config'] for a in ['SRDQN-A','Meta-HQL-P']}
design={'status':'POST_HOC_SUPPLEMENTARY_SIMULATION','train_periods':365,'checkpoints':[30,90,365],
    'cases':s.scenarios(),'profiles':[0,1,2,3],'seeds':list(range(6000,6030)),
    'demand_split':6601,'config':cfg,'retuned_for_short_horizon':False,
    'known_horizon_for_Meta':365,'baseline_prior_samples':3500,
    'baseline_information':'Weekday policy estimated from separate privileged synthetic history; cold-start learners not warm-started.',
    'actual_store_trial':False,'cost_unit':'normalized h=1; hypothetical VND uses mu=100 h=100'}
(O/'pilot_design.json').write_text(json.dumps(design,indent=2),encoding='utf-8')
rows=[];diags=[]
for block in range(6):
    rec=s.records(s.scenarios()[block*3:(block+1)*3],[0,1,2,3],list(range(6000,6030)))
    D=s.demands(rec,365,6601);E=s.demands(rec,7,6602)
    p=np.array([r['p'] for r in rec]);key=s.identity(rec)
    for alg in ['SRDQN-A','Meta-HQL-P']:
        ans,diag=s.train(D,E,p,alg,cfg[alg],key,[30,90,365],log=False)
        diags.append({'block':block,'algorithm':alg,**diag})
        for horizon,z in ans.items():
            for i,r in enumerate(rec):rows.append({**r,'algorithm':alg,'horizon':horizon,
                'mean_cost':float(z['online_cost'][i]),'fill':float(z['online_fill'][i]),
                'total_cost_vnd_sample':float(horizon*10000*z['online_cost'][i])})
    baseline=s.population_references(rec)['Prior weekday']
    for horizon in [30,90,365]:
        z=s.evaluate(D[:,:horizon],p,policy=baseline)
        for i,r in enumerate(rec):rows.append({**r,'algorithm':'Prior weekday','horizon':horizon,
            'mean_cost':float(z['cost'][i]),'fill':float(z['fill'][i]),
            'total_cost_vnd_sample':float(horizon*10000*z['cost'][i])})
    print('pilot block',block+1,'/6 finished',flush=True)
d=pd.DataFrame(rows);d.to_csv(O/'results_pilot.csv',index=False)
d.groupby(['horizon','p','algorithm'])[['mean_cost','fill','total_cost_vnd_sample']].mean().reset_index().to_csv(O/'pilot_financial_summary.csv',index=False)
(O/'pilot_diagnostics.json').write_text(json.dumps(diags,indent=2),encoding='utf-8')
assert len(d)==18*4*30*3*3
assert np.isfinite(d[['mean_cost','fill','total_cost_vnd_sample']]).all().all()
print('pilot rows',len(d),flush=True)
