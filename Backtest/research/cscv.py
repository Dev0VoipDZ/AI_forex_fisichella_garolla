"""CSCV / Probability of Backtest Overfitting (Bailey et al.) over the H1 Donchian grid (N x SL x trail, all hours)."""
from research import *
import itertools, pickle
h = resample("1h"); h["atr"] = atr(h); c = h.close
streams = {}
for N in [100, 150, 200, 300]:
    hh = h.high.rolling(N).max().shift(1); ll = h.low.rolling(N).min().shift(1)
    raw = np.where(c > hh, 1, np.where(c < ll, -1, 0)); prev = np.r_[0, raw[:-1]]; fresh = np.where(raw != prev, raw, 0)
    sig = np.r_[0, fresh[:-1]]
    for k in [0.75, 1.0, 1.25, 1.5, 2.0]:
        sld = np.r_[np.nan, (k * h.atr).values[:-1]]
        for tr in [3, 4, 5, 6]:
            streams[(N, k, tr)] = simulate(h, sig, sld, trail=tr)
pickle.dump(streams, open("grid_streams.pkl", "wb"))
# monthly P&L matrix (2% risk per trade) : T months x K variants
def monthly(tr): t = pd.DataFrame(tr, columns=["t","R"]).set_index("t"); return (0.02*t.R).groupby(t.index.to_period("M")).sum()
M = pd.DataFrame({k: monthly(v) for k, v in streams.items()}).fillna(0.0)
M = M[M.index >= "2012-09"]   # drop warm-up
T, K = M.shape; S = 10
blocks = np.array_split(np.arange(T), S)
def sharpe(x): s = x.std(axis=0); return np.where(s > 0, x.mean(axis=0) / s, 0) * np.sqrt(12)
logits = []; is_best_oos_rank = []
for comb in itertools.combinations(range(S), S // 2):
    tr_idx = np.concatenate([blocks[i] for i in comb]); te_idx = np.concatenate([blocks[i] for i in range(S) if i not in comb])
    sh_is = sharpe(M.values[tr_idx]); sh_oos = sharpe(M.values[te_idx])
    best = np.argmax(sh_is)
    rank = (sh_oos < sh_oos[best]).mean()           # relative OOS rank of IS-best, in [0,1)
    rank = min(max(rank, 1e-6), 1 - 1e-6); logits.append(np.log(rank / (1 - rank))); is_best_oos_rank.append(rank)
logits = np.array(logits)
print(f"variants K={K}, months T={T}, splits={len(logits)}")
print(f"PBO (prob. IS-best is below OOS median) = {(logits < 0).mean():.3f}")
print(f"median OOS rank of IS-best = {np.median(is_best_oos_rank):.2f}  (1.0 = best of all, 0.5 = median)")
# how often is each config the IS-best, and its OOS rank then
from collections import Counter
cnt = Counter()
for comb in itertools.combinations(range(S), S // 2):
    tr_idx = np.concatenate([blocks[i] for i in comb]); cnt[M.columns[np.argmax(sharpe(M.values[tr_idx]))]] += 1
print("most often IS-best:", cnt.most_common(6))
# Deflated Sharpe for the best full-sample config
sh = sharpe(M.values); best = np.argmax(sh); n = T
var_sh = np.var(sh); e_max = np.sqrt(var_sh) * ((1 - 0.5772) * __import__("scipy.stats", fromlist=["norm"]).norm.ppf(1 - 1/K) + 0.5772 * __import__("scipy.stats", fromlist=["norm"]).norm.ppf(1 - 1/(K*np.e)))
x = M.values[:, best]; skew = pd.Series(x).skew(); kurt = pd.Series(x).kurt() + 3
sr = sh[best] / np.sqrt(12); sr0 = e_max / np.sqrt(12)
from scipy.stats import norm
dsr = norm.cdf((sr - sr0) * np.sqrt(n - 1) / np.sqrt(1 - skew * sr + (kurt - 1) / 4 * sr**2))
print(f"best full-sample: {M.columns[best]} Sharpe {sh[best]:.2f}; expected max Sharpe under no skill {e_max:.2f}; DSR = {dsr:.3f}")
