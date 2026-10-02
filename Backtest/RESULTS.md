# Backtest results: EA_Gold_TrendBreakout (XAUUSD)

![Equity curves](results/equity_300.png)

**Data:** XAUUSD M15, May 2012 – Mar 2022, ~230k bars, broker server time (GMT+2/+3), from
[ejtraderLabs/historical-data](https://github.com/ejtraderLabs/historical-data).
**Costs:** $0.35 spread + $7/lot commission per round trip. **Execution:** signals on H1, stops and trailing
walked through M15 bars. Lot size 0.01 min / 0.01 step, 100 oz contract, 1:100 leverage.

**Settings:** H1, Donchian 200, stop 2×ATR(14), trailing 4×ATR, no fixed TP, one position at a time.

## $300 starting balance

| Risk/trade | Final balance | Multiple | Max drawdown | Months to reach $5,000 |
|---|---|---|---|---|
| 2% | $3,159 | ×10.5 | −24.6% | not reached |
| **3% (Balanced)** | **$6,818** | **×22.7** | **−35.7%** | **93** |
| 5% (Aggressive) | $17,424 | ×58.1 | −53.5% | 62 |
| 8% | $40,719 | ×135.7 | −71.5% | 49 |

Return per calendar year:

|         |   2012 |   2013 |   2014 |   2015 |   2016 |   2017 |   2018 |   2019 |   2020 |   2021 |   2022* |
|:--------|-------:|-------:|-------:|-------:|-------:|-------:|-------:|-------:|-------:|-------:|-------:|
| 2% risk |     -3% |     94% |     23% |     23% |     41% |     28% |     -1% |     22% |     76% |      6% |     -8% |
| 3% risk |     -3% |    102% |     29% |     42% |     68% |     39% |     -7% |     34% |    130% |      7% |    -11% |
| 5% risk |    -16% |    159% |     40% |     36% |    130% |     56% |    -16% |     54% |    247% |      8% |    -19% |

\* 2012 from May, 2022 to early March.

## $10,000 at 1% risk (Conservative)
×3.66 ($36,641), CAGR 14.2%, max drawdown −13.9%, 463 trades, win rate 36.9%, profit factor 1.50,
average +0.32R per trade, best trade +19.2R. Longest losing streak: 12 trades.

## Robustness checks
* **Tuned on 2012–2018, then tested on 2019–2022 data it had never seen.** The edge held:
  +0.33R per trade before, +0.42R after. At 3% risk, 2019–2022 alone was ×3.0 with a −25% max drawdown.
* **Parameter plateau:** 190 of 192 Donchian variants (H1/H2/H4, N 40–100, stop 2–3 ATR,
  trailing 2.5–5 ATR) were profitable in both periods. The chosen settings sit in the middle of the
  best region, not at a single lucky spike.
* **Cost stress:** spread $0.60 → profit factor 1.44. Spread $1.00 → profit factor 1.34 (still profitable).
* **Both directions work:** longs +0.28R (250 trades), shorts +0.37R (213 trades).

## Monte Carlo, $300 → $5,000 (2,000 reshuffles of the trade sequence)
| Risk | Chance of reaching ×16.7 | Median time | Chance of a >50% drawdown | Chance of a >80% drawdown |
|---|---|---|---|---|
| 2% | 49% | ~92 months | 4% | 0% |
| 3% | 78% | ~74 months | 36% | 0.5% |
| 5% | 90% | ~52 months | 92% | 11% |
| 10% | 92% | ~37 months | 100% | 90% |

## What did NOT work (also tested, rejected)
* Original M15 session-momentum EA (Asian breakout + EMA pullback): **−0.20R per trade after costs**.
  M15 stops are too small relative to spread and commission.
* Asian-range breakout on M15/H1 with various exits: unstable, lost money on the 2019–2022 data.
* RSI(2) mean reversion on H1/H4: negative after costs.

## Caveats
* Bar-based simulation, not tick data. Fill price, slippage and weekend gaps can differ live.
* The data ends in March 2022. Gold is now far more volatile in dollar terms, so ATR-based stops
  are wider. At $300 on a standard account, 0.01 lot may already exceed 6% risk; the EA then skips
  the trade. **Use a cent account, or start with $1,000+.**
* Past performance does not guarantee future results. Trend-following has long flat periods
  (2018, 2021–22) and earns most of its profit from a few big trends.

Reproduce: `python Backtest/gold_backtest.py --data XAUUSDm15.csv --balance 300 --risk 3 --out Backtest/results/risk3`,
then `cd Backtest && python make_report.py`.
