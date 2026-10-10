# Ladder ticket simulation: GTB_v3

**Measurement, not a recommendation.** Every row shows the probability of ruin next to the probability of success.

## Setup
* Ticket: $200 start, target $3,000 (x15.0), dead at or below $80, time box 30 days
* Tickets per risk level: 10,000; RNG seed: 20261010
* Trade source: `results/v3_10k_risk2/trades.csv` (463 trades, 2012-06-01 to 2022-02-17)
* Session filter ['london', 'ny']: 379 trades kept
* News blackout: requested but `data/news-calendar.csv` not found; **blackout NOT applied**
* Distribution: win rate 38.3%, average +0.338R, 3.2 trades per 30 days, median gap between trades 7.2 days

## Results

| Risk % per trade | P(reach target) | P(ruin) | P(time-box expired) | Median final equity | Median day of death | EV per $1 | Avg trades |
|---|---|---|---|---|---|---|---|
| 10% | 0.0% | **0.0%** | 100.0% | $195 | - | 1.11 | 3.1 |
| 20% | 0.1% | **1.2%** | 98.6% | $184 | 25 | 1.22 | 3.1 |
| 30% | 0.4% | **11.5%** | 88.0% | $168 | 22 | 1.34 | 3.0 |
| 40% | 1.0% | **28.2%** | 70.8% | $142 | 18 | 1.47 | 2.7 |
| 50% | 1.5% | **38.4%** | 60.1% | $111 | 17 | 1.57 | 2.6 |

EV per $1 = mean final equity / start balance (1.00 = break-even on average). It rises with risk while the
median falls: the mean is carried by the rare tickets that catch a big winner, the typical ticket loses money.

## Caveats
* The trade list comes from a bar-level backtest that has not been reconciled against MT5 (plan Phase 0); treat the distribution as unverified.
* Trades are drawn independently; real losing streaks cluster in flat regimes, so ruin is more likely than shown.
* Loss per trade is capped at the risked amount (hard stop). Gap slippage beyond the stop is included in R only as far as the backtest modelled it.
* The time box (30 days) holds only about 3 trades of this strategy; most tickets simply expire.
