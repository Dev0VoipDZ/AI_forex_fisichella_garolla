from research import *
rows = []
# --- RSI(2) mean reversion in trend (Connors style), H1 and H4
for tf in ["1h", "4h"]:
    df = resample(tf); df["atr"] = atr(df); c = df.close
    e200 = ema(c, 200); e5 = ema(c, 5); r2 = rsi(c, 2)
    for lo in [5, 10, 20]:
        raw = np.where((c > e200) & (r2 < lo), 1, np.where((c < e200) & (r2 > 100 - lo), -1, 0))
        sig = np.r_[0, raw[:-1]]
        ex = np.where(c > e5, -1, np.where(c < e5, 1, 0))  # long exits when close>ema5 (flag -1 vs d=1)
        for k in [2, 3, 5]:
            sld = np.r_[np.nan, (k * df.atr).values[:-1]]
            for mb in [0, 10]:
                rows.append(report(f"RSI2 {tf} lo{lo} SL{k} mb{mb}", simulate(df, sig, sld, max_bars=mb, exit_sig=ex)))
# --- Asian range breakout on M15/H1, SL = k*ATR, end-of-day exit
for tf in ["15min", "1h"]:
    df = resample(tf); df["atr"] = atr(df); c = df.close
    day = df.index.normalize(); hr = df.index.hour
    a = df[(hr >= 0) & (hr < 7)].groupby(day[(hr >= 0) & (hr < 7)]).agg(ah=("high", "max"), al=("low", "min"))
    ah = a.ah.reindex(day).values; al = a.al.reindex(day).values
    h1 = resample("1h"); tr = ema(h1.close, 200)
    trend = np.sign(h1.close - tr).reindex(df.index.floor("1h") - pd.Timedelta(hours=1)).fillna(0).values
    for filt in [0, 1]:
        for win_end in [12, 16]:
            ok = (hr >= 7) & (hr < win_end)
            up = ok & (c.values > ah) & (np.r_[np.inf, c.values[:-1]] <= np.r_[np.inf, ah[:-1]])
            dn = ok & (c.values < al) & (np.r_[-np.inf, c.values[:-1]] >= np.r_[-np.inf, al[:-1]])
            if filt: up &= trend > 0; dn &= trend < 0
            raw = np.where(up, 1, np.where(dn, -1, 0))
            # one per side per day
            s = pd.Series(raw, index=df.index); first = s.groupby([day, s]).cumcount() == 0
            raw = np.where(first.values, raw, 0)
            sig = np.r_[0, raw[:-1]]
            for k in [1.5, 3]:
                sld = np.r_[np.nan, (k * df.atr).values[:-1]]
                for tp in [0, 2, 3]:
                    for eod in [None, 22]:
                        if tp == 0 and eod is None: continue
                        rows.append(report(f"Asian {tf} f{filt} we{win_end} SL{k} tp{tp} eod{eod}",
                                           simulate(df, sig, sld, tp_r=tp, eod_hour=eod)))
show(rows, 25)
