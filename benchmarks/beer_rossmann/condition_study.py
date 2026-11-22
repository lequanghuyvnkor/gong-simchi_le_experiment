"""Predeclared condition benchmark. Versions are adaptations, not author replication code."""
from pathlib import Path
import numpy as np,pandas as pd,json,hashlib,time,argparse,sys,copy
import os
ROOT=Path(os.environ.get('GONG_RUN_DIR', str(Path(__file__).resolve().parents[2]/'local_checks/beer_rossmann'))).resolve()
sys.path.insert(0,str(Path(__file__).resolve().parent))
from research_run import BatchedRNG
OUT=ROOT/'outputs/condition_study'
OUT.mkdir(parents=True,exist_ok=True)
GRID=np.linspace(0,4,21);M=4.;H=7

def js(name,v):
    (OUT/name).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def key(s):return int.from_bytes(hashlib.sha256(str(s).encode()).digest()[:4],'little')
def scenarios():
    return [dict(case=f'a{a:.1f}_v{v:.2f}_p{p}',a=a,cv=v,p=p)
        for a in [0.,.4,.8] for v in [.25,.75] for p in [1,5,10]]
def shape(profile,validation=False):
    h=np.arange(7)
    if validation:return np.sin(2*np.pi*h/7+.37)
    if profile==0:s=np.sin(2*np.pi*h/7)
    elif profile==1:s=np.cos(2*np.pi*h/7)
    elif profile==2:s=np.sin(4*np.pi*h/7)
    else:s=np.array([-1.,-.8,-.3,0,.4,.8,.9])
    s=s-s.mean()
    return s/np.max(abs(s))
def records(cases,profiles,seeds):
    return [{**c,'profile':pr,'seed':sd} for c in cases for pr in profiles for sd in seeds]
def demands(recs,T,split,validation=False):
    out=np.empty((len(recs),T),np.float32)
    for i,r in enumerate(recs):
        mu=1+r['a']*shape(r['profile'],validation)
        # p intentionally excluded so paired penalty experiments share demand.
        for h in range(7):
            rng=np.random.default_rng(np.random.SeedSequence([20261110,key((r['a'],r['cv'])),r['profile'],r['seed'],split,h]))
            idx=np.arange(h,T,7)
            out[i,idx]=mu[h]*rng.gamma(1/r['cv']**2,r['cv']**2,len(idx))
    return out
def identity(recs):
    return [key((r['case'],r['profile'],r['seed'])) for r in recs]

class DQN:
    def __init__(self,N,cfg,keys):
        self.N=N;self.cfg=cfg;self.hist=np.zeros((N,3,3),np.float32)
        self.rng=BatchedRNG(keys);width=cfg['width'];A=len(GRID)
        self.W=[];self.b=[]
        for layer,(a,b) in enumerate([(17,width),(width,width),(width,A)]):
            w=np.empty((N,a,b),np.float32)
            for i,k in enumerate(keys):
                rg=np.random.default_rng(np.random.SeedSequence([int(k),layer,541]))
                w[i]=rg.normal(0,np.sqrt(2/a),size=(a,b)) if layer<2 else 0.
            self.W.append(w);self.b.append(np.zeros((N,1,b),np.float32))
        self.tw=[w.copy() for w in self.W];self.tb=[b.copy() for b in self.b]
        self.mw=[np.zeros_like(w) for w in self.W];self.vw=[np.zeros_like(w) for w in self.W]
        self.mb=[np.zeros_like(b) for b in self.b];self.vb=[np.zeros_like(b) for b in self.b]
        self.K=cfg['buffer'];self.S=np.zeros((N,self.K,17),np.float32);self.S2=np.zeros_like(self.S)
        self.A=np.zeros((N,self.K),np.int16);self.R=np.zeros((N,self.K),np.float32)
        self.count=0;self.updates=0;self.td=[];self.maxq=0.
    def obs(self,x,phase):
        ph=np.zeros((self.N,7),np.float32);ph[np.arange(self.N),phase]=1
        return np.concatenate([x[:,None]/M,self.hist.reshape(self.N,9)/M,ph],axis=1).astype(np.float32)
    def forward(self,s,target=False):
        W,b=(self.tw,self.tb) if target else (self.W,self.b)
        h1=np.maximum(np.einsum('nbi,nij->nbj',s,W[0])+b[0],0)
        h2=np.maximum(np.einsum('nbi,nij->nbj',h1,W[1])+b[1],0)
        q=np.einsum('nbi,nij->nbj',h2,W[2])+b[2]
        return h1,h2,q
    def choose(self,x,phase,t,greedy=False):
        s=self.obs(x,phase);q=self.forward(s[:,None])[2][:,0]
        self.last_s=s;self.last_a=q.argmax(axis=1)
        if not greedy:
            eps=max(.03,1-.97*t/self.cfg['decay'])
            mask=self.rng.uniform()<eps;ra=self.rng.integers(len(GRID))
            self.last_a[mask]=ra[mask]
        return GRID[self.last_a]
    def transition(self,xnext,sales,ordered,nextphase,p,train=True):
        self.hist[:,:-1]=self.hist[:,1:]
        self.hist[:,-1]=np.stack([sales,xnext,ordered],axis=1)
        if not train:return
        s2=self.obs(xnext,nextphase)
        # Centered pseudo-reward: affine-equivalent to Gong's [0,1] reward.
        r=(p*sales-xnext)/((1+p)*M)
        k=self.count%self.K;self.S[:,k]=self.last_s;self.S2[:,k]=s2
        self.A[:,k]=self.last_a;self.R[:,k]=r
        self.count+=1
        if self.count<64 or self.count%self.cfg['freq']:return
        ix=self.rng.integers(min(self.count,self.K),b=16);nn=np.arange(self.N)[:,None]
        s=self.S[nn,ix];s2=self.S2[nn,ix];a=self.A[nn,ix];r=self.R[nn,ix]
        h1,h2,q=self.forward(s)
        target=r+self.cfg['gamma']*self.forward(s2,target=True)[2].max(axis=2)
        err=np.take_along_axis(q,a[:,:,None],axis=2)[:,:,0]-target
        delta=np.clip(err,-1,1)/16
        dq=np.zeros_like(q);np.put_along_axis(dq,a[:,:,None],delta[:,:,None],axis=2)
        gw=[None]*3;gb=[None]*3
        gw[2]=np.einsum('nbi,nbj->nij',h2,dq);gb[2]=dq.sum(1,keepdims=True)
        dh2=np.einsum('nbj,nij->nbi',dq,self.W[2])*(h2>0)
        gw[1]=np.einsum('nbi,nbj->nij',h1,dh2);gb[1]=dh2.sum(1,keepdims=True)
        dh1=np.einsum('nbj,nij->nbi',dh2,self.W[1])*(h1>0)
        gw[0]=np.einsum('nbi,nbj->nij',s,dh1);gb[0]=dh1.sum(1,keepdims=True)
        self.updates+=1;tt=self.updates
        for i in range(3):
            for par,g,m,v in [(self.W[i],gw[i],self.mw[i],self.vw[i]),(self.b[i],gb[i],self.mb[i],self.vb[i])]:
                np.clip(g,-5,5,out=g);m*=.9;m+=.1*g;v*=.999;v+=.001*g*g
                par-=self.cfg['lr']*(m/(1-.9**tt))/(np.sqrt(v/(1-.999**tt))+1e-8)
        if tt%self.cfg['target']==0:
            self.tw=[w.copy() for w in self.W];self.tb=[b.copy() for b in self.b]
        if tt%50==0:
            self.td.append(float(abs(err).mean()));self.maxq=max(self.maxq,float(abs(q).max()))
        assert np.isfinite(self.W[-1]).all()

class Meta:
    def __init__(self,N,cfg,T,H_=7):
        self.N=N;self.cfg=cfg;self.T=T;self.H=H_;A=len(GRID)
        self.Q=np.full((N,H_,H_,A),float(H_));self.alive=np.ones_like(self.Q,dtype=bool)
        self.valid=np.ones((N,H_),bool);self.k=np.zeros((N,H_),int)
        self.w=np.zeros(N,int);self.j=np.zeros(N,int);self.rounds=np.zeros(N,int)
        self.visited=np.zeros((N,H_),bool);self.active=np.zeros(N,bool);self.h=np.zeros(N,int)
        self.sales=np.zeros((N,H_));self.stocks=np.zeros((N,H_));self.guards=np.zeros(N,int)
        self.discarded=np.zeros(N,int);self.eliminated=np.zeros(N,int);self.feedback_violations=0
    def tops(self,n,w,h):
        a=self.alive[n,w,h]
        return np.max(np.where(a,GRID,-np.inf),axis=-1)
    def choose(self,x,phase,t):
        n=np.arange(self.N);tops=self.tops(n,self.w,np.zeros(self.N,int))
        start=(~self.active)&(phase==self.w)&(x<=tops+1e-9)
        self.active[start]=True;self.h[start]=0
        lev=self.tops(n,self.w,self.h)
        return np.where(self.active,lev,x)
    def learn(self,sales,stock,p):
        act=np.flatnonzero(self.active)
        self.sales[act,self.h[act]]=sales[act];self.stocks[act,self.h[act]]=stock[act]
        self.h[act]+=1;end=act[self.h[act]==self.H]
        if not len(end):return
        w=self.w[end];self.k[end,w]+=1
        k=self.k[end,w];alpha=(self.H+1)/(self.H+k)
        old=self.alive[end,w].copy()
        # Backward delayed Bellman updates using only own censored sales.
        for hh in range(self.H-1,-1,-1):
            eligible=old[:,hh]
            z=np.broadcast_to(GRID,(len(end),len(GRID))).copy();ret=np.zeros_like(z)
            pending=eligible.copy()
            for ss in range(hh,self.H):
                illegal=pending&(z>self.stocks[end,ss,None]+1e-7)
                self.feedback_violations+=int(illegal.sum())
                assert not illegal.any(), 'Counterfactual needs unavailable feedback'
                sale=np.minimum(z,self.sales[end,ss,None]);left=z-sale
                reward=(M-left+p[end,None]*sale)/((1+p[end,None])*M)
                ret+=np.where(pending,reward,0.);z=left
                if ss==self.H-1:break
                nxt=self.alive[end,w,ss+1]
                top=np.max(np.where(nxt,GRID,-np.inf),axis=1)
                stop=pending&(z<=top[:,None]+1e-9)
                qnext=np.where(nxt,self.Q[end,w,ss+1],-np.inf)
                suffix=np.maximum.accumulate(qnext[:,::-1],axis=1)[:,::-1]
                ix=np.searchsorted(GRID,z-1e-9,side='left').clip(0,len(GRID)-1)
                V=np.take_along_axis(suffix,ix,axis=1)
                assert np.isfinite(V[stop]).all()
                ret+=np.where(stop,V,0.);pending[stop]=False
                if not pending.any():break
            qold=self.Q[end,w,hh]
            self.Q[end,w,hh]=np.where(eligible,(1-alpha[:,None])*qold+alpha[:,None]*ret,qold)
        assert self.Q[end,w].min()>-1e-7 and self.Q[end,w].max()<=self.H+1e-7
        cb=self.cfg['action_scale']*8*np.sqrt(self.H**5*9*np.log(len(GRID)*self.T))/np.sqrt(np.maximum(1,k-1))
        cb[k==1]=np.inf
        q=self.Q[end,w];best=np.max(np.where(old,q,-np.inf),axis=2)
        proposed=old&((best[:,:,None]-q)<=cb[:,None,None])
        top0=np.max(np.where(proposed[:,0],GRID,-np.inf),axis=1)
        proposed &= GRID[None,None,:]<=top0[:,None,None]+1e-9
        bad=~proposed.any(axis=2).all(axis=1)
        last=self.valid[end].sum(axis=1)==1
        guard=bad&last
        # Explicit practical safeguard: retain previous sets for the final arm.
        proposed[guard]=old[guard];self.guards[end[guard]]+=1
        drop=bad&~last
        self.valid[end[drop],w[drop]]=False;self.discarded[end[drop]]+=1
        proposed[drop]=old[drop]  # discarded copies are never selected again
        self.eliminated[end]+=np.sum(old&~proposed,axis=(1,2))
        self.alive[end,w]=proposed
        self.h[end]=0;self.rounds[end]+=1
        block=(self.rounds[end]>=2.**self.j[end])|drop
        done=end[block]
        if not len(done):return
        self.rounds[done]=0;self.active[done]=False
        self.visited[done,self.w[done]]=True
        remaining=self.valid[done]&~self.visited[done]
        phase_end=~remaining.any(axis=1)
        rows=done[phase_end]
        if len(rows):
            val=np.max(np.where(self.alive[rows,:,0,:],self.Q[rows,:,0,:],-np.inf),axis=2)
            best=np.max(np.where(self.valid[rows],val,-np.inf),axis=1)
            bound=self.cfg['bandit_scale']*4*np.sqrt(self.H**7*np.log(self.T))/np.sqrt(np.maximum(1,self.k[rows]))
            kill=self.valid[rows]&((best[:,None]-val)>bound)
            self.valid[rows]&=~kill
            assert self.valid[rows].any(axis=1).all()
            self.j[rows]+=1;self.visited[rows]=False
        remaining=self.valid[done]&~self.visited[done]
        self.w[done]=remaining.argmax(axis=1)
    def policy(self):
        val=np.max(np.where(self.alive[:,:,0],self.Q[:,:,0],-np.inf),axis=2)
        w=np.where(self.valid,val,-np.inf).argmax(axis=1)
        policies=np.zeros((self.N,self.H))
        for phase in range(self.H):
            hh=(phase-w)%self.H
            a=np.where(self.alive[np.arange(self.N),w,hh],self.Q[np.arange(self.N),w,hh],-np.inf).argmax(axis=1)
            policies[:,phase]=GRID[a]
        return policies

def evaluate(D,p,model=None,policy=None,H_=7,startphase=0):
    N,T=D.shape;x=np.zeros(N);cost=np.zeros(N);lost=np.zeros(N);inv=np.zeros(N)
    if model is not None:
        oldhist=model.hist;model.hist=np.zeros_like(oldhist)
    for t in range(T):
        phase=(startphase+t)%H_
        ix=np.broadcast_to(phase,(N,)).astype(int)
        B=model.choose(x,phase,0,True) if model is not None else policy[np.arange(N),ix]
        y=np.maximum(x,B);q=y-x;s=np.minimum(y,D[:,t]);x=y-s
        if model is not None:model.transition(x,s,q,(phase+1)%H_,p,False)
        loss=D[:,t]-s;cost+=x+p*loss;lost+=loss;inv+=x
    if model is not None:model.hist=oldhist
    return {'cost':cost/T,'fill':1-lost/D.sum(1),'inventory':inv/T}

def train(D,E,p,kind,cfg,keys,checkpoints,H_=7,log=True,eval_phase=0):
    N,T=D.shape;x=np.zeros(N);cost=np.zeros(N);lost=np.zeros(N);inv=np.zeros(N);start=time.time();out={}
    agent=DQN(N,cfg,keys) if kind=='SRDQN-A' else Meta(N,cfg,T,H_)
    for t in range(T):
        phase=t%H_;B=agent.choose(x,phase,t)
        y=np.maximum(x,B);q=y-x;s=np.minimum(y,D[:,t]);x=y-s
        if kind=='SRDQN-A':agent.transition(x,s,q,(phase+1)%H_,p,True)
        else:agent.learn(s,y,p)
        loss=D[:,t]-s;cost+=x+p*loss;lost+=loss;inv+=x
        if t+1 in checkpoints:
            frozen=evaluate(E,p,model=agent,H_=H_,startphase=eval_phase) if kind=='SRDQN-A' else evaluate(E,p,policy=agent.policy(),H_=H_,startphase=eval_phase)
            out[t+1]={'online_cost':cost.copy()/(t+1),'online_fill':1-lost/D[:,:t+1].sum(1),
                **{'frozen_'+k:v for k,v in frozen.items()}}
        if log and (t+1)%3500==0:print(kind,t+1,'/',T,'N',N,'sec',round(time.time()-start,1),flush=True)
    diagnostics=({'updates':agent.updates,'max_abs_Q':agent.maxq,'last_TD':agent.td[-1] if agent.td else None}
        if kind=='SRDQN-A' else {'guards_total':int(agent.guards.sum()),'eliminated_actions':int(agent.eliminated.sum()),
        'feedback_violations':agent.feedback_violations,'valid_arms_mean':float(agent.valid.sum(1).mean())})
    return out,diagnostics

def predeclare():
    configs_d=[]
    rg=np.random.default_rng(331)
    combos=[dict(lr=lr,gamma=gamma,width=width,target=tar,decay=decay,buffer=1024,freq=4)
        for lr in [.0005,.001,.002] for gamma in [.9,.97,.99] for width in [12,24] for tar in [25,75] for decay in [500,1500]]
    ix=rg.choice(len(combos),20,replace=False)
    configs_d=[combos[i] for i in ix]
    configs_m=[dict(action_scale=a,bandit_scale=b) for a in [3e-5,1e-4,3e-4,.001,.003] for b in [1e-5,3e-5,1e-4,3e-4]]
    plan={'date':'2026-11-10','cases':scenarios(),'profiles':[0,1,2,3],'seeds':list(range(1000,1030)),
        'train_T':21000,'checkpoints':[7000,21000],'frozen_eval_T':1400,
        'long_cases':[c['case'] for c in scenarios() if c['a'] in [0.,.8] and c['cv']==.75],
        'long_profiles':[0],'long_seeds':list(range(3000,3030)),'long_T':70000,
        'DQN_configs':configs_d,'Meta_configs':configs_m,
        'costs':{'holding':1,'penalty':[1,5,10]},'H':7,'M':4,'step':.2,
        'primary':'Frozen policy after 21000 interactions; paired relative cost difference; 18 cells.',
        'decision_threshold_percent':5,'familywise_alpha':.05,'bootstrap':20000,
        'meta_practical_changes':['Scaled confidence bounds','Discard copies with empty trimmed action sets',
            'Retain previous sets if trimming would empty final remaining copy; count every safeguard activation',
            'Frozen deployment chooses copy maximizing estimated V1, then argmax-Q base stocks by phase'],
        'DQN_changes':['Centered observable pseudo-reward','Zero-initialized output layer','Validation-selected network and update settings'],
        'data_source_checks':'Beer held-out 2016-2017; new Rossmann stores 1-10 evaluation 2015; fit 2013 only.'}
    text=json.dumps(plan,ensure_ascii=False,indent=2)
    p=OUT/'preregistered_design.json'
    if p.exists():assert p.read_text(encoding='utf-8')==text,'Do not overwrite a changed preregistration'
    else:p.write_text(text,encoding='utf-8')
    print('Design SHA256',hashlib.sha256(text.encode()).hexdigest(),flush=True)

def tune(kind):
    plan=json.loads((OUT/'preregistered_design.json').read_text())
    rec=records(scenarios(),[10],[100,101,102])
    D=demands(rec,3500,1001,True);E=demands(rec,700,1002,True);p=np.array([r['p'] for r in rec])
    configs=plan['DQN_configs'] if kind=='SRDQN-A' else plan['Meta_configs']
    rows=[]
    # Equal case weights, normalized by a fixed privileged constant-stock reference.
    prior=demands(rec,3500,1003,True)
    loss=np.mean(np.maximum(GRID[None,None,:]-prior[:,:,None],0)+p[:,None,None]*np.maximum(prior[:,:,None]-GRID[None,None,:],0),axis=1)
    denominator=loss.min(axis=1)
    for i,cfg in enumerate(configs):
        print('Tune',kind,i,cfg,flush=True)
        ans,diag=train(D,E,p,kind,cfg,identity(rec),[3500],log=False)
        row={'index':i,'score':float(np.mean(ans[3500]['frozen_cost']/denominator)),
            'frozen_cost':float(ans[3500]['frozen_cost'].mean()),'diagnostics':diag,'config':cfg}
        rows.append(row);js('tuning_'+kind+'.json',rows)
        print('score',row['score'],'diagnostics',diag,flush=True)
    best=min(rows,key=lambda a:a['score'])
    js('selected_'+kind+'.json',best)
    print('SELECTED',kind,best,flush=True)

def run_block(recs,D,E,label,checkpoints,eval_phase=0,baseline_policy=None):
    p=np.array([r['p'] for r in recs],float);rows=[];diags={}
    variants=['SRDQN-A','Meta-HQL-P','Meta-HQL-T']
    for kind in variants:
        if kind=='SRDQN-A':cfg=json.loads((OUT/'selected_SRDQN-A.json').read_text())['config']
        elif kind=='Meta-HQL-P':cfg=json.loads((OUT/'selected_Meta-HQL-P.json').read_text())['config']
        else:cfg=dict(action_scale=1.,bandit_scale=1.)
        ans,diag=train(D,E,p,kind,cfg,identity(recs),checkpoints,eval_phase=eval_phase)
        diags[kind]=diag
        for t,vals in ans.items():
            for i,r in enumerate(recs):rows.append({**r,'algorithm':kind,'checkpoint':t,**{k:float(v[i]) for k,v in vals.items()}})
        pd.DataFrame(rows).to_csv(OUT/f'results_{label}.csv',index=False)
        js('diagnostics_'+label+'.json',diags)
    if baseline_policy is not None:
        for name,pol in baseline_policy.items():
            vals=evaluate(E,p,policy=pol,startphase=eval_phase)
            for t in checkpoints:
                for i,r in enumerate(recs):
                    rows.append({**r,'algorithm':name,'checkpoint':t,
                        **{'frozen_'+k:float(v[i]) for k,v in vals.items()}})
        pd.DataFrame(rows).to_csv(OUT/f'results_{label}.csv',index=False)
    print('FINISHED',label,flush=True)

def run_core(block):
    cs=scenarios()[block*3:(block+1)*3]
    rec=records(cs,[0,1,2,3],list(range(1000,1030)))
    D=demands(rec,21000,2001);E=demands(rec,1400,2002)
    run_block(rec,D,E,'core_'+str(block),[7000,21000],baseline_policy=population_references(rec))
def run_long(block):
    cs=[c for c in scenarios() if c['a'] in [0.,.8] and c['cv']==.75]
    c=cs[block];rec=records([c],[0],list(range(3000,3030)))
    D=demands(rec,70000,3001);E=demands(rec,1400,3002)
    run_block(rec,D,E,'long_'+str(block),[21000,70000],baseline_policy=population_references(rec))

def population_references(rec):
    prior=demands(rec,3500,9999)
    p=np.array([r['p'] for r in rec]);c=np.empty((len(rec),7));w=np.empty_like(c)
    for pp in [1,5,10]:
        mask=p==pp
        if not mask.any():continue
        v=np.quantile(prior[mask],pp/(1+pp),axis=1)
        c[mask]=GRID[np.argmin(abs(v[:,None]-GRID),axis=1)][:,None]
        for h in range(7):
            v=np.quantile(prior[mask,h::7],pp/(1+pp),axis=1)
            w[mask,h]=GRID[np.argmin(abs(v[:,None]-GRID),axis=1)]
    return {'Prior constant':c,'Prior weekday':w}

def sources(dataset):
    seeds=list(range(1000,1030));rec=[];trains=[];tests=[];phases=[];constant=[];weekly=[]
    if dataset=='Beer':
        d=pd.read_csv(ROOT/'outputs/datasets/store_item_demand_train.csv',parse_dates=['date'])
        pairs=[(s,i) for s in range(1,11) for i in [5,34,46]]
        groups=[(f's{s:02d}_i{i:02d}',d[(d.store==s)&(d.item==i)].copy()) for s,i in pairs]
        test_start='2016-01-01';test_end='2017-12-31';expect=731;target='sales'
    else:
        d=pd.read_csv(ROOT/'outputs/datasets/rossmann_train.csv',parse_dates=['Date'],dtype={'StateHoliday':str})
        d=d.rename(columns={'Date':'date','Sales':'sales'})
        groups=[(f's{s:04d}',d[d.Store==s].copy()) for s in range(1,11)]
        test_start='2015-01-01';test_end='2015-07-31';expect=212;target='sales'
    data_audit=[]
    for pr,(sid,g) in enumerate(groups):
        g=g.sort_values('date')
        tt=g[g.date.dt.year==2013].copy();ee=g[g.date.between(test_start,test_end)].copy()
        assert len(tt)==365 and len(ee)==expect
        divisor=20 if dataset=='Rossmann' else 1
        mu=(tt[target]/divisor).mean()
        tt['D']=tt[target]/divisor/mu;ee['D']=ee[target]/divisor/mu
        atoms=[tt[tt.date.dt.dayofweek==h].D.to_numpy() for h in range(7)]
        b0=float(GRID[np.argmin(abs(GRID-np.median(tt.D)))])
        bw=[float(GRID[np.argmin(abs(GRID-np.median(x)))]) for x in atoms]
        for sd in seeds:
            r=dict(case=dataset+'_external',a=np.nan,cv=np.nan,p=1,profile=pr,seed=sd,series_id=sid)
            rec.append(r);v=np.empty(21000,np.float32)
            for h in range(7):
                rng=np.random.default_rng(np.random.SeedSequence([key(sid),sd,20261110,4001,h]))
                ix=np.arange(h,21000,7);v[ix]=rng.choice(atoms[h],len(ix))
            trains.append(v);tests.append(ee.D.to_numpy(dtype=np.float32));phases.append(int(ee.date.dt.dayofweek.iloc[0]))
            constant.append([b0]*7);weekly.append(bw)
        data_audit.append({'series_id':sid,'train_days':365,'test_days':expect,'mean_scale':mu,
            'test_mean_normalized':float(ee.D.mean()),'closed_test_days':int((ee.Open==0).sum()) if dataset=='Rossmann' else 0,
            'test_begin':test_start,'test_end':test_end})
    js('source_audit_'+dataset+'.json',data_audit)
    run_block(rec,np.stack(trains),np.stack(tests),'source_'+dataset,[7000,21000],eval_phase=np.array(phases),
        baseline_policy={'Prior constant':np.array(constant),'Prior weekday':np.array(weekly)})

def gate(selected=False):
    global GRID
    original=GRID.copy();GRID=np.arange(5,dtype=float)
    # Known discrete distributions: exact finite-horizon DP on inventory states 0..4.
    F=np.array([[.05,.15,.3,.5],[.5,.3,.15,.05],[.1,.4,.4,.1],[.4,.4,.15,.05],[.05,.1,.35,.5],[.1,.2,.4,.3],[.2,.4,.3,.1]])
    E_T=350
    V=np.zeros((E_T+1,5));PI=np.zeros((E_T,5),int)
    for t in range(E_T-1,-1,-1):
        for x in range(5):
            vals=[]
            for y in range(x,5):
                nx=np.maximum(y-np.arange(4),0)
                vals.append(np.sum(F[t%7]*(nx+np.maximum(np.arange(4)-y,0)+V[t+1,nx])))
            PI[t,x]=x+int(np.argmin(vals));V[t,x]=min(vals)
    n=12;T=14000 if selected else 7000
    def sample(T,salt):
        a=np.empty((n,T),np.float32)
        for i in range(n):
            for h in range(7):
                rng=np.random.default_rng([i,salt,h]);idx=np.arange(h,T,7)
                a[i,idx]=rng.choice(4,len(idx),p=F[h])
        return a
    D=sample(T,42);E=sample(E_T,54);p=np.ones(n)
    xc=np.zeros(n,int);cost=np.zeros(n)
    for t in range(E_T):
        y=PI[t,xc];s=np.minimum(y,E[:,t]);xc=(y-s).astype(int);cost+=xc+E[:,t]-s
    oracle=cost/E_T
    check={'exact_DP_expected_cost':float(V[0,0]/E_T),'MC_oracle_cost':float(oracle.mean()),'finite_DP':True}
    for kind,cfg in [('SRDQN-A',dict(lr=.001,gamma=.9,width=12,target=25,decay=1000,buffer=1024,freq=4)),
        ('Meta-HQL-P',dict(action_scale=.0003,bandit_scale=.0001))]:
        if selected:cfg=json.loads((OUT/f'selected_{kind}.json').read_text())['config']
        ans,diag=train(D,E,p,kind,cfg,list(range(n)),[7000,T])
        check[kind]={'greedy_cost':float(ans[T]['frozen_cost'].mean()),'online_cost':float(ans[T]['online_cost'].mean()),
            'cost_at_7000':float(ans[7000]['frozen_cost'].mean()),'diagnostics':diag}
    # Exact cost/pseudo-cost identity and one-sided feedback sufficiency.
    for y in np.linspace(0,4,21):
        for dd in [0,.3,1.7,6.2]:
            s=min(y,dd);left=y-s
            for pp in [1,5,10]:
                assert abs((left+pp*(dd-s))-(left-pp*s)-pp*dd)<1e-8
            assert abs(y-s-left)<1e-9
            for z in np.linspace(0,y,7):assert abs(min(z,dd)-min(z,s))<1e-9
    check['environment_identities']=True
    GRID=original
    if selected:
        for kind in ['SRDQN-A','Meta-HQL-P']:
            v=check[kind]
            assert v['greedy_cost']<1.25*check['exact_DP_expected_cost'], 'Gate gap to oracle too large'
            assert v['greedy_cost']<=1.10*v['cost_at_7000'],'Policy degraded on toy gate'
        check['selected_gate_passed']=True
        import datetime
        js('locked_selection.json',{'locked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'files':{k:hashlib.sha256((OUT/f'selected_{k}.json').read_bytes()).hexdigest() for k in ['SRDQN-A','Meta-HQL-P']}})
    js('gate_selected.json' if selected else 'gate_initial.json',check);print(check,flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage');ap.add_argument('--block',type=int,default=0);args=ap.parse_args()
    if args.stage=='design':predeclare()
    elif args.stage=='gate':gate()
    elif args.stage=='gate-selected':gate(True)
    elif args.stage=='tune-dqn':tune('SRDQN-A')
    elif args.stage=='tune-meta':tune('Meta-HQL-P')
    elif args.stage=='core':run_core(args.block)
    elif args.stage=='long':run_long(args.block)
    elif args.stage=='source-beer':sources('Beer')
    elif args.stage=='source-ross':sources('Rossmann')
