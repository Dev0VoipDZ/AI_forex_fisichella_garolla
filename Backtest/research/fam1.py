from research import *
rows = []
for tf in ["1h", "4h"]:
    df = resample(tf); df["atr"] = atr(df)
    c = df.close
    for N in [20, 55]:
        hh = df.high.rolling(N).max().shift(1); ll = df.low.rolling(N).min().shift(1)
        for filt in [0, 200]:
            raw = np.where(c > hh, 1, np.where(c < ll, -1, 0))
            if filt:
                e = ema(c, filt); raw = np.where((raw > 0) & (c > e), 1, np.where((raw < 0) & (c < e), -1, 0))
            sig = np.r_[0, raw[:-1]]
            prev = np.r_[0, sig[:-1]]; sig = np.where(sig != prev, sig, 0)    # fresh only
            for k in [2, 3, 4]:
                sld = np.r_[np.nan, (k * df.atr).values[:-1]]
                for trail in [0, 3, 5]:
                    for tp in [0, 3]:
                        if trail == 0 and tp == 0: continue
                        rows.append(report(f"Donch {tf} N{N} f{filt} SL{k} tr{trail} tp{tp}",
                                           simulate(df, sig, sld, tp_r=tp, trail=trail)))
show(rows, 30)
