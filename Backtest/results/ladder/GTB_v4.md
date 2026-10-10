# Ladder ticket simulation: GTB_v4

**Measurement, not a recommendation.** Every row shows the probability of ruin next to the probability of success.

## Setup
* Ticket: $200 start, target $3,000 (x15.0), dead at or below $80, time box 30 days
* Tickets per risk level: 10,000; RNG seed: 20261010
* Trade source: `results/v4_10k_risk1.5/trades.csv` (452 trades, 2012-06-01 to 2022-02-17)
* Session filter ['london', 'ny']: 368 trades kept
* News blackout: requested but `data/news-calendar.csv` not found; **blackout NOT applied**
* Distribution: win rate 29.3%, average +0.526R, 3.1 trades per 30 days, median gap between trades 7.9 days

## Results

| Risk % per trade | P(reach target) | P(ruin) | P(time-box expired) | Median final equity | Median day of death | EV per $1 | Avg trades |
|---|---|---|---|---|---|---|---|
| 10% | 0.0% | **0.0%** | 100.0% | $183 | - | 1.16 | 3.0 |
| 20% | 0.4% | **3.0%** | 96.6% | $161 | 25 | 1.35 | 2.9 |
| 30% | 1.1% | **20.3%** | 78.6% | $139 | 21 | 1.52 | 2.8 |
| 40% | 1.7% | **41.6%** | 56.7% | $118 | 17 | 1.66 | 2.4 |
| 50% | 2.4% | **48.3%** | 49.3% | $91 | 17 | 1.78 | 2.3 |

EV per $1 = mean final equity / start balance (1.00 = break-even on average). It rises with risk while the
median falls: the mean is carried by the rare tickets that catch a big winner, the typical ticket loses money.

## Caveats
* The trade list comes from a bar-level backtest that has not been reconciled against MT5 (plan Phase 0); treat the distribution as unverified.
* Trades are drawn independently; real losing streaks cluster in flat regimes, so ruin is more likely than shown.
* Loss per trade is capped at the risked amount (hard stop). Gap slippage beyond the stop is included in R only as far as the backtest modelled it.
* The time box (30 days) holds only about 3 trades of this strategy; most tickets simply expire.
