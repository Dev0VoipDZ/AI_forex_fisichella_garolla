"""Portfolio: monthly return streams of candidate strategies, correlation, combined Sharpe/DD at 2% risk."""
from research import *
import pickle
h = resample("1h"); h["atr"] = atr(h); c = h.close
streams = {}
# Donchian H1 N200
hh = h.high.rolling(200).max().shift(1); ll = h.low.rolling(200).min().shift(1)
raw = np.where(c > hh, 1, np.where(c < ll, -1, 0)); prev = np.r_[0, raw[:-1]]; fresh = np.where(raw != prev, raw, 0)
streams["Donch H1 N200"] = simulate(h, np.r_[0, fresh[:-1]], np.r_[np.nan, (2*h.atr).values[:-1]], trail=4)
# Donchian H4 N100 tr3
h4 = resample("4h"); h4["atr"] = atr(h4); c4 = h4.close
hh = h4.high.rolling(100).max().shift(1); ll = h4.low.rolling(100).min().shift(1)
raw = np.where(c4 > hh, 1, np.where(c4 < ll, -1, 0)); prev = np.r_[0, raw[:-1]]; fresh = np.where(raw != prev, raw, 0)
streams["Donch H4 N100"] = simulate(h4, np.r_[0, fresh[:-1]], np.r_[np.nan, (2*h4.atr).values[:-1]], trail=3)
# D1 Donch N20
d = resample("1D"); d["atr"] = atr(d, 20); cd = d.close
hh = d.high.rolling(20).max().shift(1); ll = d.low.rolling(20).min().shift(1)
raw = np.where(cd > hh, 1, np.where(cd < ll, -1, 0)); prev = np.r_[0, raw[:-1]]; fresh = np.where(raw != prev, raw, 0)
streams["Donch D1 N20"] = simulate(d, np.r_[0, fresh[:-1]], np.r_[np.nan, (1.5*d.atr).values[:-1]], trail=2)
# D1 vol breakout tp2
rng = (d.high - d.low).shift(1); up = cd > d.open + 0.5*rng; dn = cd < d.open - 0.5*rng
raw = np.where(up, 1, np.where(dn, -1, 0)); streams["D1 VolBrk"] = simulate(d, np.r_[0, raw[:-1]], np.r_[np.nan, (1.5*d.atr).values[:-1]], tp_r=2)
# RSI2 mean reversion H4 (counter-trend flavour)
e200 = ema(c4, 200); e5 = ema(c4, 5); r2 = rsi(c4, 2)
raw = np.where((c4 > e200) & (r2 < 10), 1, np.where((c4 < e200) & (r2 > 90), -1, 0))
ex = np.where(c4 > e5, -1, np.where(c4 < e5, 1, 0))
streams["RSI2 H4"] = simulate(h4, np.r_[0, raw[:-1]], np.r_[np.nan, (3*h4.atr).values[:-1]], max_bars=10, exit_sig=ex)
pickle.dump(streams, open("portfolio_streams.pkl", "wb"))

def monthly(tr, f=0.02):
    t = pd.DataFrame(tr, columns=["t", "R"]).set_index("t")
    return (f * t.R).groupby(t.index.to_period("M")).sum()
M = pd.DataFrame({k: monthly(v) for k, v in streams.items()}).fillna(0)
print("monthly return correlation (2% risk):"); print(M.corr().round(2).to_string())
def perf(m):
    eq = (1 + m).cumprod(); dd = (eq / eq.cummax() - 1).min()
    return f"x{eq.iloc[-1]:6.2f}  Sharpe {m.mean()/m.std()*np.sqrt(12):5.2f}  maxDD {dd*100:6.1f}%"
print("\nsingle:"); [print(f"  {k:16s}", perf(M[k])) for k in M]
print("\ncombos (each at 2%, OOS 2019+ in brackets):")
import itertools
for r in [2, 3]:
    for combo in itertools.combinations(M.columns, r):
        m = M[list(combo)].sum(axis=1); o = m[m.index >= "2019-01"]
        print(f"  {'+'.join(combo):52s}", perf(m), "| OOS", perf(o))
