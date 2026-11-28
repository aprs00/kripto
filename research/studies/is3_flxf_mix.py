import json, numpy as np
from research.studies import is3_flxf as X
from kripto.strategies import REGISTRY
p=X.p; S=X.S
wb=REGISTRY["blend"](p, components={"carry_trend": {}, "carry": {}, "xsmom": {}}).ffill().fillna(0.0).reindex(columns=X.cols, fill_value=0.0)
out={}
for k,mode in (("flow",None),("resid_f7","resid_f7")):
    wf=X.flow_x(p, mode=mode).ffill().fillna(0.0).reindex(columns=X.cols, fill_value=0.0)
    r=X.run((wf+wb)*0.5).returns.loc[S]
    out[k]={"sr":round(float(r.mean()/r.std()*np.sqrt(365)),2),"by_year":{int(y):round(float(v.mean()/v.std()*np.sqrt(365)),2) for y,v in r.groupby(r.index.year)}}
r=X.run(wb).returns.loc[S]; out["blend_alone"]={"sr":round(float(r.mean()/r.std()*np.sqrt(365)),2),"by_year":{int(y):round(float(v.mean()/v.std()*np.sqrt(365)),2) for y,v in r.groupby(r.index.year)}}
print(json.dumps(out)); json.dump(out,open("research/is3/flxf_mix.json","w"),indent=1)
