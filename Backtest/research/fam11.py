from research import *
rows = []
for tf, Ns in [("2h", [50, 75, 100, 150]), ("4h", [25, 40, 50, 75])]:
    h = resample(tf); h["atr"] = atr(h); c = h.close
    for N in Ns:
        hh = h.high.rolling(N).max().shift(1); ll = h.low.rolling(N).min().shift(1)
        raw = np.where(c > hh, 1, np.where(c < ll, -1, 0)); prev = np.r_[0, raw[:-1]]; fresh = np.where(raw != prev, raw, 0)
        sig = np.r_[0, fresh[:-1]]
        for k in [1.0, 1.25, 1.5, 2.0]:
            sld = np.r_[np.nan, (k * h.atr).values[:-1]]
            for tr in [3, 4, 5]:
                rows.append(report(f"{tf} N{N} SL{k} tr{tr}", simulate(h, sig, sld, trail=tr)))
show(rows, 25); print("variants:", len(rows))
