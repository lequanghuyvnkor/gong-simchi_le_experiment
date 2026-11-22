"""Locked analysis of condition_study outputs. No training or configuration selection."""
from pathlib import Path
import json,sys,os,hashlib
import numpy as np,pandas as pd
import os
ROOT=Path(os.environ.get('GONG_RUN_DIR', str(Path(__file__).resolve().parents[2]/'local_checks/beer_rossmann'))).resolve()
OUT=ROOT/'outputs/condition_study'; W=ROOT/'work/condition_report_build'
sys.path.append(str(ROOT/'work/condition_plot_dependencies'))
os.environ['MPLCONFIGDIR']=str(ROOT/'work/mplconfig_conditions')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'axes.spines.top':False,'axes.spines.right':False})
FIG=W/'figures';FIG.mkdir(parents=True,exist_ok=True)
ALG=['SRDQN-A','Meta-HQL-P','Meta-HQL-T']

def finite_json(x):
    if isinstance(x,dict):return {k:finite_json(v) for k,v in x.items()}
    if isinstance(x,list):return [finite_json(v) for v in x]
    if isinstance(x,float) and not np.isfinite(x):return None
    return x

def effect(s,m):
    den=(np.mean(s,axis=-1)+np.mean(m,axis=-1))/2
    return np.divide(100*(np.mean(s,axis=-1)-np.mean(m,axis=-1)),den,out=np.zeros_like(den),where=den>0)

def paired(g,metric,alpha,nboot=20000,salt=100):
    # Four prescribed profiles are a fixed panel; seed is the repeated-run block.
    v=g.pivot_table(index='seed',columns='algorithm',values=metric,aggfunc='mean')[ALG[:2]].dropna()
    s=v.iloc[:,0].to_numpy();m=v.iloc[:,1].to_numpy()
    rng=np.random.default_rng(salt);ix=rng.integers(len(s),size=(nboot,len(s)))
    delta=effect(s[ix],m[ix]);lo,hi=np.quantile(delta,[alpha/2,1-alpha/2])
    e=float(effect(s,m))
    winner='SRDQN-A' if hi < -5 else ('Meta-HQL-P' if lo > 5 else ('Tương đương' if lo>=-5 and hi<=5 else 'Chưa rõ'))
    return dict(effect=e,lo=float(lo),hi=float(hi),decision=winner,SRDQN=float(s.mean()),MetaP=float(m.mean()),n_seeds=len(s))

def crossed_source(g,metric,alpha,nboot=20000,salt=400):
    v=g[g.algorithm.isin(ALG[:2])].copy()
    v['store']=v.series_id.str.extract(r'(s\d+)')[0]
    # Beer items are nested within stores. Bootstrap stores and algorithm seeds independently.
    v=v.groupby(['store','seed','algorithm'])[metric].mean().unstack('algorithm')
    stores=v.index.get_level_values('store').unique();seeds=v.index.get_level_values('seed').unique()
    s=v[ALG[0]].unstack('seed').reindex(index=stores,columns=seeds).to_numpy()
    m=v[ALG[1]].unstack('seed').reindex(index=stores,columns=seeds).to_numpy()
    assert np.isfinite(s).all() and np.isfinite(m).all()
    rng=np.random.default_rng(salt);vals=[]
    for k in range(0,nboot,500):
        n=min(500,nboot-k);ii=rng.integers(len(stores),size=(n,len(stores)))
        jj=rng.integers(len(seeds),size=(n,len(seeds)))
        ss=s[ii[:,:,None],jj[:,None,:]].mean(1);mm=m[ii[:,:,None],jj[:,None,:]].mean(1)
        vals.extend(effect(ss,mm))
    lo,hi=np.quantile(vals,[alpha/2,1-alpha/2]);e=float(effect(s.ravel(),m.ravel()))
    winner='SRDQN-A' if hi < -5 else ('Meta-HQL-P' if lo > 5 else ('Tương đương' if lo>=-5 and hi<=5 else 'Chưa rõ'))
    return dict(effect=e,lo=float(lo),hi=float(hi),decision=winner,SRDQN=float(s.mean()),MetaP=float(m.mean()),n_seeds=len(seeds),n_stores=len(stores))

def collect(prefix,n):
    frames=[]
    for i in range(n):
        f=OUT/f'results_{prefix}_{i}.csv';df=pd.read_csv(f)
        assert set(df.algorithm)==set(ALG+['Prior constant','Prior weekday']),f'Incomplete {f}'
        frames.append(df)
    return pd.concat(frames,ignore_index=True)

def validate_metrics(df,mode):
    assert not df.duplicated(['case','profile','seed','algorithm','checkpoint']).any()
    assert df.frozen_cost.notna().all() and (df.frozen_cost>=0).all()
    assert df.frozen_fill.between(0,1).all() and df.frozen_inventory.between(0,4+1e-8).all()
    assert (df.frozen_cost+1e-8>=df.frozen_inventory).all()
    mean={}
    if mode in ['core','long']:
        from condition_study import demands
        rec=df[['case','a','cv','p','profile','seed']].drop_duplicates().to_dict('records')
        E=demands(rec,1400,2002 if mode=='core' else 3002)
        mean={(r['case'],r['profile'],r['seed']):float(E[i].astype(float).mean()) for i,r in enumerate(rec)}
        mu=np.array([mean[(r.case,r.profile,r.seed)] for r in df.itertuples()])
    else:
        audits=json.loads((OUT/f'source_audit_{mode}.json').read_text())
        mean={r['series_id']:r['test_mean_normalized'] for r in audits}
        mu=df.series_id.map(mean).to_numpy()
    expected=df.frozen_inventory+df.p*(1-df.frozen_fill)*mu
    err=float(np.max(abs(expected-df.frozen_cost)))
    assert err<2e-6,(mode,err)
    return {'rows':len(df),'duplicates':0,'bounds_passed':True,'max_cost_decomposition_error':err}

def maps(table,name,title):
    colors={'SRDQN-A':0,'Meta-HQL-P':1,'Tương đương':2,'Chưa rõ':3}
    fig,axs=plt.subplots(1,2,figsize=(9,4.1),layout='constrained')
    for ax,cv in zip(axs,[.25,.75]):
        sub=table[table.cv==cv].sort_values(['a','p']);z=np.array([colors[x] for x in sub.decision]).reshape(3,3)
        ax.imshow(z,cmap=ListedColormap(['#4379aa','#c9783f','#98b7a0','#e4e5e8']),vmin=0,vmax=3)
        for i,r in enumerate(sub.itertuples()):
            ax.text(i%3,i//3,f'{r.effect:+.1f}%',ha='center',va='center',fontsize=13,color='white' if r.decision in ALG[:2] else '#222')
        ax.set_xticks([0,1,2],['1','5','10']);ax.set_yticks([0,1,2],['0','0.4','0.8'])
        ax.set_xlabel('Mức phạt thiếu hàng p');ax.set_ylabel('Biên độ mùa vụ a');ax.set_title(f'Nhiễu theo pha CV = {cv}')
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color=c,label=l) for c,l in zip(['#4379aa','#c9783f','#98b7a0','#e4e5e8'],['SRDQN-A','Meta-HQL-P','Tương đương','Chưa rõ'])],loc='outside lower center',ncol=4,frameon=False,fontsize=11)
    fig.suptitle(title,fontsize=14);fig.savefig(FIG/f'{name}.png',dpi=250);plt.close(fig)

def main():
    core=collect('core',6);long=collect('long',6)
    assert len(core)==21600 and len(long)==1800,(len(core),len(long))
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    quality={'core':validate_metrics(core,'core'),'long':validate_metrics(long,'long')}
    core.to_csv(OUT/'combined_core.csv',index=False);long.to_csv(OUT/'combined_long.csv',index=False)
    # Secondary decision aid added after inspection of core results, not a primary test.
    z=core[(core.checkpoint==21000)&core.algorithm.isin(ALG[:2])].groupby(['case','a','cv','p','algorithm'])[['online_cost','frozen_cost']].mean().unstack('algorithm')
    b=z.reset_index()[['case','a','cv','p']].copy();b.columns=['case','a','cv','p']
    gap=z[('frozen_cost',ALG[0])]-z[('frozen_cost',ALG[1])]
    initial=z[('online_cost',ALG[1])]-z[('online_cost',ALG[0])]
    b['future_periods_break_even']=np.where((gap>0)&(initial>0),21000*initial/gap,np.nan)
    b.to_csv(OUT/'secondary_break_even.csv',index=False)
    locked=json.loads((OUT/'locked_selection.json').read_text())
    for name,sha in locked['files'].items():assert hashlib.sha256((OUT/f'selected_{name}.json').read_bytes()).hexdigest()==sha
    tables={}
    for metric,cp,label in [('frozen_cost',21000,'primary'),('online_cost',21000,'online'),('frozen_cost',7000,'early')]:
        rows=[]
        for i,((case,a,cv,p),g) in enumerate(core[core.checkpoint==cp].groupby(['case','a','cv','p'],sort=True)):
            rows.append(dict(case=case,a=a,cv=cv,p=p,**paired(g,metric,.05/18,salt=100+i)))
        table=pd.DataFrame(rows);table.to_csv(OUT/f'comparison_{label}.csv',index=False);tables[label]=table
    lr=[]
    for i,((case,cp),g) in enumerate(long.groupby(['case','checkpoint'])):
        r=g.iloc[0];lr.append(dict(case=case,checkpoint=int(cp),a=r.a,cv=r.cv,p=r.p,**paired(g,'frozen_cost',.05/6,salt=800+i)))
    lt=pd.DataFrame(lr);lt.to_csv(OUT/'comparison_long.csv',index=False)
    sr=[];sources=[]
    for k,ds in enumerate(['Beer','Rossmann']):
        df=pd.read_csv(OUT/f'results_source_{ds}.csv')
        assert set(df.algorithm)==set(ALG+['Prior constant','Prior weekday'])
        assert len(df)==(9000 if ds=='Beer' else 3000)
        quality[ds]=validate_metrics(df,ds)
        sources.append(df)
        for cp in [7000,21000]:
            for metric in ['frozen_cost','online_cost']:
                sr.append(dict(dataset=ds,checkpoint=cp,metric=metric,**crossed_source(df[df.checkpoint==cp],metric,.05/2,salt=500+k)))
    st=pd.DataFrame(sr);st.to_csv(OUT/'comparison_sources.csv',index=False)
    pd.concat(sources,ignore_index=True).to_csv(OUT/'combined_sources.csv',index=False)
    summary={
        'primary_counts':tables['primary'].decision.value_counts().to_dict(),
        'online_counts':tables['online'].decision.value_counts().to_dict(),
        'early_counts':tables['early'].decision.value_counts().to_dict(),
        'long_counts':lt[lt.checkpoint==70000].decision.value_counts().to_dict(),
        'core_means':core[core.checkpoint==21000].groupby('algorithm')[['online_cost','frozen_cost','frozen_fill','frozen_inventory']].mean().round(6).to_dict('index'),
        'source_means':pd.concat(sources).query('checkpoint==21000').groupby(['case','algorithm'])[['online_cost','frozen_cost','frozen_fill','frozen_inventory']].mean().round(6).reset_index().to_dict('records'),
        'training_models_main_per_algorithm':2160,'training_models_long_per_algorithm':180,'training_models_source_per_algorithm':1200,
        'training_interactions_per_algorithm':83160000,
        'notes':'Bootstrap percentile intervals approximate; primary 18 comparisons Bonferroni adjusted. Profile panel fixed.'}
    diags={p.stem:json.loads(p.read_text()) for p in OUT.glob('diagnostics_*.json')}
    summary['diagnostics']=diags
    summary['total_safeguards']=sum(v.get('Meta-HQL-P',{}).get('guards_total',0) for v in diags.values())
    summary['feedback_violations']=sum(v.get(k,{}).get('feedback_violations',0) for v in diags.values() for k in ALG[1:])
    (OUT/'analysis_summary.json').write_text(json.dumps(finite_json(summary),ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    (OUT/'result_quality.json').write_text(json.dumps(quality,indent=2),encoding='utf-8')
    maps(tables['primary'],'primary_map','Chi phí triển khai sau 21 000 quan sát')
    maps(tables['online'],'online_map','Chi phí bình quân trong 21 000 kỳ học')
    # Average across fixed cases/profiles/seeds; bars are descriptive, not confidence intervals.
    g=core.groupby(['checkpoint','algorithm']).frozen_cost.mean().unstack('algorithm').reindex(columns=ALG+['Prior weekday','Prior constant'])
    ax=g.plot.bar(figsize=(9,4),rot=0,color=['#4379aa','#c9783f','#89929b','#6c9c7a','#b5c8b4'])
    ax.set_xlabel('Số quan sát dùng để học');ax.set_ylabel('Chi phí triển khai mỗi kỳ')
    ax.legend(ncol=3,fontsize=11,frameon=False,loc='upper center',bbox_to_anchor=(.5,1.27))
    ax.figure.tight_layout();ax.figure.savefig(FIG/'checkpoints.png',dpi=250);plt.close(ax.figure)
    # Seasonal shapes are design inputs, not fitted from the source datasets.
    sys.path.insert(0,str(Path(__file__).resolve().parent));from condition_study import shape
    fig,ax=plt.subplots(figsize=(8.5,3.3))
    for pr in range(4):ax.plot(range(1,8),1+.8*shape(pr),marker='o',label=f'Dạng {pr}')
    ax.set(xlabel='Pha trong chu kỳ 7 kỳ',ylabel='Kỳ vọng nhu cầu theo pha',xticks=range(1,8))
    ax.legend(ncol=4,frameon=False,loc='upper center',bbox_to_anchor=(.5,1.22))
    fig.tight_layout();fig.savefig(FIG/'profiles.png',dpi=250);plt.close(fig)
    # Long horizon diagnostics with identical evaluation path for each checkpoint of a model.
    fig,axs=plt.subplots(1,2,figsize=(9,3.8),layout='constrained')
    for ax,a in zip(axs,[0,.8]):
        ss=lt[lt.a==a]
        for p in [1,5,10]:
            t=ss[ss.p==p].sort_values('checkpoint');ax.plot(t.checkpoint,t.effect,marker='o',label=f'p={p}')
        ax.axhline(0,color='#555',lw=.7);ax.axhspan(-5,5,color='#e5e5e5',alpha=.7)
        ax.set(title=f'a={a}, CV=0.75',xlabel='Số quan sát học',ylabel='Chênh lệch chi phí S trừ M (%)')
    handles,labels=axs[0].get_legend_handles_labels()
    fig.legend(handles,labels,ncol=3,frameon=False,loc='outside lower center')
    fig.savefig(FIG/'long.png',dpi=250);plt.close(fig)
    # Keep redirected Windows consoles usable even when their code page is not UTF-8.
    print(json.dumps({k:summary[k] for k in ['primary_counts','online_counts','long_counts','total_safeguards','feedback_violations']},ensure_ascii=True))

if __name__=='__main__':main()
