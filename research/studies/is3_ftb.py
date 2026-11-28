"""InSilico pass 3, FTB: cached bnall nested pool: standalone net SR by year + daily corr matrix of the pool. Descriptive.
python -m research.studies.is3_ftb data/is3/fc1c_bnall_1d.pkl"""
import json, pickle, sys
import numpy as np, pandas as pd
from kripto import strategies as S

p = pickle.load(open(sys.argv[1], "rb"))
R = {}
for n in S.NESTED_POOL:
    try:
        R[n] = S._component_returns(p, n)[1]
    except KeyError:
        continue
R = pd.DataFrame(R).loc[pd.Timestamp("2021-01-01", tz="UTC"):]
out = {"sr": {}, "corr": {}}
for n in R.columns:
    out["sr"][n] = {str(y): round(float(R[n][R.index.year == y].mean() / R[n][R.index.year == y].std() * np.sqrt(365)), 2) for y in range(2021, 2027)}
    print(f"{n:15s}", out["sr"][n], flush=True)
act = R.where(R != 0)
C = act.corr(min_periods=120).round(2)
out["corr"] = C.to_dict()
print(C.to_string(), flush=True)
json.dump(out, open("research/is3/ftb_a.json", "w"), indent=1)
