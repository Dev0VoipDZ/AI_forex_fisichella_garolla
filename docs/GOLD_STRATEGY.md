# Gold (XAUUSD) Trend Breakout Strategy

* EA: `Code/MQL5_2020_06_15/Experts/Advisors/EA_Gold_TrendBreakout.mq5`
* Presets: `Code/MQL5_2020_06_15/Presets/GTB_*.set`
* Backtest + full results: [`Backtest/RESULTS.md`](../Backtest/RESULTS.md)

> **Risk warning:** No strategy guarantees profit. Every trade has a stop loss. Without one,
> a single gold move of $30–$100 can wipe a small account. Test on demo first.

## Rules (chart: XAUUSD H1)
| | |
|---|---|
| **Buy** | The last closed H1 candle closes **above the highest high of the previous 200 candles**, and the candle before did not (fresh breakout). |
| **Sell** | The last closed H1 candle closes **below the lowest low of the previous 200 candles** (fresh breakout). |
| **Stop loss** | 2 × ATR(14) from entry. Always set. |
| **Trailing stop** | 4 × ATR(14) behind price; it only moves in your favour. It starts moving once the trade is about +1R. |
| **Take profit** | None: let trends run. Trades of +10R to +19R pay for the many small losses. |
| **Positions** | One at a time. Signals during an open trade are ignored. |
| **Size** | Risk % of equity per trade, from the stop distance. |

Expect a **~37% win rate**. Most trades are small losses; a few huge winners make the profit.
Losing streaks of 10–12 trades happened in the backtest. Do not switch the EA off during one.

## $300 → $5,000 plan
1. Open a **cent account** (or start with $1,000+ on a standard account), raw/ECN spread under $0.40.
2. Load `GTB_Balanced_3pct.set` (3% risk). Backtest: ×22.7 over 10 years, $5k in ~7–8 years, max drawdown −36%.
   For faster growth, use `GTB_Aggressive_5pct.set`: $5k in ~5 years in the backtest, **but expect a 50%+ drawdown**.
3. Never raise risk above 5%. At 10% risk, Monte Carlo gives a 90% chance of an 80%+ drawdown.
4. After reaching $5,000, switch to `GTB_Conservative_1pct.set` to keep it.

## Installation
1. Copy `EA_Gold_TrendBreakout.mq5` to `MQL5/Experts/` and compile it in MetaEditor (F7).
2. Open an **XAUUSD H1** chart and attach the EA. Enable Algo Trading.
3. Inputs → Load → choose a preset from `Presets/`.
4. Keep the terminal running 24/5 (VPS recommended). The trailing stop is updated by the EA.
5. Verify in the MT5 Strategy Tester (XAUUSD, H1, "Every tick based on real ticks", your broker's data).
