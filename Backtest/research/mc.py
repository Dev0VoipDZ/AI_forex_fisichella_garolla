import pandas as pd, numpy as np, sys
O = sys.argv[1]; start = float(sys.argv[2])
t = pd.read_csv(f"{O}/trades.csv", parse_dates=["open"]); e = pd.read_csv(f"{O}/equity.csv", index_col=0, parse_dates=True).iloc[:,0]
bal = start; fr = []
for p in t.pnl: fr.append(p / bal); bal += p
fr = np.array(fr); R = t.R.values
print(f"trades {len(t)}, win {np.mean(R>0)*100:.0f}%, avg R {R.mean():+.3f}, best {R.max():.1f}R, worst {R.min():.2f}R")
ls=m=0
for r in R: m = m+1 if r<0 else 0; ls=max(ls,m)
print(f"longest losing streak {ls} | avg realised loss per losing trade {np.abs(fr[R<0]).mean()*100:.2f}% of equity")
rng = np.random.default_rng(0); dds=[]; fins=[]
for _ in range(5000):
    s = rng.permutation(fr); eq = np.cumprod(1+s); dds.append((eq/np.maximum.accumulate(eq)-1).min()); fins.append(eq[-1])
dds=np.array(dds)
print(f"MC reshuffle (5000): median maxDD {np.median(dds)*100:.0f}%, 95th pct {np.percentile(dds,5)*100:.0f}%, P(DD>50%) {(dds<-0.5).mean()*100:.1f}%, P(DD>70%) {(dds<-0.7).mean()*100:.1f}%")
y=e.resample('YE').last(); prev=pd.concat([pd.Series([start]),y.iloc[:-1]]).values
print("yearly %:", {int(k): int(v) for k, v in zip(y.index.year, ((y.values/prev-1)*100).round(0))})
