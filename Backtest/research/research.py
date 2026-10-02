"""Strategy research harness: per-trade R simulation with costs, IS/OOS split."""
import itertools, math, sys
import numpy as np, pandas as pd

import os
D = os.environ.get("GOLD_M15_CSV", "XAUUSDm15.csv")
COST = 0.42          # spread 0.35 + commission 0.07 per oz, round trip
SPLIT = pd.Timestamp("2019-01-01")

m15 = pd.read_csv(D, parse_dates=["Date"]).rename(columns={"Date": "time"}).set_index("time")
m15 = m15[["open", "high", "low", "close"]] / 100.0


def resample(rule):
    return m15.resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()


def ema(s, n): return s.ewm(span=n, adjust=False).mean()


def atr(df, n=14):
    pc = df.close.shift(1)
    tr = pd.concat([df.high - df.low, (df.high - pc).abs(), (df.low - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def rsi(s, n):
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def simulate(df, sig, sld, tp_r=0.0, trail=0.0, be_r=0.0, max_bars=0, exit_sig=None, eod_hour=None):
    """sig[i] decided on close of bar i-1, entry at open of bar i. Returns list of (time, R)."""
    O, H, L, C = df.open.values, df.high.values, df.low.values, df.close.values
    A = df.atr.values
    hours = df.index.hour.values
    T = df.index
    out = []
    i, n = 0, len(df)
    while i < n:
        s = sig[i]
        if s == 0 or not (sld[i] > 0):
            i += 1
            continue
        d, e, r = s, O[i], sld[i]
        sl = e - d * r
        tp = e + d * tp_r * r if tp_r > 0 else None
        be = False
        j = i
        exit_px = None
        while j < n:
            path = [O[j], L[j], H[j], C[j]] if C[j] >= O[j] else [O[j], H[j], L[j], C[j]]
            if (O[j] - sl) * d <= 0:
                exit_px = O[j]; break
            for a, b in zip(path[:-1], path[1:]):
                if (b - a) * d > 0:
                    if be_r > 0 and not be and (b - e) * d >= be_r * r:
                        be = True; sl = max(sl, e) if d > 0 else min(sl, e)
                    if tp is not None and (b - tp) * d >= 0:
                        exit_px = tp; break
                    if trail > 0:
                        nsl = b - d * trail * A[j - 1]
                        if (nsl - sl) * d > 0: sl = nsl
                else:
                    if (b - sl) * d <= 0:
                        exit_px = sl; break
            if exit_px is not None: break
            # bar-close exits
            if max_bars and j - i + 1 >= max_bars:
                exit_px = C[j]; break
            if exit_sig is not None and exit_sig[j] * d < 0:   # exit flag on close
                exit_px = C[j]; break
            if eod_hour is not None and hours[j] == eod_hour:
                exit_px = C[j]; break
            j += 1
        if exit_px is None:
            exit_px = C[-1]; j = n - 1
        R = ((exit_px - e) * d - COST) / r
        out.append((T[i], R))
        i = j + 1
    return out


def report(name, trades, risk=0.02):
    t = pd.DataFrame(trades, columns=["t", "R"])
    res = {}
    for lab, part in (("IS", t[t.t < SPLIT]), ("OOS", t[t.t >= SPLIT])):
        if len(part) == 0:
            res[lab] = (0, 0, 0, 0, 0); continue
        R = part.R.values
        eq = np.cumprod(1 + risk * R)
        dd = (eq / np.maximum.accumulate(eq) - 1).min()
        pf = R[R > 0].sum() / -R[R < 0].sum() if (R < 0).any() else 99
        res[lab] = (len(R), R.mean(), pf, eq[-1], dd)
    return name, res


def show(rows, top=25, key="IS"):
    rows = [r for r in rows if r[1]["IS"][0] >= 60]
    rows.sort(key=lambda r: r[1][key][1] if r[1][key][0] else -9, reverse=True)
    for name, res in rows[:top]:
        i, o = res["IS"], res["OOS"]
        print(f"{name:60s} IS n={i[0]:4d} R={i[1]:+.3f} PF={i[2]:.2f} x{i[3]:6.2f} | "
              f"OOS n={o[0]:4d} R={o[1]:+.3f} PF={o[2]:.2f} x{o[3]:6.2f} dd={o[4]*100:5.1f}%")
