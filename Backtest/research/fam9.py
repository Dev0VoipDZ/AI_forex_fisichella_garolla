from research import *
h = resample("1h"); h["atr"] = atr(h); c = h.close; hr = h.index.hour.values
rows = []; grid = {}
for N in [100, 150, 200, 300]:
    hh = h.high.rolling(N).max().shift(1); ll = h.low.rolling(N).min().shift(1)
    raw = np.where(c > hh, 1, np.where(c < ll, -1, 0)); prev = np.r_[0, raw[:-1]]; fresh = np.where(raw != prev, raw, 0)
    for hours in ["all", "ny"]:
        ok = (hr >= 14) & (hr < 22) if hours == "ny" else np.ones(len(h), bool)
        sig = np.r_[0, np.where(ok, fresh, 0)[:-1]]
        for k in [0.75, 1.0, 1.25, 1.5, 2.0]:
            sld = np.r_[np.nan, (k * h.atr).values[:-1]]
            for tr in [3, 4, 5, 6]:
                name = f"N{N} {hours} SL{k} tr{tr}"; r = report(name, simulate(h, sig, sld, trail=tr)); rows.append(r)
                grid[(N, hours, k, tr)] = (r[1]["IS"][1], r[1]["OOS"][1], r[1]["IS"][3], r[1]["OOS"][3], r[1]["OOS"][4])
show(rows, 20); print("variants:", len(rows))
# plateau map: SL x trail for N200 all-hours, cells = IS R / OOS R
print("\nN200 all-hours, cell = IS R / OOS R")
for k in [0.75, 1.0, 1.25, 1.5, 2.0]:
    print(f"SL{k:<5}", "  ".join(f"tr{tr}: {grid[(200,'all',k,tr)][0]:+.2f}/{grid[(200,'all',k,tr)][1]:+.2f}" for tr in [3,4,5,6]))
print("\nSL1.5 tr4 across N (all / ny): IS R / OOS R / OOS x / OOS dd")
for N in [100,150,200,300]:
    for hours in ["all","ny"]:
        g = grid[(N,hours,1.5,4)]; print(f"  N{N} {hours:4s} {g[0]:+.2f} / {g[1]:+.2f} / x{g[3]:.2f} / {g[4]*100:.0f}%")
