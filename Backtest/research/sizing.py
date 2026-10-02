import pickle, numpy as np, pandas as pd
st = pickle.load(open("streams.pkl","rb"))
t = pd.DataFrame(st["Donch 1h N200 SL2 tr4"], columns=["t","R"])
R = t.R.values; yrs = (t.t.iloc[-1]-t.t.iloc[0]).days/365.25
print(f"trades={len(R)} over {yrs:.1f}y ({len(R)/yrs:.0f}/yr) meanR={R.mean():.3f} win%={(R>0).mean()*100:.0f} maxR={R.max():.1f}")
# longest losing streak
ls=m=0
for r in R: m = m+1 if r<0 else 0; ls=max(ls,m)
print("longest losing streak:", ls)
rng = np.random.default_rng(0)
print("risk | hist final x | hist maxDD | MC: P(reach 16.7x) | median months to 16.7x | P(DD>50%) | P(DD>80%)")
for f in [0.01,0.02,0.03,0.05,0.08,0.10,0.15]:
    eq = np.cumprod(1+f*R); dd=(eq/np.maximum.accumulate(eq)-1).min()
    hits=[]; d50=d80=0; months=[]
    for _ in range(2000):
        s = rng.choice(R, size=len(R), replace=True)
        e = np.cumprod(1+f*np.maximum(s,-1/f+1e-9))
        ddm=(e/np.maximum.accumulate(e)-1).min()
        d50 += ddm<-0.5; d80 += ddm<-0.8
        k = np.argmax(e>=16.67) if (e>=16.67).any() else None
        if k is not None: months.append(k/len(R)*yrs*12)
    print(f"{f*100:4.0f}% | {eq[-1]:10.1f} | {dd*100:6.1f}% | {len(months)/2000*100:5.1f}% | {np.median(months) if months else float('nan'):6.0f} | {d50/20:5.1f}% | {d80/20:5.1f}%")
t['y']=t.t.dt.year; print(t.groupby('y').R.agg(['size','sum']).round(1).T)
