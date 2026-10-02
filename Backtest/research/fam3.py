from research import *
rows = []
for tf in ["1h", "2h", "4h"]:
    df = resample(tf); df["atr"] = atr(df); c = df.close
    e = ema(c, 200)
    for N in [40, 55, 70, 100]:
        hh = df.high.rolling(N).max().shift(1); ll = df.low.rolling(N).min().shift(1)
        for filt in [0, 200]:
            raw = np.where(c > hh, 1, np.where(c < ll, -1, 0))
            if filt: raw = np.where((raw > 0) & (c > e), 1, np.where((raw < 0) & (c < e), -1, 0))
            sig = np.r_[0, raw[:-1]]; prev = np.r_[0, sig[:-1]]; sig = np.where(sig != prev, sig, 0)
            for k in [2, 3]:
                sld = np.r_[np.nan, (k * df.atr).values[:-1]]
                for trail in [2.5, 3, 4, 5]:
                    rows.append(report(f"Donch {tf} N{N} f{filt} SL{k} tr{trail}", simulate(df, sig, sld, trail=trail)))
t = pd.DataFrame([(n, r["IS"][1], r["OOS"][1], r["IS"][0], r["OOS"][0]) for n, r in rows], columns=["name","isR","oosR","isN","oosN"])
t["tf"] = t.name.str.split().str[1]
print("share of variants positive IS & OOS:", ((t.isR>0)&(t.oosR>0)).mean().round(2), "of", len(t))
print(t.groupby("tf")[["isR","oosR","isN","oosN"]].mean().round(3))
for col in ["N", "f", "SL", "tr"]:
    t[col] = t.name.str.extract(rf" {col}([\d.]+)")[0]
    print(t.groupby(col)[["isR","oosR"]].mean().round(3).T)
show(rows, 12)
