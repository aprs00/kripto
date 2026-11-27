import numpy as np, pandas as pd, json
from research.studies import t5b_positioning as T
from kripto import data
start,end=T.EXPLORE
p=data.load_bn_all_panel(); close=p['close']
dv=p['volume'].rolling(30,min_periods=7).mean(); member=(dv.rank(axis=1,ascending=False)<=60)
lo,hi=pd.Timestamp(start,tz='UTC'),pd.Timestamp(end,tz='UTC')
syms=[c+'USDT' for c in member.columns[member.loc[lo:hi].any()]]
m=T.daily_metrics(syms,start,end)
coins=[c for c in m['oi'].columns if c in close.columns]
ret3=(close/close.shift(3)-1).reindex(columns=coins); fwd1=close.pct_change(fill_method=None).shift(-1)
doi=np.log(m['oi'].reindex(columns=coins)).diff(3); r3=ret3.reindex(index=doi.index)
idx=doi.index[(doi.index>=lo)&(doi.index<=hi)]
V={'F3':doi*-np.sign(r3),'rev_sign':-np.sign(r3)+0*doi,'absdoi_x_rev':doi.abs()*-np.sign(r3),'doi':doi,'rev3':-r3,
   'doi_in_losers':doi.where(r3<0),'doi_in_winners':doi.where(r3>0)}
for k,f in V.items():
    f=f.loc[f.index.isin(idx)]
    print(k, T.stats(T.ic_series(f,fwd1,member,None,1)))
# quintile spread of F3, gross next-day, and daily turnover of a top/bottom quintile book
f=V['F3'].loc[idx]; sp=[]; prevL=prevS=set(); to=[]
for d in idx:
    mm=member.loc[d]; x=f.loc[d].reindex(mm[mm].index).dropna(); y=fwd1.loc[d].reindex(x.index)
    ok=y.notna(); x,y=x[ok],y[ok]
    if len(x)<20: continue
    q=x.rank(pct=True); L=set(x[q>0.8].index); S=set(x[q<=0.2].index)
    sp.append(y[list(L)].mean()-y[list(S)].mean())
    if prevL: to.append(1-len(L&prevL)/max(len(L),1))
    prevL,prevS=L,S
sp=pd.Series(sp); print('Q5-Q1 gross bp/day mean %.1f median %.1f t %.2f; leg turnover/day %.2f'%(sp.mean()*1e4, sp.median()*1e4, sp.mean()/sp.std()*np.sqrt(len(sp)), np.mean(to)))
# winners only: next-day return by tercile of 3-day OI change (simple mean, median, and trimmed), explore only
rows=[]
for d in idx:
    mm=member.loc[d]; nm=mm[mm].index
    w=r3.loc[d].reindex(nm); x=doi.loc[d].reindex(nm); y=fwd1.loc[d].reindex(nm)
    ok=(w>0)&x.notna()&y.notna()&np.isfinite(x)
    if ok.sum()<9: continue
    t=x[ok].rank(pct=True)
    for c in t.index: rows.append((d,c,int(min(2,t[c]*3)),y[c]))
R=pd.DataFrame(rows,columns=['d','c','terc','y'])
g=R.groupby('terc')['y']; print('winners by OI-change tercile: mean bp',(g.mean()*1e4).round(1).to_dict(),'median bp',(g.median()*1e4).round(1).to_dict(),'n',g.size().to_dict())
dd=R.groupby(['d','terc'])['y'].mean().unstack(); s=(dd[2]-dd[0]).dropna(); print('top-minus-bottom tercile within winners, per day: mean %.1f bp t %.2f, median %.1f'%(s.mean()*1e4, s.mean()/s.std()*np.sqrt(len(s)), s.median()*1e4))
