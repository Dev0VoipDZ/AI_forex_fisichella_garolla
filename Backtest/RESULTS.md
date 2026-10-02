# Backtest results: EA_Gold_TrendBreakout v3 (XAUUSD)

![Equity curves](results/equity_300.png)

**Data:** XAUUSD M15, May 2012 – Mar 2022 (~230k bars, broker server time GMT+2/+3), from
[ejtraderLabs/historical-data](https://github.com/ejtraderLabs/historical-data).
**Costs:** $0.35 spread + $7/lot commission per round trip. **Execution:** signals on H1, stops and trailing
walked through M15 bars. Lot size 0.01 min / 0.01 step, 100 oz contract, 1:100 leverage.

**Strategy v3:** H1, 200-bar Donchian breakout, stop 2×ATR(14), trailing 4×ATR, no fixed TP, one position.
**Data-mined volatility sizing:** risk ×2 when weekly volatility is below 0.8× its 1-year median.

## $300 starting balance

| Version / risk | Final balance | Max drawdown | Months to $5,000 |
|---|---|---|---|
| v2 flat 3% | $6,818 | −35.7% | 93 |
| v3 1.5% (3% in quiet markets) | $5,014 | −24.4% | 98 |
| **v3 2% (4% in quiet markets): Balanced** | **$8,502** | **−31.7%** | **92** |
| v3 3% (6% in quiet markets): Aggressive | $23,306 | −45.0% | 62 |

Return per calendar year (%):

|                  |   2012* |   2013 |   2014 |   2015 |   2016 |   2017 |   2018 |   2019 |   2020 |   2021 |   2022* |
|:-----------------|-------:|-------:|-------:|-------:|-------:|-------:|-------:|-------:|-------:|-------:|-------:|
| v2 flat 3%       |     -3 |    102 |     29 |     42 |     68 |     39 |     -7 |     34 |    130 |      7 |    -11 |
| v3 data-mined 2% |     -3 |     98 |     32 |     54 |     59 |     62 |     -5 |     64 |    107 |      1 |    -13 |
| v3 data-mined 3% |     -3 |    107 |     54 |     80 |     93 |     84 |    -11 |     94 |    185 |     -1 |    -20 |

\* 2012 from May, 2022 to early March. On 2019–2022 alone, v3 2% grew ×3.02 (max drawdown −23.6%)
and v3 3% grew ×4.55 (max drawdown −34.9%).

## $10,000 at 2% base risk (precise lot sizing)
×29.4, CAGR 41%, max drawdown −33.0%, 463 trades, win rate 36.9%, profit factor 1.44, best trade +19.2R.
For comparison, v2 with flat 2.5% risk: ×17.4 with a −31.7% drawdown.

## How the strategy was found from the data
All scripts are in [`research/`](research/). Set `GOLD_M15_CSV` to the data file.

1. **Strategy families** (`fam1-4.py`): Donchian breakouts, Asian-range breakouts, RSI(2) mean
   reversion and the original M15 session EA. Tuned on 2012–2018, judged on 2019–2022.
   Only trend breakouts survived: 190 of 192 variants were profitable in both periods.
2. **Seasonality mining:** hour-of-day and weekday returns. Edges of ~1 basis point did not persist into
   2019–2022 and are smaller than trading costs (~2.8 basis points). Rejected.
3. **Machine learning** (`ml.py`, `ml_trade.py`): LightGBM trained on 33 features built from raw
   price data (multi-horizon returns, volatility, skew, range position, candle shape, hour, weekday).
   Retrained each year (walk-forward) and always predicting the next, unseen year. Prediction quality
   (rank IC) was positive in 7 of 8 years, but trading the model directly earned only +0.06 to +0.2R per trade
   and was unstable. Rejected as a standalone strategy.
4. **ML filter on breakouts** (`meta.py`, `meta2.py`): learn from the data which breakouts win.
   The most important features were **weekly volatility** and weekly skew/momentum. A shuffled-label
   placebo test showed no improvement, so the effect is not leakage.
5. **Turning it into simple rules** (`dist.py`, `rule.py`): breakouts that start when weekly volatility is
   **below 0.8× its 1-year median** averaged **+0.77R (2012–18) and +1.48R (2019–22)**, versus about 0
   for the rest. This is the "quiet market before the move" effect. The weekly-momentum rule looked good
   on the rough H1 simulation but did not help in the precise M15 backtest, so it is off by default
   (`MomentumBars=0`).
6. **Final rule:** keep every breakout but **double the risk on low-volatility breakouts**. At the same
   drawdown, this beats flat sizing in both the tuning period and the unseen period.

## Monte Carlo, $300 → $5,000 (v2 flat sizing, 2,000 reshuffles of the trade sequence)
| Risk | Chance of reaching ×16.7 | Median time | Chance of a >50% drawdown | Chance of a >80% drawdown |
|---|---|---|---|---|
| 2% | 49% | ~92 months | 4% | 0% |
| 3% | 78% | ~74 months | 36% | 0.5% |
| 5% | 90% | ~52 months | 92% | 11% |
| 10% | 92% | ~37 months | 100% | 90% |

**Reaching $5,000 within 2 weeks:** over every 2-week window in 2012–2022, the chance was 0% at
any risk up to 30%. At 50% risk it was 0.1%, with a 6.9% chance of losing more than 80%.

## Caveats
* Bar-based simulation, not tick data. Slippage and weekend gaps can differ live.
* The data ends in March 2022. Gold is now more volatile in dollar terms, so stops are wider. On a $300
  standard account, 0.01 lot can exceed the risk cap and the EA then skips the trade.
  **Use a cent account, or $1,000+.**
* Past performance does not guarantee future results. Expect losing streaks of 10–12 trades and flat years.

Reproduce: `python Backtest/gold_backtest.py --data XAUUSDm15.csv --balance 300 --risk 2 --out Backtest/results/v3_risk2`
