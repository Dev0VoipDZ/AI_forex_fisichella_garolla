# Gold (XAUUSD) Session Momentum Strategy

EA: `Code/MQL5_2020_06_15/Experts/Advisors/EA_Gold_SessionMomentum.mq5`
Presets: `Code/MQL5_2020_06_15/Presets/*.set`

> **Risk warning:** No strategy guarantees profit. Gold moves $30–$100+ per day and
> can gap on news (CPI, NFP, FOMC). Backtest and run on a demo account first.

## Why this design
Gold trends strongly once London and New York open, after a quiet Asian session.
The EA only trades **with the higher-timeframe trend** and **during liquid hours**.
It lets winners run (trailing stop) and cuts losers quickly (ATR stop). That gives it
a positive expectancy profile even with a win rate under 50%.

## Rules
| Part | Rule |
|---|---|
| Trend filter (H1) | EMA50 > EMA200 and close > EMA200 → longs only. Reverse for shorts. ADX(14) ≥ 20 or no trade. |
| Setup A: Asian breakout (M15) | Build the high/low from 00:00–07:00 server time. From 08:00–18:00, enter on the **first** M15 close beyond the range ± 0.1×ATR in the trend direction. One per side per day. Range must be 1.5–10 ATR. |
| Setup B: Pullback (M15) | Bar dips to EMA21, closes back above it as a bullish candle (bearish for shorts), RSI 45–70 (30–55 for shorts). |
| Stop loss | 1.5 × ATR(14, M15) |
| Take profit | 2.5R (standard) / 3R (aggressive) |
| Trade management | At +1R: close 50% and move the stop to entry + 0.1 ATR. After that, trail at 2 × ATR. |
| Risk controls | Risk % per trade, max spread, max 3 trades/day, daily loss limit, equity drawdown kill switch, flat on Friday at 20:00. |

## The $300 → $5,000 goal: honest math
That is a **~16.7× return**. On gold with 0.01 lot minimum:

* 0.01 lot ≈ $1 per $1 move. A 1.5×ATR stop on M15 is about $6–$10, so **the smallest
  possible trade already risks 2–3% of $300**. That's why the aggressive preset uses 3%
  risk and allows the minimum lot up to 5%.
* Suppose the edge is 40% wins at about 2.5R average and 60% losses at -1R. Expectancy is
  then ≈ +0.4R per trade. At 3% risk that is ≈ +1.2% per trade, compounded.
  Then 300 → 5,000 needs roughly **ln(16.7)/ln(1.012) ≈ 235 trades**. At 1–2 trades/day
  that is about **6–10 months, if the edge holds**.
* At 3% risk, 10 losses in a row (that happens) means about -26%. **Raising risk to 10%+
  per trade to "go faster" makes losing the account the most likely outcome.** Don't.

Realistic path:
1. Demo-test 1 month with the aggressive preset. Confirm spreads and behaviour.
2. Go live with $300 on a **cent or micro account** if you can (finer lot sizing = real % risk).
3. Once the account is above ~$1,000, switch to the **standard preset (1%)** to protect gains.
4. Withdraw your initial $300 once you're up 3×.

## Installation
1. Copy `EA_Gold_SessionMomentum.mq5` into `MQL5/Experts/` and compile it in MetaEditor (F7).
2. Attach it to an **XAUUSD M15** chart. Enable Algo Trading.
3. Load a preset from `Presets/` (Inputs → Load).
4. **Check your broker's server time.** The session hours are server hours. The defaults
   assume a GMT+2/+3 server (most MT5 brokers). Shift `AsianStartHour`,
   `AsianEndHour`, `TradeStartHour` and `TradeEndHour` if yours differs.
5. Use an ECN/raw-spread account. Gold spreads above $0.60 kill the edge.

## Backtesting in MT5 Strategy Tester
* Symbol XAUUSD, timeframe M15, model "Every tick based on real ticks", 2+ years.
* Optimize carefully (avoid curve-fitting): `SL_ATR` 1.0–2.5, `TP_R` 2–4, `ADXMin` 15–30,
  `Trail_ATR` 1.5–3. Validate on an out-of-sample period you did not optimize on.
* Avoid trading around high-impact news. Turn the EA off 30 minutes before NFP, CPI and FOMC.
