from research import *
import lightgbm as lgb, warnings; warnings.filterwarnings("ignore")
h = resample("1h"); h["atr"] = atr(h)
c = h.close; lc = np.log(c)
F = pd.DataFrame(index=h.index)
for n in [1, 2, 4, 8, 24, 72, 168, 500]:
    F[f"ret{n}"] = (lc - lc.shift(n)) / (h.atr / c)            # return in ATR units
r1 = lc.diff()
for n in [24, 168]:
    F[f"vol{n}"] = r1.rolling(n).std()
F["volratio"] = F.vol24 / F.vol168
for n in [24, 168, 500]:
    hi, lo = h.high.rolling(n).max(), h.low.rolling(n).min()
    F[f"pos{n}"] = (c - lo) / (hi - lo)
    F[f"dhi{n}"] = (hi - c) / h.atr
    F[f"dlo{n}"] = (c - lo) / h.atr
F["body"] = (h.close - h.open) / (h.high - h.low).replace(0, np.nan)
F["upwick"] = (h.high - np.maximum(h.open, h.close)) / h.atr
F["dnwick"] = (np.minimum(h.open, h.close) - h.low) / h.atr
F["hour"] = h.index.hour; F["dow"] = h.index.dayofweek
day = h.index.normalize()
F["ret_today"] = (lc - pd.Series(lc.groupby(day).transform("first").values, index=h.index)) / (h.atr / c)
F["atr_pct"] = h.atr / c
F["skew168"] = r1.rolling(168).skew()
# features known at close of bar t; we act at open of t+1
H = 24
fwd = (c.shift(-H) - c) / h.atr      # target: next 24h move in ATR
X = F.shift(0); y = fwd
ok = X.notna().all(axis=1) & y.notna()
params = dict(objective="regression", learning_rate=0.03, num_leaves=15, min_data_in_leaf=400,
              feature_fraction=0.7, bagging_fraction=0.7, bagging_freq=1, lambda_l2=10, verbose=-1)
pred = pd.Series(np.nan, index=h.index); thr = {}
for Y in range(2015, 2023):
    tr = ok & (h.index < pd.Timestamp(f"{Y}-01-01") - pd.Timedelta(days=2))
    te = ok.index[(h.index.year == Y)]
    m = lgb.train(params, lgb.Dataset(X[tr], y[tr]), num_boost_round=300)
    p_tr = m.predict(X[tr]); pred.loc[te] = m.predict(X.loc[te].fillna(0))
    thr[Y] = (np.quantile(p_tr, 0.95), np.quantile(p_tr, 0.05))
    if Y == 2022:
        imp = pd.Series(m.feature_importance("gain"), index=X.columns).sort_values(ascending=False)
        print("top features:", imp.head(10).round(0).to_dict())
h["pred"] = pred
yrs = h.index.year
ic = pd.DataFrame({"p": pred, "y": fwd}).dropna()
print("rank IC by year:", ic.groupby(ic.index.year).apply(lambda d: d.p.corr(d.y, method="spearman")).round(3).to_dict())
pd.to_pickle((h, thr), "ml_pred.pkl")
