from research import *
rows = []
h = resample("1h"); h["atr"] = atr(h); c = h.close; hr = h.index.hour.values
N = 200
hh = h.high.rolling(N).max().shift(1); ll = h.low.rolling(N).min().shift(1)
raw = np.where(c > hh, 1, np.where(c < ll, -1, 0)); prev = np.r_[0, raw[:-1]]; fresh = np.where(raw != prev, raw, 0)
sld2 = np.r_[np.nan, (2 * h.atr).values[:-1]]
# A. entry hour windows (signal bar hour)
for lab, lo, hi in [("all", 0, 24), ("asia", 1, 9), ("london", 8, 16), ("ny", 14, 22), ("ldn+ny", 8, 22), ("no-late", 1, 21)]:
    ok = (hr >= lo) & (hr < hi); s = np.where(ok, fresh, 0); sig = np.r_[0, s[:-1]]
    rows.append(report(f"Donch hours {lab}", simulate(h, sig, sld2, trail=4)))
# B. re-entry: allow any breakout bar (not only fresh) -> re-enters after stop-out if trend continues
sig_any = np.r_[0, raw[:-1]]
rows.append(report("Donch any-bar re-entry tr4", simulate(h, sig_any, sld2, trail=4)))
rows.append(report("Donch any-bar re-entry tr3", simulate(h, sig_any, sld2, trail=3)))
# C. exits on fresh signal: trail variants + breakeven + time stop + opposite-signal exit
sig = np.r_[0, fresh[:-1]]
ex = np.r_[0, raw[:-1]]  # exit flag: opposite breakout closes the trade
for tr in [3, 4, 5]:
    rows.append(report(f"Donch tr{tr} + opposite-exit", simulate(h, sig, sld2, trail=tr, exit_sig=-ex)))
    rows.append(report(f"Donch tr{tr} + BE@1R", simulate(h, sig, sld2, trail=tr, be_r=1)))
    rows.append(report(f"Donch tr{tr} + BE@2R", simulate(h, sig, sld2, trail=tr, be_r=2)))
    for mb in [72, 168, 336]:
        rows.append(report(f"Donch tr{tr} + time{mb}h", simulate(h, sig, sld2, trail=tr, max_bars=mb)))
# D. stop variants
for k in [1, 1.5, 2.5]:
    sld = np.r_[np.nan, (k * h.atr).values[:-1]]
    rows.append(report(f"Donch SL{k} tr4", simulate(h, sig, sld, trail=4)))
# E. channel-based stop: stop at opposite channel (N/4 bars)
for M in [20, 50]:
    lo_m = h.low.rolling(M).min().shift(1); hi_m = h.high.rolling(M).max().shift(1)
    dist = np.where(fresh > 0, c - lo_m, np.where(fresh < 0, hi_m - c, np.nan))
    sld = np.r_[np.nan, dist[:-1]]
    rows.append(report(f"Donch SL=chan{M} tr4", simulate(h, sig, sld, trail=4)))
show(rows, 40); print("variants:", len(rows))
