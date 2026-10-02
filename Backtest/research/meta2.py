from research import *
import lightgbm as lgb, warnings; warnings.filterwarnings("ignore")
exec(open("ml.py").read().split("# features known")[0])   # rebuild h, F
import sys
SH=sys.argv[1]=='shuffle'
for N in [100, 200]:
    hh = h.high.rolling(N).max().shift(1); ll = h.low.rolling(N).min().shift(1)
    raw = np.where(c > hh, 1, np.where(c < ll, -1, 0))
    s = np.r_[0, raw[:-1]]; prev = np.r_[0, s[:-1]]; sig = np.where(s != prev, s, 0)
    sld = np.r_[np.nan, (2 * h.atr).values[:-1]]
    # take EVERY signal (no skipping while in trade) to build a labelled dataset
    T = []
    for i in np.nonzero(sig)[0]:
        one = np.zeros_like(sig); one[i] = sig[i]
        r = simulate(h, one, sld, trail=4)
        if r: T.append((h.index[i], sig[i], r[0][1]))
    T = pd.DataFrame(T, columns=["t", "dir", "R"]).set_index("t")
    Xf = F.shift(1).reindex(T.index)                     # features at the signal bar close
    signed = [c for c in Xf.columns if c.startswith(("ret", "skew")) or c in ("body",)]
    Xf[signed] = Xf[signed].mul(T.dir, axis=0)
    Xf["dir"] = T.dir
    T["p"] = np.nan
    for Y in range(2015, 2023):
        tr = T.index < pd.Timestamp(f"{Y}-01-01") - pd.Timedelta(days=90)
        te = T.index.year == Y
        if te.sum() == 0: continue
        m = lgb.train(dict(objective="regression", learning_rate=0.05, num_leaves=4, min_data_in_leaf=30,
                           feature_fraction=0.7, lambda_l2=10, verbose=-1),
                      lgb.Dataset(Xf[tr], (T.R[tr].sample(frac=1,random_state=Y).values if SH else T.R[tr]).clip(-1.5, 6)), 150)
        T.loc[te, "p"] = m.predict(Xf[te])
        T.loc[te, "thr"] = np.median(m.predict(Xf[tr]))
    W = T[T.index.year >= 2015]
    for lab, part in (("2015-18", W[W.index.year < 2019]), ("2019-22", W[W.index.year >= 2019])):
        kept = part[part.p > part.thr]
        print(f"N{N} {lab}: all n={len(part):4d} R={part.R.mean():+.3f} | ML-kept n={len(kept):4d} R={kept.R.mean():+.3f} | ML-rejected R={part[part.p <= part.thr].R.mean():+.3f}")

    imp = pd.Series(m.feature_importance("gain"), index=Xf.columns).sort_values(ascending=False)
    print("   top:", list(imp.head(6).index))
