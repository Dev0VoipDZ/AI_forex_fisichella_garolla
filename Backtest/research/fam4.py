from research import *
import pickle
rows = []; streams = {}
for tf in ["1h", "2h", "4h"]:
    df = resample(tf); df["atr"] = atr(df); c = df.close
    for N in [100, 120, 150, 200]:
        hh = df.high.rolling(N).max().shift(1); ll = df.low.rolling(N).min().shift(1)
        raw = np.where(c > hh, 1, np.where(c < ll, -1, 0))
        sig = np.r_[0, raw[:-1]]; prev = np.r_[0, sig[:-1]]; sig = np.where(sig != prev, sig, 0)
        for k in [2]:
            sld = np.r_[np.nan, (k * df.atr).values[:-1]]
            for trail in [3, 4, 5]:
                tr = simulate(df, sig, sld, trail=trail); name = f"Donch {tf} N{N} SL{k} tr{trail}"
                rows.append(report(name, tr)); streams[name] = tr
show(rows, 40)
pickle.dump(streams, open("streams.pkl", "wb"))
