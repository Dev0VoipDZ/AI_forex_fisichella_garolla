"""Volume confirmation + ATR period variants on H1 Donchian N200 SL1.5 tr5."""
from research import *
m15v = pd.read_csv(D, parse_dates=["Date"]).rename(columns={"Date": "time"}).set_index("time")
h = resample("1h"); h["vol"] = m15v.tick_volume.resample("1h", label="left", closed="left").sum().reindex(h.index)
c = h.close; rows = []
hh = h.high.rolling(200).max().shift(1); ll = h.low.rolling(200).min().shift(1)
raw = np.where(c > hh, 1, np.where(c < ll, -1, 0)); prev = np.r_[0, raw[:-1]]; fresh = np.where(raw != prev, raw, 0)
# A. ATR period for stop/trail
for ap in [7, 10, 14, 20, 30, 50]:
    h["atr"] = atr(h, ap); sig = np.r_[0, fresh[:-1]]
    for k, tr in [(1.5, 5), (1.5, 4), (1.25, 4)]:
        sld = np.r_[np.nan, (k * h.atr).values[:-1]]
        rows.append(report(f"ATR{ap} SL{k} tr{tr}", simulate(h, sig, sld, trail=tr)))
h["atr"] = atr(h, 14); sld = np.r_[np.nan, (1.5 * h.atr).values[:-1]]
# B. volume confirmation: breakout bar volume vs rolling mean of 50 / 200 bars
for w in [50, 200]:
    vr = (h.vol / h.vol.rolling(w).mean().shift(1)).values
    for thr in [0.8, 1.0, 1.2, 1.5, 2.0]:
        s = np.where(vr >= thr, fresh, 0); sig = np.r_[0, s[:-1]]
        rows.append(report(f"vol>={thr}x mean{w} SL1.5 tr5", simulate(h, sig, sld, trail=5)))
    for thr in [1.0, 1.5]:   # inverse: LOW volume breakouts
        s = np.where(vr < thr, fresh, 0); sig = np.r_[0, s[:-1]]
        rows.append(report(f"vol<{thr}x mean{w} SL1.5 tr5", simulate(h, sig, sld, trail=5)))
# C. relative volume as size multiplier instead of filter (report per-quintile R)
sig = np.r_[0, fresh[:-1]]; base = simulate(h, sig, sld, trail=5)
t = pd.DataFrame(base, columns=["t", "R"]).set_index("t"); vr = pd.Series((h.vol / h.vol.rolling(200).mean().shift(1)).values, index=h.index)
t["vr"] = vr.shift(1).reindex(t.index); t["q"] = pd.qcut(t.vr, 4, labels=False); t["per"] = np.where(t.index < SPLIT, "IS", "OOS")
print("R by relative-volume quartile of the signal bar:"); print(t.pivot_table(index="per", columns="q", values="R", aggfunc=["mean", "size"]).round(2).to_string())
show(rows, 40)
