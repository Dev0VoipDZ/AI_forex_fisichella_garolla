exec(open("meta.py").read().split("    T[\"p\"] = np.nan")[0].replace("for N in [55, 100, 200]:", "for N in [100]:"))
# relative vol: vol168 vs its own 1-year median (stationary)
vr = (F.vol168 / F.vol168.rolling(24*250).median()).shift(1).reindex(T.index)
D = pd.DataFrame({"R": T.R, "dir": T.dir, "vol168": Xf.vol168, "vrel": vr, "skew": Xf.skew168, "ret168": Xf.ret168,
                  "ret500": Xf.ret500, "vol24r": Xf.volratio}).dropna()
D["per"] = np.where(D.index.year < 2019, "A_12-18", "B_19-22")
for col in ["vrel", "skew", "ret168", "ret500", "vol24r"]:
    D["q"] = pd.qcut(D[col], 5, labels=False)
    print(col, "quintile edges:", np.round(D[col].quantile([.2,.4,.6,.8]).values, 2))
    print(D.pivot_table(index="per", columns="q", values="R", aggfunc="mean").round(2).to_string())
pd.to_pickle(D, "dist.pkl")
