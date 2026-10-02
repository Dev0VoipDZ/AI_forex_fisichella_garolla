"""
Backtester for EA_Gold_TrendBreakout.mq5 v3 (XAUUSD).

Mirrors the EA: signals on closed SignalTF bars (default H1) = fresh close
beyond the DonchianPeriod channel; entry at the next bar's open (+spread for
buys); SL = SL_ATR x ATR; trailing stop Trail_ATR x ATR updated on every price
move; data-mined momentum filter and volatility-regime risk multiplier;
one position at a time; risk-% sizing with 0.01 lot minimum, 0.01 step,
100 oz contract, 1:100 margin; optional drawdown kill switch and Friday flat.

Execution is walked through M15 bars (bullish bars open->low->high->close,
bearish bars open->high->low->close), so stops and trailing are resolved at
15-minute granularity.

Data: M15 CSV with columns Date,open,high,low,close in broker server time.
Tested with ejtraderLabs/historical-data XAUUSD/XAUUSDm15.csv (prices x100):
  git clone --depth 1 --filter=blob:none --sparse https://github.com/ejtraderLabs/historical-data
  cd historical-data && git sparse-checkout set XAUUSD

Usage:
  python gold_backtest.py --data XAUUSDm15.csv --balance 300 --risk 3
  python gold_backtest.py --data XAUUSDm15.csv --report RESULTS_DIR
"""
import argparse
import json
import math
import os

import numpy as np
import pandas as pd

DEFAULTS = dict(SignalTF="1h", DonchianPeriod=200, TrendEMA=0, ATRPeriod=14,
                SL_ATR=2.0, Trail_ATR=4.0, TP_R=0.0,
                MomentumBars=0, MinMomentumATR=5.0, VolBars=168, VolLookbackDays=250,
                LowVolRatio=0.8, LowVolRiskMult=2.0,
                RiskPercent=2.0, MaxRiskAtMinLot=6.0, MaxDrawdownPct=0.0,
                CloseOnFriday=False, FridayCloseHour=21)

CONTRACT = 100.0          # oz per lot
MIN_LOT, LOT_STEP, MAX_LOT = 0.01, 0.01, 100.0
LEVERAGE = 100.0
OOS_START = pd.Timestamp("2019-01-01")


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def atr_sma(df, n):
    """MT5 iATR: simple average of true range."""
    pc = df.close.shift(1)
    tr = pd.concat([df.high - df.low, (df.high - pc).abs(), (df.low - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def load(path, scale):
    df = pd.read_csv(path, parse_dates=["Date"]).rename(columns={"Date": "time"}).set_index("time")
    df = df[["open", "high", "low", "close"]] / scale
    return df.sort_index()


def signals(m15, p):
    """Per M15 bar: signal to act on at its open, and ATR of last closed signal bar."""
    sig_df = m15.resample(p["SignalTF"], label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    n = p["DonchianPeriod"]
    hh = sig_df.high.rolling(n).max().shift(1)
    ll = sig_df.low.rolling(n).min().shift(1)
    c = sig_df.close
    brk = np.where(c > hh, 1, np.where(c < ll, -1, 0))
    prev = np.r_[0, brk[:-1]]
    fresh = np.where(brk != prev, brk, 0)
    if p["TrendEMA"] > 0:
        e = ema(c, p["TrendEMA"]).values
        fresh = np.where(((fresh > 0) & (c.values > e)) | ((fresh < 0) & (c.values < e)), fresh, 0)
    sig_df["atr"] = atr_sma(sig_df, p["ATRPeriod"])
    if p["MomentumBars"] > 0:
        move = (c - c.shift(p["MomentumBars"])).values * fresh
        fresh = np.where(move >= p["MinMomentumATR"] * sig_df.atr.values, fresh, 0)
    sig_df["fresh"] = fresh
    # volatility regime: std of log returns over VolBars / its median, sampled once per day
    bpd = max(1, int(pd.Timedelta("1D") / pd.Timedelta(p["SignalTF"])))
    vol = np.log(c).diff().rolling(p["VolBars"]).std()
    med = pd.concat([vol.shift(bpd * k) for k in range(p["VolLookbackDays"])], axis=1).median(axis=1, skipna=False)
    sig_df["mult"] = np.where((vol / med) < p["LowVolRatio"], p["LowVolRiskMult"], 1.0)

    # value of the last *closed* signal bar, valid from the open of the next one
    nxt = sig_df[["fresh", "atr", "mult"]].copy()
    nxt.index = nxt.index + pd.tseries.frequencies.to_offset(p["SignalTF"])
    # The signal is only acted on at the first M15 bar of the new signal bar
    cur = m15.index.floor(p["SignalTF"])
    out = pd.DataFrame(index=m15.index)
    out["atr"] = nxt.atr.reindex(cur).values
    first = np.r_[True, cur[1:] != cur[:-1]]
    out["mult"] = nxt.mult.reindex(cur).fillna(1.0).values
    out["sig"] = np.where(first, nxt.fresh.reindex(cur).fillna(0).values, 0).astype(int)
    return out


def run(m15, p, balance0, spread, commission):
    s = signals(m15, p)
    T = m15.index
    O, H, L, C = (m15[c].values for c in ("open", "high", "low", "close"))
    SIG, ATR, MULT = s.sig.values, s.atr.values, s.mult.values
    DOW, HOUR = T.dayofweek.values, T.hour.values

    balance, peak, kill = balance0, balance0, False
    pos = None          # dict(dir, entry, sl, tp, lots, risk, t)
    trades, eq = [], np.empty(len(m15))
    skipped = 0

    def close(px, t):
        nonlocal balance, pos
        pnl = (px - pos["entry"]) * pos["dir"] * pos["lots"] * CONTRACT - commission * pos["lots"]
        balance += pnl
        trades.append(dict(open=pos["t"], close=t, dir=pos["dir"], lots=pos["lots"],
                           entry=pos["entry"], exit=px, pnl=pnl,
                           R=pnl / (pos["risk"] * pos["lots"] * CONTRACT)))
        pos = None

    def floating(bid):
        if pos is None:
            return 0.0
        px = bid if pos["dir"] > 0 else bid + spread
        return (px - pos["entry"]) * pos["dir"] * pos["lots"] * CONTRACT

    for i in range(len(m15)):
        atr = ATR[i]
        e_open = balance + floating(O[i])
        peak = max(peak, e_open)
        if not kill and p["MaxDrawdownPct"] > 0 and e_open <= peak * (1 - p["MaxDrawdownPct"] / 100):
            kill = True
            if pos:
                close(O[i] if pos["dir"] > 0 else O[i] + spread, T[i])
        friday = p["CloseOnFriday"] and DOW[i] == 4 and HOUR[i] >= p["FridayCloseHour"]
        if friday and pos:
            close(O[i] if pos["dir"] > 0 else O[i] + spread, T[i])

        # ---- entry at open
        if pos is None and not kill and not friday and SIG[i] != 0 and atr > 0:
            d = SIG[i]
            px = O[i] + spread if d > 0 else O[i]
            sld = p["SL_ATR"] * atr
            equity = balance
            loss_lot = sld * CONTRACT
            lots = min(math.floor(equity * p["RiskPercent"] * MULT[i] / 100 / loss_lot / LOT_STEP + 1e-9) * LOT_STEP, MAX_LOT)
            while lots >= MIN_LOT and lots * CONTRACT * px / LEVERAGE > equity * 0.9:
                lots -= LOT_STEP
            if (lots < MIN_LOT and p["MaxRiskAtMinLot"] > 0
                    and MIN_LOT * loss_lot <= equity * p["MaxRiskAtMinLot"] / 100
                    and MIN_LOT * CONTRACT * px / LEVERAGE <= equity * 0.9):
                lots = MIN_LOT
            lots = round(lots, 2)
            if lots >= MIN_LOT:
                pos = dict(dir=d, entry=px, sl=px - d * sld,
                           tp=px + d * sld * p["TP_R"] if p["TP_R"] > 0 else None,
                           lots=lots, risk=sld, t=T[i])
            else:
                skipped += 1

        # ---- walk the bar
        if pos is not None:
            d = pos["dir"]
            off = 0.0 if d > 0 else spread       # long exits on bid, short exits on ask
            path = [O[i], L[i], H[i], C[i]] if C[i] >= O[i] else [O[i], H[i], L[i], C[i]]
            path = [x + off for x in path]
            if (path[0] - pos["sl"]) * d <= 0:
                close(path[0], T[i])
            else:
                for a, b in zip(path[:-1], path[1:]):
                    if (b - a) * d > 0:
                        if pos["tp"] is not None and (b - pos["tp"]) * d >= 0:
                            close(pos["tp"], T[i])
                            break
                        if p["Trail_ATR"] > 0 and atr > 0:
                            nsl = b - d * p["Trail_ATR"] * atr
                            if (nsl - pos["sl"]) * d > 0:
                                pos["sl"] = nsl
                    elif (b - pos["sl"]) * d <= 0:
                        close(pos["sl"], T[i])
                        break
        eq[i] = balance + floating(C[i])

    if pos is not None:
        close(C[-1] if pos["dir"] > 0 else C[-1] + spread, T[-1])
        eq[-1] = balance
    return pd.Series(eq, index=T), pd.DataFrame(trades), dict(kill=kill, skipped=skipped)


def stats(eq, tr, balance0):
    dd = (eq / eq.cummax() - 1).min() * 100
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    final = eq.iloc[-1]
    cagr = ((final / balance0) ** (1 / years) - 1) * 100 if final > 0 else -100.0
    n = len(tr)
    wins = tr[tr.pnl > 0] if n else tr
    gl = -tr[tr.pnl <= 0].pnl.sum() if n else 0
    hit = eq[eq >= balance0 * 5000 / 300]
    return dict(start=balance0, final=round(final, 2), multiple=round(final / balance0, 2),
                cagr_pct=round(cagr, 1), max_dd_pct=round(dd, 1), trades=n,
                win_rate_pct=round(len(wins) / n * 100, 1) if n else 0,
                profit_factor=round(wins.pnl.sum() / gl, 2) if gl > 0 else None,
                avg_R=round(tr.R.mean(), 3) if n else 0,
                best_R=round(tr.R.max(), 1) if n else 0,
                months_to_16_7x=round((hit.index[0] - eq.index[0]).days / 30.44, 1) if len(hit) else None)


def parse_overrides(pairs):
    out = {}
    for kv in pairs:
        k, v = kv.split("=", 1)
        base = DEFAULTS[k]
        out[k] = (v == "True") if isinstance(base, bool) else type(base)(v)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--price-scale", type=float, default=100.0)
    ap.add_argument("--balance", type=float, default=300.0)
    ap.add_argument("--risk", type=float, default=None, help="RiskPercent override")
    ap.add_argument("--spread", type=float, default=0.35, help="USD per oz")
    ap.add_argument("--commission", type=float, default=7.0, help="USD per lot round turn")
    ap.add_argument("--set", nargs="*", default=[], help="override inputs, e.g. SL_ATR=2.5")
    ap.add_argument("--out", help="write equity.csv, trades.csv, stats.json here")
    a = ap.parse_args()

    p = {**DEFAULTS, **parse_overrides(a.set)}
    if a.risk is not None:
        p["RiskPercent"] = a.risk
    m15 = load(a.data, a.price_scale)
    eq, tr, info = run(m15, p, a.balance, a.spread, a.commission)
    s = {**stats(eq, tr, a.balance), **info}
    print(json.dumps(s, indent=2, default=str))
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        eq.resample("1D").last().dropna().to_csv(os.path.join(a.out, "equity.csv"))
        tr.to_csv(os.path.join(a.out, "trades.csv"), index=False)
        with open(os.path.join(a.out, "stats.json"), "w") as f:
            json.dump({"params": p, "stats": s}, f, indent=2, default=str)


if __name__ == "__main__":
    main()
