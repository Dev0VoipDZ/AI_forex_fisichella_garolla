"""Pyramiding: Turtle-style adds. Units added every add_atr move in favour, up to max_units; stop for all units = last entry - sl_atr*ATR."""
from research import *
h = resample("1h"); h["atr"] = atr(h); c = h.close
N = 200
hh = h.high.rolling(N).max().shift(1); ll = h.low.rolling(N).min().shift(1)
raw = np.where(c > hh, 1, np.where(c < ll, -1, 0)); prev = np.r_[0, raw[:-1]]; fresh = np.where(raw != prev, raw, 0)
sig = np.r_[0, fresh[:-1]]
O, H, L, C, A = h.open.values, h.high.values, h.low.values, h.close.values, h.atr.values
T = h.index

def simulate_pyr(sl_atr, trail, add_atr, max_units, unit_frac=None):
    """Returns list of (time, R) where R is total P&L in units of the FIRST unit's risk (1 unit = 1R at full size).
       unit_frac: size of each add relative to the first unit (list) or None=equal."""
    out = []; i = 0; n = len(h)
    while i < n:
        d = sig[i]
        if d == 0 or not A[i-1] > 0: i += 1; continue
        a0 = A[i-1]; r = sl_atr * a0
        entries = [O[i]]; sizes = [1.0]; sl = O[i] - d * r
        next_add = O[i] + d * add_atr * a0
        j = i; exit_px = None
        while j < n:
            path = [O[j], L[j], H[j], C[j]] if C[j] >= O[j] else [O[j], H[j], L[j], C[j]]
            if (O[j] - sl) * d <= 0: exit_px = O[j]; break
            for a, b in zip(path[:-1], path[1:]):
                if (b - a) * d > 0:
                    # adds
                    while len(entries) < max_units and (b - next_add) * d >= 0:
                        entries.append(next_add); sizes.append(1.0 if unit_frac is None else unit_frac[len(entries)-1])
                        sl = max(sl, next_add - d * r) if d > 0 else min(sl, next_add - d * r)
                        next_add = next_add + d * add_atr * a0
                    nsl = b - d * trail * A[j-1]
                    if (nsl - sl) * d > 0: sl = nsl
                else:
                    if (b - sl) * d <= 0: exit_px = sl; break
            if exit_px is not None: break
            j += 1
        if exit_px is None: exit_px = C[-1]; j = n - 1
        pnl = sum(((exit_px - e) * d - COST) * s for e, s in zip(entries, sizes))
        out.append((T[i], pnl / r, len(entries)))
        i = j + 1
    return out

rows = []
base = simulate_pyr(2, 4, 1e9, 1)
for add in [0.5, 1.0, 1.5, 2.0]:
    for mu in [2, 3, 4]:
        for tr in [3, 4]:
            res = simulate_pyr(2, tr, add, mu)
            t = pd.DataFrame(res, columns=["t", "R", "units"])
            # exposure-normalised: risk budget per trade = max_units; report R per max-unit so sizing is comparable
            name = f"Pyr add{add}ATR max{mu} tr{tr}"
            rr = [(a, b / mu) for a, b, _ in res]
            rows.append(report(name + " (R/maxunits)", rr))
rows.append(report("Baseline single unit", [(a, b) for a, b, _ in base]))
show(rows, 30)
# distribution of units actually reached for the best
res = simulate_pyr(2, 4, 1.0, 3); t = pd.DataFrame(res, columns=["t","R","units"]); print(t.units.value_counts().sort_index().to_dict())
