from research import *
h, thr = pd.read_pickle("ml_pred.pkl")
h = h[h.index >= "2015-01-01"].copy()
yr = h.index.year
rows = []
for q in [0.95, 0.98, 0.99]:
    # thresholds re-derived from training predictions at quantile q (only past data)
    import lightgbm  # noqa
    lo_q = 1 - q
    hi_t = pd.Series({Y: None for Y in thr})
    p = h.pred.values
    # per-year threshold from the training distribution saved in thr (95/5) scaled: recompute simply from prior-year preds
    th_hi = np.array([np.nanquantile(h.pred[(yr < Y) | (yr == 2015) & (yr == Y)], q) if (yr < Y).any() else thr[Y][0] for Y in yr]) if False else None
    hi = pd.Series(yr).map({Y: (np.nanquantile(h.pred[yr < Y], q) if (yr < Y).any() else thr[Y][0]) for Y in set(yr)}).values
    lo = pd.Series(yr).map({Y: (np.nanquantile(h.pred[yr < Y], lo_q) if (yr < Y).any() else thr[Y][1]) for Y in set(yr)}).values
    raw = np.where(p > hi, 1, np.where(p < lo, -1, 0))
    sig = np.r_[0, raw[:-1]]
    for k in [1.5, 2, 3]:
        sld = np.r_[np.nan, (k * h.atr).values[:-1]]
        for mode in ["time24", "tp2", "trail3", "tp3_time48"]:
            kw = dict(time24=dict(max_bars=24), tp2=dict(tp_r=2), trail3=dict(trail=3),
                      tp3_time48=dict(tp_r=3, max_bars=48))[mode]
            rows.append(report(f"ML q{q} SL{k} {mode}", simulate(h, sig, sld, **kw)))
# IS here = 2015-2018 (walk-forward predictions), OOS = 2019-2022
rows = [r for r in rows]
for name, res in sorted(rows, key=lambda r: r[1]["IS"][1], reverse=True)[:15]:
    i, o = res["IS"], res["OOS"]
    print(f"{name:32s} 2015-18 n={i[0]:4d} R={i[1]:+.3f} PF={i[2]:.2f} | 2019-22 n={o[0]:4d} R={o[1]:+.3f} PF={o[2]:.2f} x{o[3]:.2f} dd={o[4]*100:.0f}%")
