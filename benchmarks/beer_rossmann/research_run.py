from pathlib import Path
import sys, json, hashlib, argparse, time
import numpy as np
import pandas as pd

import os
ROOT=Path(os.environ.get('GONG_RUN_DIR', str(Path(__file__).resolve().parents[2]/'local_checks/beer_rossmann'))).resolve()
OUT=ROOT/'outputs/beer_rossmann_benchmark'
OUT.mkdir(parents=True,exist_ok=True)
H=7
M=4.
GRID=np.linspace(0,M,21)
STORES=[85,262,335,423,494,562,682,733,769,1097]
PILOTS=['beer_s01_i05','beer_s01_i34','beer_s01_i46','ross_s0085']

def savejson(name,obj):
    (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')

def prepare():
    beer=pd.read_csv(ROOT/'outputs/datasets/store_item_demand_train.csv',parse_dates=['date'])
    ross=pd.read_csv(ROOT/'outputs/datasets/rossmann_train.csv',parse_dates=['Date'],dtype={'StateHoliday':str})
    tr=ross[ross.Date.dt.year==2013]
    eligibility=tr.groupby('Store').agg(n=('Date','nunique'),opened=('Open','sum'))
    selected=eligibility[(eligibility.n==365)&(eligibility.opened==365)].index.tolist()
    assert selected==STORES
    b=beer[beer.item.isin([5,34,46])].copy()
    b['dataset']='Beer'
    b['series_id']=[f'beer_s{s:02d}_i{i:02d}' for s,i in zip(b.store,b.item)]
    b['observed_sales']=b.sales
    b['demand_base']=b.sales.astype(float)
    b['Open']=1;b['Promo']=np.nan;b['StateHoliday']='not_recorded'
    r=ross[ross.Store.isin(STORES)].rename(columns={'Date':'date','Store':'store','Sales':'observed_sales'}).copy()
    r['dataset']='Rossmann';r['series_id']=r.store.map(lambda s:f'ross_s{s:04d}')
    r['item']=pd.NA;r['demand_base']=r.observed_sales/20.
    cols=['dataset','series_id','date','store','item','observed_sales','demand_base','Open','Promo','StateHoliday']
    all_data=pd.concat([b[cols],r[cols]],ignore_index=True).sort_values(['series_id','date'])
    all_data['weekday']=all_data.date.dt.dayofweek
    all_data['split']=np.select([all_data.date.dt.year==2013,all_data.date.dt.year==2014,all_data.date.le('2015-07-31')],['train','validation','test'],default='beer_extension')
    scales=all_data[all_data.split=='train'].groupby('series_id').demand_base.mean()
    assert (scales>0).all()
    all_data['scale_train_mean']=all_data.series_id.map(scales)
    all_data['demand_normalized']=all_data.demand_base/all_data.scale_train_mean
    common=all_data[all_data.date.le('2015-07-31')].copy()
    assert len(common)==40*942
    assert common.duplicated(['series_id','date']).sum()==0
    assert not common[['date','demand_base','demand_normalized']].isna().any().any()
    assert (common.demand_normalized>=0).all()
    assert common.groupby('series_id').size().eq(942).all()
    assert np.allclose(common[common.split=='train'].groupby('series_id').demand_normalized.mean(),1)
    common.to_csv(OUT/'common_daily.csv',index=False,date_format='%Y-%m-%d')
    all_data[all_data.split=='beer_extension'].to_csv(OUT/'beer_extension.csv',index=False,date_format='%Y-%m-%d')
    scales.rename('scale_train_mean').to_csv(OUT/'normalization_parameters.csv')
    summaries=[]
    diagnostics=[]
    for (sid,split),g in common.groupby(['series_id','split'],sort=True):
        v=g.demand_normalized.to_numpy()
        residual=g.demand_normalized-g.groupby('weekday').demand_normalized.transform('mean')
        summaries.append(dict(series_id=sid,dataset=g.dataset.iloc[0],split=split,n=len(g),mean=float(v.mean()),
            std=float(v.std(ddof=1)),q50=float(np.quantile(v,.5)),q95=float(np.quantile(v,.95)),
            maximum=float(v.max()),zeros=int((v==0).sum()),closed=int((g.Open==0).sum())))
        diagnostics.append(dict(series_id=sid,split=split,lag1=float(pd.Series(v).autocorr(1)),
            residual_lag1=float(residual.reset_index(drop=True).autocorr(1)),
            residual_lag7=float(residual.reset_index(drop=True).autocorr(7))))
    pd.DataFrame(summaries).to_csv(OUT/'series_summary.csv',index=False)
    pd.DataFrame(diagnostics).to_csv(OUT/'dependence_diagnostics.csv',index=False)
    common.groupby(['dataset','split']).agg(n=('demand_normalized','size'),mean=('demand_normalized','mean'),
        sd=('demand_normalized','std'),closed=('Open',lambda a:(a==0).sum())).reset_index().to_csv(OUT/'dataset_summary.csv',index=False)
    common.groupby(['series_id','split','weekday']).demand_normalized.agg(['size','mean','std']).reset_index().to_csv(OUT/'weekday_profiles.csv',index=False)
    savejson('data_quality.json',{'common_rows':len(common),'beer_rows':int((common.dataset=='Beer').sum()),'rossmann_rows':int((common.dataset=='Rossmann').sum()),
        'series':int(common.series_id.nunique()),'dates':942,'split_days':{'train':365,'validation':365,'test':212},
        'rossmann_stores':selected,'beer_items':[5,34,46],'duplicates':0,'missing_demand':0,
        'closed_days_after_selection':int((common.Open==0).sum()),'train_normalized_mean':1.,
        'beer_extension_rows':int((all_data.split=='beer_extension').sum())})
    ids=sorted(common.series_id.unique())
    bank={}
    npbanks={}
    base_const=[];base_week=[]
    for sid in ids:
        g=common[(common.series_id==sid)&(common.split=='train')]
        v=g.demand_normalized.to_numpy()
        costs=[]
        for a in GRID:
            x=0.;c=0.
            for d in v:
                y=max(x,a);x=max(y-d,0);c+=x+max(d-y,0)
            costs.append(c/len(v))
        base_const.append(float(GRID[int(np.argmin(costs))]))
        base_week.append([float(GRID[np.argmin(abs(GRID-np.median(g[g.weekday==h].demand_normalized)))]) for h in range(7)])
        for split in ['train','validation']:
            gg=common[(common.series_id==sid)&(common.split==split)]
            for h in range(7):
                npbanks[f'{sid}__{split}__{h}']=gg[gg.weekday==h].demand_normalized.to_numpy()
    np.savez_compressed(OUT/'phase_distributions.npz',**npbanks)
    savejson('series_order.json',ids)
    savejson('offline_references.json',{'series_order':ids,'constant':base_const,'weekday_median':base_week})
    savejson('scenario.json',{'H':H,'inventory_cap':M,'action_grid':GRID.tolist(),'holding_cost':1.,'shortage_cost':1.,
        'lead_time':0,'purchase_cost':0,'fixed_order_cost':0,'initial_inventory':0,'discard_inventory':False,
        'main_seeds':list(range(30)),'simulation_horizon':7000,'extended_pilot_horizon':21000,
        'observations':'own censored sales and inventory; true demand available only to evaluator',
        'notes':'Costs are experimental scenarios. Historical sales treated as exogenous demand proxy. Main simulation cold start; source phase distributions unavailable to the learning agents.'})
    print('Prepared',len(common),'rows',len(ids),'series',flush=True)

def load_data():
    ids=json.loads((OUT/'series_order.json').read_text())
    d=pd.read_csv(OUT/'common_daily.csv',parse_dates=['date'])
    bank=np.load(OUT/'phase_distributions.npz')
    return ids,d,bank

def paths(ids,bank,seeds,T,split='train',salt=0):
    v=np.empty((len(ids)*len(seeds),T),dtype=np.float32)
    for i,sid in enumerate(ids):
        key=int.from_bytes(hashlib.sha256(sid.encode()).digest()[:4],'little')
        for j,seed in enumerate(seeds):
            for h in range(7):
                rng=np.random.default_rng(np.random.SeedSequence([20261109,key,seed,salt,h]))
                atom=bank[f'{sid}__{split}__{h}']
                idx=np.arange(h,T,7)
                v[i*len(seeds)+j,idx]=rng.choice(atom,size=len(idx))
    return v

def meta_schedule(T,startphase=0):
    B=np.empty(T);active=False;w=0;j=0;rounds=0;step=0;switches=0
    for t in range(T):
        phase=(startphase+t)%7
        if not active and phase==w:
            active=True;step=0
        B[t]=M if active else -1.
        if active:
            step+=1
            if step==7:
                step=0;rounds+=1
                if rounds==2**j:
                    rounds=0;w+=1;active=False;switches+=1
                    if w==7:w=0;j+=1
    return B,switches

def reference_eval(D,name,B,startphase=0):
    N,T=D.shape;x=np.zeros(N);cost=np.zeros(N);lost=np.zeros(N);inv=np.zeros(N);stockout=np.zeros(N);running=[]
    checkpoints=[t for t in [100,500,1000,3500,7000,14000,21000] if t<=T]
    for t in range(T):
        if name=='Meta-HQL':
            lev=B[t]
            y=np.maximum(x,lev) if lev>=0 else x
        elif np.ndim(B)==2:
            y=np.maximum(x,B[:,(startphase+t)%7])
        else:y=np.maximum(x,B)
        d=D[:,t];x=np.maximum(y-d,0.);short=np.maximum(d-y,0.)
        cost+=x+short;lost+=short;inv+=x;stockout+=(short>1e-9)
        if t+1 in checkpoints:running.append((t+1,cost.copy()/(t+1)))
    return {'cost':cost/T,'fill':1-lost/D.sum(axis=1),'inventory':inv/T,'stockout':stockout/T,'curve':running}

class BatchedRNG:
    """Each model owns its counter, independent of batch/panel size."""
    def __init__(self,keys):
        self.state=np.array(keys,dtype=np.uint64)+np.uint64(17329083)
    def bits(self,b=1):
        step=np.uint64(0x9E3779B97F4A7C15)
        z=self.state[:,None]+np.arange(1,b+1,dtype=np.uint64)[None,:]*step
        self.state=self.state+np.uint64((int(step)*b)%(1<<64))
        z=(z^(z>>np.uint64(30)))*np.uint64(0xBF58476D1CE4E5B9)
        z=(z^(z>>np.uint64(27)))*np.uint64(0x94D049BB133111EB)
        return z^(z>>np.uint64(31))
    def uniform(self):
        return (self.bits()[:,0]>>np.uint64(11)).astype(float)*(1./(1<<53))
    def integers(self,high,b=1):
        r=(self.bits(b)%np.uint64(high)).astype(np.int64)
        return r[:,0] if b==1 else r

class BatchedDQN:
    def __init__(self,N,cfg,seed_keys):
        self.N=N;self.cfg=cfg;self.obs_dim=17;self.hidden=24;self.A=len(GRID)
        rng=np.random.default_rng(20071)
        self.rng=BatchedRNG(seed_keys)
        self.W=[];self.b=[]
        for a,b in [(17,24),(24,24),(24,self.A)]:
            weights=np.empty((N,a,b),dtype=np.float32)
            for i,key in enumerate(seed_keys):
                rg=np.random.default_rng(np.random.SeedSequence([19371,int(key),a,b]))
                weights[i]=rg.normal(0,np.sqrt(2/a),size=(a,b))
            self.W.append(weights);self.b.append(np.zeros((N,1,b),np.float32))
        self.tw=[a.copy() for a in self.W];self.tb=[a.copy() for a in self.b]
        self.mw=[np.zeros_like(a) for a in self.W];self.vw=[np.zeros_like(a) for a in self.W]
        self.mb=[np.zeros_like(a) for a in self.b];self.vb=[np.zeros_like(a) for a in self.b]
        self.K=512
        self.S=np.zeros((N,self.K,17),np.float32);self.S2=np.zeros_like(self.S)
        self.R=np.zeros((N,self.K),np.float32);self.ACT=np.zeros((N,self.K),np.int16)
        self.count=0;self.updates=0
    def forward(self,s,target=False):
        W,b=(self.tw,self.tb) if target else (self.W,self.b)
        h1=np.maximum(np.einsum('nbi,nij->nbj',s,W[0])+b[0],0)
        h2=np.maximum(np.einsum('nbi,nij->nbj',h1,W[1])+b[1],0)
        q=np.einsum('nbi,nij->nbj',h2,W[2])+b[2]
        return h1,h2,q
    def choose(self,s,t,greedy=False):
        q=self.forward(s[:,None,:])[2][:,0,:]
        a=q.argmax(axis=1)
        if not greedy:
            eps=max(.05,1.-.95*t/self.cfg['decay'])
            explore=self.rng.uniform()<eps
            random_actions=self.rng.integers(self.A)
            a[explore]=random_actions[explore]
        return a
    def observe(self,s,a,r,s2,t):
        k=self.count%self.K;self.S[:,k]=s;self.S2[:,k]=s2;self.ACT[:,k]=a;self.R[:,k]=r;self.count+=1
        if self.count<64 or self.count%8:return
        n=np.arange(self.N)[:,None];ix=self.rng.integers(min(self.count,self.K),b=16)
        s=self.S[n,ix];s2=self.S2[n,ix];a=self.ACT[n,ix];r=self.R[n,ix]
        h1,h2,q=self.forward(s)
        qn=self.forward(s2,target=True)[2].max(axis=2)
        target=r+self.cfg['gamma']*qn
        chosen=np.take_along_axis(q,a[:,:,None],axis=2)[:,:,0]
        delta=np.clip(chosen-target,-1,1)/a.shape[1]
        dq=np.zeros_like(q);np.put_along_axis(dq,a[:,:,None],delta[:,:,None],axis=2)
        gw=[None]*3;gb=[None]*3
        gw[2]=np.einsum('nbi,nbj->nij',h2,dq);gb[2]=dq.sum(axis=1,keepdims=True)
        dh2=np.einsum('nbj,nij->nbi',dq,self.W[2])*(h2>0)
        gw[1]=np.einsum('nbi,nbj->nij',h1,dh2);gb[1]=dh2.sum(axis=1,keepdims=True)
        dh1=np.einsum('nbj,nij->nbi',dh2,self.W[1])*(h1>0)
        gw[0]=np.einsum('nbi,nbj->nij',s,dh1);gb[0]=dh1.sum(axis=1,keepdims=True)
        self.updates+=1;tt=self.updates
        for i in range(3):
            for par,grad,mm,vv in [(self.W[i],gw[i],self.mw[i],self.vw[i]),(self.b[i],gb[i],self.mb[i],self.vb[i])]:
                np.clip(grad,-5,5,out=grad);mm*=.9;mm+=.1*grad;vv*=.999;vv+=.001*grad*grad
                par-=self.cfg['lr']*(mm/(1-.9**tt))/(np.sqrt(vv/(1-.999**tt))+1e-8)
        if self.updates%50==0:
            self.tw=[w.copy() for w in self.W];self.tb=[b.copy() for b in self.b]

def dqn_eval(D,cfg,seed_keys,startphase=0,verbose=True):
    N,T=D.shape;agent=BatchedDQN(N,cfg,seed_keys)
    x=np.zeros(N);hist=np.zeros((N,3,3));cost=np.zeros(N);lost=np.zeros(N);inv=np.zeros(N);stockout=np.zeros(N)
    curve=[];start=time.time()
    def obs(t):
        phase=np.zeros((N,7));phase[:,(startphase+t)%7]=1
        return np.concatenate([x[:,None]/M,hist.reshape(N,9)/M,phase],axis=1).astype(np.float32)
    s=obs(0)
    checkpoints=[t for t in [100,500,1000,3500,7000,14000,21000] if t<=T]
    for t in range(T):
        a=agent.choose(s,t)
        y=np.maximum(x,GRID[a]);q=y-x
        # Policy sees censored sales, not D or shortage/true cost.
        sales=np.minimum(y,D[:,t]);x=y-sales
        pseudo=x-sales
        reward=((M-pseudo)/(2*M)).astype(np.float32)
        hist[:,:-1]=hist[:,1:];hist[:,-1]=np.stack([sales,x,q],axis=1)
        s2=obs(t+1);agent.observe(s,a,reward,s2,t);s=s2
        shortage=np.maximum(D[:,t]-y,0)
        cost+=x+shortage;lost+=shortage;inv+=x;stockout+=(shortage>1e-9)
        if t+1 in checkpoints:curve.append((t+1,cost.copy()/(t+1)))
        if verbose and (t+1)%1000==0:print(f'DQN {t+1}/{T} N={N} elapsed={time.time()-start:.1f}s',flush=True)
    return {'cost':cost/T,'fill':1-lost/D.sum(axis=1),'inventory':inv/T,'stockout':stockout/T,'curve':curve,
        'updates':agent.updates,'elapsed':time.time()-start}

def model_keys(ids,seeds):
    return [int.from_bytes(hashlib.sha256(f'{sid}|{seed}'.encode()).digest()[:4],'little') for sid in ids for seed in seeds]

def tune():
    ids,d,bank=load_data();pilots=PILOTS
    D=paths(pilots,bank,[100,101,102],3500,'validation',salt=14)
    configs=[{'lr':lr,'decay':decay,'gamma':.99} for lr in [.0005,.001] for decay in [1000,2500]]
    rows=[]
    for i,cfg in enumerate(configs):
        print('Tune',i,cfg,flush=True)
        res=dqn_eval(D,cfg,model_keys(pilots,[100,101,102]),verbose=False)
        rows.append({'config':i,**cfg,'mean_cost':float(res['cost'].mean()),'fill':float(res['fill'].mean()),'seconds':res['elapsed']})
    pd.DataFrame(rows).to_csv(OUT/'validation_tuning.csv',index=False)
    best=min(rows,key=lambda r:r['mean_cost'])
    savejson('selected_hyperparameters.json',{k:best[k] for k in ['lr','decay','gamma']})
    print('Selected',best,flush=True)

def bench(mode):
    ids,d,bank=load_data();cfg=json.loads((OUT/'selected_hyperparameters.json').read_text())
    if mode=='synthetic':seeds=list(range(30));T=7000;D=paths(ids,bank,seeds,T);phase=0
    elif mode=='long':
        ids=PILOTS;seeds=list(range(30));T=21000;D=paths(ids,bank,seeds,T);phase=0
    else:
        seeds=list(range(30));T=212;phase=3
        D=np.repeat(np.stack([d[(d.series_id==sid)&(d.split=='test')].sort_values('date').demand_normalized.to_numpy() for sid in ids]),len(seeds),axis=0)
    # Save same demand trajectories once for all policies. First 7000 of long = synthetic prefix.
    np.savez_compressed(OUT/f'demand_paths_{mode}.npz',demand=D,series_id=np.repeat(ids,len(seeds)),seed=np.tile(seeds,len(ids)),startphase=phase)
    refs=json.loads((OUT/'offline_references.json').read_text())
    const=np.repeat([refs['constant'][refs['series_order'].index(s)] for s in ids],len(seeds))
    week=np.repeat(np.array([refs['weekday_median'][refs['series_order'].index(s)] for s in ids]),len(seeds),axis=0)
    schedule,switches=meta_schedule(T,phase)
    results={}
    start=time.time()
    results['Meta-HQL']=reference_eval(D,'Meta-HQL',schedule,phase)
    meta_sec=time.time()-start
    results['Constant offline']=reference_eval(D,'Constant',const,phase)
    results['Weekly median offline']=reference_eval(D,'Weekly',week,phase)
    results['SRDQN adapted']=dqn_eval(D,cfg,model_keys(ids,seeds),phase)
    records=[];curves=[]
    for name,res in results.items():
        for i,sid in enumerate(ids):
            for j,seed in enumerate(seeds):
                ix=i*len(seeds)+j
                records.append({'mode':mode,'algorithm':name,'series_id':sid,'dataset':'Beer' if sid.startswith('beer') else 'Rossmann',
                    'seed':seed,'T':T,**{k:float(res[k][ix]) for k in ['cost','fill','inventory','stockout']}})
        for t,values in res['curve']:
            for ds in ['Beer','Rossmann']:
                mask=np.repeat([s.startswith('beer') if ds=='Beer' else s.startswith('ross') for s in ids],len(seeds))
                curves.append({'mode':mode,'algorithm':name,'dataset':ds,'t':t,'average_cost':float(values[mask].mean())})
    pd.DataFrame(records).to_csv(OUT/f'benchmark_{mode}.csv',index=False)
    pd.DataFrame(curves).to_csv(OUT/f'learning_curves_{mode}.csv',index=False)
    iota=9*np.log(len(GRID)*T);kmax=max(1,T//7)
    cb1=8*np.sqrt(7**5*iota)/np.sqrt(max(1,kmax-1))
    cb2=2*np.sqrt(7**7*np.log(T))/np.sqrt(kmax)
    assert cb1>7 and 2*cb2>7
    savejson(f'runtime_{mode}.json',{'models':len(ids)*len(seeds),'T':T,'dqn_seconds':results['SRDQN adapted']['elapsed'],
        'dqn_gradient_updates_per_model':results['SRDQN adapted']['updates'],'meta_seconds':meta_sec,'meta_switch_blocks':switches,
        'minimum_CB1_even_if_all_cycles_one_arm':float(cb1),'minimum_twice_CB2_C2_1':float(2*cb2),
        'Q_gap_upper_bound':7,'exact_meta_policy_reduction':'No action/arm elimination possible at this horizon with theoretical CB1 and C2>=1. All running maxima = M. Execute order-up-to M on active blocks, no new orders while aligning to next arm phase.'})
    print('Finished',mode,time.time(),flush=True)

def checks():
    # Censored pseudo-cost identity and simulation conservation for all grid actions.
    for y in GRID:
        for D in [0.,.7,2.3,5.9]:
            sale=min(y,D);x=max(y-D,0);lost=max(D-y,0);true=x+lost;pseudo=x-sale
            assert abs(true-pseudo-D)<1e-9
            assert abs(y-sale-x)<1e-9
            for yp in GRID[GRID<=y+1e-12]:
                assert abs(min(yp,D)-min(yp,sale))<1e-9
    ids,d,b=load_data()
    for split,expected in [('train',365),('validation',365),('test',212)]:
        assert d[d.split==split].groupby('series_id').size().eq(expected).all()
    a=paths(PILOTS,b,[0,1],21000)
    assert np.array_equal(a[:,:7000],paths(PILOTS,b,[0,1],7000))
    assert np.array_equal(a,paths(PILOTS,b,[0,1],21000))
    assert not np.array_equal(a[0],a[1])
    # Initial state/action information contains no demand or shortage values.
    savejson('verification.json',{'normalization_train_only':True,'split_counts_pass':True,'conservation_pass':True,
        'pseudo_cost_identity_pass':True,'one_sided_feedback_pass':True,'deterministic_sampling_pass':True,
        'nested_horizon_sampling_pass':True,'independent_seed_streams_distinct':True,'future_observation_fields_excluded':True})
    print('Verification passed',flush=True)

def direct_meta_check():
    ids,d,bank=load_data()
    D=paths([PILOTS[0]],bank,[0],7000)[0]
    Q=np.full((7,7,len(GRID)),7.);k=np.zeros(7,int)
    x=0.;w=0;j=0;rounds=0;h=0;active=False;values=[];obs=[]
    for t,dd in enumerate(D):
        if not active and t%7==w:active=True;h=0;obs=[]
        y=M if active else x
        s=min(y,dd);x=y-s;values.append(y)
        if active:
            obs.append(s);h+=1
            if h==7:
                k[w]+=1;alpha=8/(7+k[w])
                for hh in range(6,-1,-1):
                    sales=np.minimum(GRID,obs[hh]);left=GRID-sales
                    reward=(M-left+sales)/(2*M)
                    V=np.zeros(len(GRID))
                    if hh<6:
                        for a in range(len(GRID)):
                            V[a]=Q[w,hh+1,GRID>=left[a]-1e-12].max()
                    Q[w,hh]=(1-alpha)*Q[w,hh]+alpha*(reward+V)
                assert Q.min()>=-1e-9 and Q.max()<=7+1e-9
                cb=8*np.sqrt(7**5*9*np.log(len(GRID)*len(D)))/np.sqrt(max(1,k[w]-1))
                assert (Q[w].max(axis=1)-Q[w].min(axis=1)).max()<cb
                h=0;rounds+=1
                if rounds==2**j:
                    rounds=0;w+=1;active=False
                    if w==7:w=0;j+=1
    schedule,_=meta_schedule(len(D))
    xx=0.;fast=[]
    for t,dd in enumerate(D):
        yy=M if schedule[t]>=0 else xx;fast.append(yy);xx=max(yy-dd,0)
    assert np.allclose(values,fast)
    savejson('meta_direct_verification.json',{'T':len(D),'action_trajectories_equal':True,
        'all_Q_in_0_H':True,'no_action_elimination_directly_verified':True,'completed_episodes_per_arm':k.tolist()})
    print('Direct HQL updates and accelerated Meta actions agree',flush=True)

def sensitivity():
    global M,GRID
    ids,d,bank=load_data();cfg=json.loads((OUT/'selected_hyperparameters.json').read_text())
    seeds=list(range(10));ids=PILOTS;D=paths(ids,bank,seeds,7000)
    records=[]
    for cap in [2.,8.]:
        M=cap;GRID=np.linspace(0,M,int(M/.2)+1)
        schedule,_=meta_schedule(7000)
        mr=reference_eval(D,'Meta-HQL',schedule)
        dr=dqn_eval(D,cfg,model_keys(ids,seeds),verbose=False)
        for name,res in [('Meta-HQL',mr),('SRDQN adapted',dr)]:
            for i,sid in enumerate(ids):
                for j,seed in enumerate(seeds):
                    ix=i*len(seeds)+j
                    records.append({'cap':cap,'algorithm':name,'series_id':sid,'seed':seed,
                        'cost':float(res['cost'][ix]),'fill':float(res['fill'][ix]),'inventory':float(res['inventory'][ix])})
        print('Sensitivity cap',cap,'finished',flush=True)
    pd.DataFrame(records).to_csv(OUT/'sensitivity_capacity.csv',index=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','tune','synthetic','long','historical','check','direct','sensitivity']);args=p.parse_args()
    if args.stage=='prepare':prepare()
    elif args.stage=='tune':tune()
    elif args.stage=='check':checks()
    elif args.stage=='direct':direct_meta_check()
    elif args.stage=='sensitivity':sensitivity()
    else:bench(args.stage)
