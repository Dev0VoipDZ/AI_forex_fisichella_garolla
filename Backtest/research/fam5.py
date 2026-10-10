from research import *
rows = []
# ---- A. Daily Donchian (Turtle style) with ATR trail
d = resample("1D"); d["atr"] = atr(d, 20); c = d.close
for N in [10, 20, 40, 55, 80]:
    hh = d.high.rolling(N).max().shift(1); ll = d.low.rolling(N).min().shift(1)
    raw = np.where(c > hh, 1, np.where(c < ll, -1, 0)); prev = np.r_[0, raw[:-1]]; fresh = np.where(raw != prev, raw, 0)
    sig = np.r_[0, fresh[:-1]]
    for k in [1.5, 2, 3]:
        sld = np.r_[np.nan, (k * d.atr).values[:-1]]
        for tr in [2, 3, 4]:
            rows.append(report(f"D1 Donch N{N} SL{k} tr{tr}", simulate(d, sig, sld, trail=tr)))
# ---- B. Daily volatility breakout (Larry Williams): buy if close > open + k*prev range; exit next close or trail
for k in [0.5, 0.8, 1.0]:
    rng = (d.high - d.low).shift(1)
    up = c > d.open + k * rng; dn = c < d.open - k * rng
    raw = np.where(up, 1, np.where(dn, -1, 0)); sig = np.r_[0, raw[:-1]]
    for sl in [1.5, 2, 3]:
        sld = np.r_[np.nan, (sl * d.atr).values[:-1]]
        for mode, kw in (("time1", dict(max_bars=1)), ("time3", dict(max_bars=3)), ("tr3", dict(trail=3)), ("tp2", dict(tp_r=2))):
            rows.append(report(f"D1 VolBrk k{k} SL{sl} {mode}", simulate(d, sig, sld, **kw)))
# ---- C. Time-series momentum: sign of N-day return, enter on fresh sign change, trail
for N in [20, 60, 120, 250]:
    mom = np.sign(c - c.shift(N)); raw = mom.fillna(0).values.astype(int); prev = np.r_[0, raw[:-1]]
    fresh = np.where(raw != prev, raw, 0); sig = np.r_[0, fresh[:-1]]
    for sl in [2, 3]:
        sld = np.r_[np.nan, (sl * d.atr).values[:-1]]
        for tr in [3, 5]:
            rows.append(report(f"D1 TSMom N{N} SL{sl} tr{tr}", simulate(d, sig, sld, trail=tr)))
# ---- D. H4 EMA pullback in trend
h4 = resample("4h"); h4["atr"] = atr(h4); c4 = h4.close; e200 = ema(c4, 200)
for pe in [20, 50]:
    e = ema(c4, pe)
    up = (c4 > e200) & (h4.low <= e) & (c4 > e) & (c4 > h4.open)
    dn = (c4 < e200) & (h4.high >= e) & (c4 < e) & (c4 < h4.open)
    raw = np.where(up, 1, np.where(dn, -1, 0)); sig = np.r_[0, raw[:-1]]
    for sl in [1.5, 2, 3]:
        sld = np.r_[np.nan, (sl * h4.atr).values[:-1]]
        for mode, kw in (("tp2", dict(tp_r=2)), ("tp3", dict(tp_r=3)), ("tr3", dict(trail=3))):
            rows.append(report(f"H4 Pullback e{pe} SL{sl} {mode}", simulate(h4, sig, sld, **kw)))
show(rows, 30)
print("variants tested:", len(rows))
