from research import *
h = resample("1h"); h["atr"] = atr(h); c = h.close; lc = np.log(c); r1 = lc.diff()
vol = r1.rolling(168).std()
med = pd.concat([vol.shift(24 * k) for k in range(250)], axis=1).median(axis=1)
h["vrel"] = vol / med
h["mom"] = (c - c.shift(168)) / h.atr          # weekly move in ATR units
rows = []
for N in [100, 150, 200]:
    hh = h.high.rolling(N).max().shift(1); ll = h.low.rolling(N).min().shift(1)
    raw = np.where(c > hh, 1, np.where(c < ll, -1, 0))
    prev = np.r_[0, raw[:-1]]; fresh = np.where(raw != prev, raw, 0)
    for vmax in [0.8, 0.9, 1.0, 9]:
        for mmin in [-99, 2.5, 5]:
            ok = (h.vrel.values < vmax) & (h.mom.values * fresh >= mmin)
            s = np.where(ok, fresh, 0)
            sig = np.r_[0, s[:-1]]
            sld = np.r_[np.nan, (2 * h.atr).values[:-1]]
            for tr in [3, 4]:
                rows.append(report(f"N{N} vrel<{vmax} mom>={mmin} tr{tr}", simulate(h, sig, sld, trail=tr), risk=0.03))
show(rows, 25)
