exec(open("rule.py").read().split("rows = []")[0])
N = 100
hh = h.high.rolling(N).max().shift(1); ll = h.low.rolling(N).min().shift(1)
raw = np.where(c > hh, 1, np.where(c < ll, -1, 0)); prev = np.r_[0, raw[:-1]]; fresh = np.where(raw != prev, raw, 0)
s = np.where(h.mom.values * fresh >= 5, fresh, 0); sig = np.r_[0, s[:-1]]
sld = np.r_[np.nan, (2 * h.atr).values[:-1]]
T = pd.DataFrame(simulate(h, sig, sld, trail=4), columns=["t", "R"]).set_index("t")
T["vrel"] = h.vrel.shift(1).reindex(T.index)          # value at the signal bar close
yrs = (T.index[-1] - T.index[0]).days / 365.25
print(f"trades={len(T)} ({len(T)/yrs:.0f}/yr), low-vol share={(T.vrel<0.8).mean():.0%}")
for base in [0.02, 0.03, 0.04]:
    for mult in [1, 2]:
        w = np.where(T.vrel < 0.8, mult, 1.0)
        f = base * w
        for lab, m in (("all", slice(None)), ("2019-22", T.index >= SPLIT)):
            R = T.R.values[m]; ff = f[m]
            eq = np.cumprod(1 + ff * R); dd = (eq / np.maximum.accumulate(eq) - 1).min()
            hit = np.argmax(eq * 300 >= 5000) if (eq * 300 >= 5000).any() else None
            when = f"{(T.index[m][hit] - T.index[m][0]).days/30.44:.0f}mo" if hit is not None else "-"
            print(f"base {base:.0%} x{mult} on low-vol | {lab:7s} final x{eq[-1]:8.1f} maxDD {dd*100:5.1f}%  $5k after {when}")
T.to_pickle("tier_trades.pkl")
